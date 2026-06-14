const fs = require('fs');
const path = require('path');
const ssh2 = require('ssh2');
const { query } = require('../database/schema');

const hostKeyPath = path.join(__dirname, 'sftp_host_rsa_key');

function getHostKey() {
  if (fs.existsSync(hostKeyPath)) {
    return fs.readFileSync(hostKeyPath);
  }
  const { privateKey } = require('crypto').generateKeyPairSync('rsa', {
    modulusLength: 2048,
    publicKeyEncoding: { type: 'spki', format: 'pem' },
    privateKeyEncoding: { type: 'pkcs1', format: 'pem' }
  });
  fs.writeFileSync(hostKeyPath, privateKey);
  return privateKey;
}

function startSFTPServer(port = 2022) {
  const server = new ssh2.Server({
    hostKeys: [getHostKey()]
  }, (client) => {
    let authenticatedUser = null;

    client.on('authentication', async (ctx) => {
      if (ctx.method !== 'password') {
        return ctx.reject(['password']);
      }

      try {
        const res = await query('SELECT * FROM users WHERE username = $1', [ctx.username]);
        if (res.rows.length === 0) return ctx.reject();

        const user = res.rows[0];
        const bcrypt = require('bcryptjs');

        let match = false;
        if (user.sftp_password) {
          match = await bcrypt.compare(ctx.password, user.sftp_password);
        }
        if (!match) {
          match = await bcrypt.compare(ctx.password, user.password_hash);
        }

        if (match) {
          authenticatedUser = user;
          return ctx.accept();
        }
        return ctx.reject();
      } catch (err) {
        console.error('[SFTP] Auth Error:', err);
        return ctx.reject();
      }
    });

    client.on('ready', () => {
      client.on('session', (accept, reject) => {
        const session = accept();
        session.on('sftp', async (acceptSftp, rejectSftp) => {
          try {
            let servers = [];
            if (authenticatedUser.role === 'admin') {
              const allRes = await query('SELECT uuid FROM servers');
              servers = allRes.rows;
            } else {
              const myRes = await query('SELECT uuid FROM servers WHERE owner_id = $1', [authenticatedUser.id]);
              servers = myRes.rows;
            }

            if (servers.length === 0) {
              return rejectSftp();
            }

            const sftpRoot = path.join(__dirname, '../../servers');
            const openFiles = new Map();
            let handleCounter = 1;

            const sftpStream = acceptSftp();

            sftpStream.on('OPEN', (reqid, filename, flags, attrs) => {
              const safePath = path.resolve(sftpRoot, filename.replace(/^\//, ''));
              if (!safePath.startsWith(sftpRoot)) {
                return sftpStream.status(reqid, ssh2.SFTP_STATUS_CODE.PERMISSION_DENIED);
              }
              const handle = Buffer.alloc(4);
              handle.writeUInt32BE(handleCounter++, 0);
              const fd = fs.openSync(safePath, flags);
              openFiles.set(handle.toString('hex'), fd);
              sftpStream.handle(reqid, handle);
            });

            sftpStream.on('READ', (reqid, handle, offset, length) => {
              const fd = openFiles.get(handle.toString('hex'));
              if (!fd) return sftpStream.status(reqid, ssh2.SFTP_STATUS_CODE.FAILURE);
              const buffer = Buffer.alloc(length);
              fs.read(fd, buffer, 0, length, offset, (err, bytesRead, buf) => {
                if (err) return sftpStream.status(reqid, ssh2.SFTP_STATUS_CODE.FAILURE);
                if (bytesRead === 0) return sftpStream.status(reqid, ssh2.SFTP_STATUS_CODE.EOF);
                sftpStream.data(reqid, buf.slice(0, bytesRead));
              });
            });

            sftpStream.on('WRITE', (reqid, handle, offset, data) => {
              const fd = openFiles.get(handle.toString('hex'));
              if (!fd) return sftpStream.status(reqid, ssh2.SFTP_STATUS_CODE.FAILURE);
              fs.write(fd, data, 0, data.length, offset, (err) => {
                if (err) return sftpStream.status(reqid, ssh2.SFTP_STATUS_CODE.FAILURE);
                sftpStream.status(reqid, ssh2.SFTP_STATUS_CODE.OK);
              });
            });

            sftpStream.on('CLOSE', (reqid, handle) => {
              const fd = openFiles.get(handle.toString('hex'));
              if (fd) {
                fs.closeSync(fd);
                openFiles.delete(handle.toString('hex'));
              }
              sftpStream.status(reqid, ssh2.SFTP_STATUS_CODE.OK);
            });

            sftpStream.on('READDIR', (reqid, handle) => {
              sftpStream.status(reqid, ssh2.SFTP_STATUS_CODE.EOF);
            });

          } catch (e) {
            return rejectSftp();
          }
        });
      });
    });
  });

  server.listen(port, '0.0.0.0', () => {
    console.log(`[SFTPServer] Embedded SFTP Daemon active on port ${port}`);
  });

  return server;
}

module.exports = {
  startSFTPServer
};
