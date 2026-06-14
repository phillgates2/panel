const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const { query } = require('../database/schema');
const { sendCommand } = require('../daemon/serverManager');
const { requireAuth } = require('../security/security');

async function checkFileAccess(req, res, next) {
  const { serverUuid, filePath } = req.body;
  if (!serverUuid || !filePath) {
    return res.status(400).json({ error: 'Missing parameters' });
  }

  const user = req.session.user;
  try {
    const srvRes = await query('SELECT * FROM servers WHERE uuid = $1', [serverUuid]);
    if (srvRes.rows && srvRes.rows.length === 0) return res.status(404).json({ error: 'Server not found' });
    
    const server = srvRes.rows[0];
    if (server.owner_id !== user.id && user.role !== 'admin') {
      return res.status(403).json({ error: 'Access denied' });
    }

    const serverRoot = path.resolve(__dirname, '../../servers', server.uuid);
    const targetPath = path.resolve(serverRoot, filePath.replace(/^\//, ''));

    if (!targetPath.startsWith(serverRoot)) {
      return res.status(403).json({ error: 'Path traversal prevented.' });
    }

    req.server = server;
    req.targetPath = targetPath;
    req.serverRoot = serverRoot;
    next();
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}

router.post('/files/read', requireAuth, checkFileAccess, async (req, res) => {
  try {
    if (!fs.existsSync(req.targetPath)) {
      return res.status(404).json({ error: 'File does not exist' });
    }
    const content = fs.readFileSync(req.targetPath, 'utf8');
    res.json({ content });
  } catch (err) {
    res.status(500).json({ error: 'Cannot read file' });
  }
});

router.post('/files/write', requireAuth, checkFileAccess, async (req, res) => {
  try {
    const fileDir = path.dirname(req.targetPath);
    if (!fs.existsSync(fileDir)) {
      fs.mkdirSync(fileDir, { recursive: true });
    }
    fs.writeFileSync(req.targetPath, req.body.content || '', 'utf8');
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/files/delete', requireAuth, checkFileAccess, async (req, res) => {
  try {
    if (fs.existsSync(req.targetPath)) {
      fs.rmSync(req.targetPath, { recursive: true, force: true });
    }
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/files/rename', requireAuth, checkFileAccess, async (req, res) => {
  const { newName } = req.body;
  if (!newName) return res.status(400).json({ error: 'New name required' });

  try {
    const fileDir = path.dirname(req.targetPath);
    const newPath = path.resolve(fileDir, newName.replace(/^\//, ''));
    if (!newPath.startsWith(req.serverRoot)) {
      return res.status(403).json({ error: 'Security violation' });
    }

    fs.renameSync(req.targetPath, newPath);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/files/create-folder', requireAuth, checkFileAccess, async (req, res) => {
  try {
    if (!fs.existsSync(req.targetPath)) {
      fs.mkdirSync(req.targetPath, { recursive: true });
    }
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/rcon/dispatch', requireAuth, async (req, res) => {
  const { serverId, command } = req.body;
  const user = req.session.user;

  try {
    const srvRes = await query('SELECT * FROM servers WHERE id = $1', [serverId]);
    if (srvRes.rows && srvRes.rows.length === 0) return res.status(404).json({ error: 'Server not found' });
    const server = srvRes.rows[0];

    if (server.owner_id !== user.id && user.role !== 'admin') {
      return res.status(403).json({ error: 'Permission denied.' });
    }

    const response = await sendCommand(serverId, command);
    res.json({ response });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/forums/chat', requireAuth, async (req, res) => {
  const { message } = req.body;
  const user = req.session.user;
  if (!message || !message.trim()) return res.status(400).json({ error: 'Message required' });

  try {
    const insertRes = await query(`
      INSERT INTO forum_chat_messages (user_id, message) 
      VALUES ($1, $2) RETURNING *
    `, [user.id, message.trim()]);

    const msg = insertRes.rows[0];
    const formatted = {
      ...msg,
      username: user.username,
      avatar: user.avatar,
      role: user.role
    };

    if (global.io) {
      global.io.emit('forum_chat', formatted);
    }

    res.json({ success: true, message: formatted });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/discord/test', requireAuth, async (req, res) => {
  const { webhookUrl, serverName } = req.body;
  if (!webhookUrl) return res.status(400).json({ error: 'Webhook URL required' });

  try {
    await axios.post(webhookUrl, {
      embeds: [{
        title: `🧪 Automated Embedded Channel Test: ${serverName}`,
        description: `This automated test confirms that your **-OZ- Panel Hub Enterprise** instance is perfectly bound to this Discord channel!`,
        color: 0x5865F2,
        timestamp: new Date().toISOString(),
        footer: { text: '-OZ- Sentinel Core' }
      }]
    }, { timeout: 3000 });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Webhook failed to dispatch' });
  }
});

module.exports = router;
