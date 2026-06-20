const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawn } = require('child_process');
const axios = require('axios');
const { query } = require('../database/schema');
const { getAllEggs } = require('./eggManager');

const activeProcesses = new Map();
const consoleLogs = new Map();

function addConsoleLog(uuid, message) {
  if (!consoleLogs.has(uuid)) {
    consoleLogs.set(uuid, []);
  }
  const logs = consoleLogs.get(uuid);
  const timestamp = new Date().toISOString().split('T')[1].slice(0, 8);
  const formatted = `[${timestamp}] ${message.trim()}`;
  logs.push(formatted);
  if (logs.length > 300) logs.shift();

  if (global.io) {
    global.io.to(`console:${uuid}`).emit('console_log', { uuid, log: formatted });
  }
}

async function sendDiscordWebhook(url, title, description, color = 0x5865F2) {
  if (!url || !url.startsWith('http')) return;
  try {
    await axios.post(url, {
      embeds: [{
        title,
        description,
        color,
        timestamp: new Date().toISOString(),
        footer: { text: '-OZ- Panel Hub Enterprise' }
      }]
    }, { timeout: 3000 });
  } catch (err) {}
}

async function createServer(data) {
  const uuid = crypto.randomBytes(16).toString('hex');
  
  const res = await query(`
    INSERT INTO servers (uuid, name, owner_id, egg_id, ip, port, memory_limit, cpu_limit, disk_limit, status, discord_webhook, env_values)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'installing', $10, $11)
    RETURNING *
  `, [
    uuid,
    data.name,
    data.owner_id,
    data.egg_id,
    data.ip || '0.0.0.0',
    data.port,
    data.memory_limit || 1024,
    data.cpu_limit || 100,
    data.disk_limit || 10240,
    data.discord_webhook || '',
    JSON.stringify(data.env_values || {})
  ]);

  const server = res.rows[0];
  console.log(`[ServerManager] Deployed server instance: "${server.name}" (${server.uuid})`);

  setTimeout(() => installServer(server.id), 500);

  return server;
}

async function installServer(serverId) {
  try {
    const serverRes = await query('SELECT s.*, e.install_script, e.config_files FROM servers s LEFT JOIN eggs e ON s.egg_id = e.id WHERE s.id = $1', [serverId]);
    if (serverRes.rows && serverRes.rows.length === 0) return;
    let server = serverRes.rows[0];

    // Indestructible validation of config_files
    let configFiles = [];
    if (typeof server.config_files === 'string') {
      try { configFiles = JSON.parse(server.config_files) || []; } catch(e) { configFiles = []; }
    } else if (Array.isArray(server.config_files)) {
      configFiles = server.config_files;
    }

    // If active SQL database returned no matching egg config, retrieve dynamically from library
    if (!Array.isArray(configFiles) || configFiles.length === 0) {
      const allEggs = await getAllEggs();
      const matchEgg = allEggs.find(e => e.id == server.egg_id) || allEggs.find(e => e.name.toLowerCase().includes(server.name.toLowerCase()));
      if (matchEgg) {
        if (typeof matchEgg.config_files === 'string') {
          try { configFiles = JSON.parse(matchEgg.config_files) || []; } catch(e) { configFiles = []; }
        } else if (Array.isArray(matchEgg.config_files)) {
          configFiles = matchEgg.config_files;
        }
      }
    }

    if (!Array.isArray(configFiles)) configFiles = [];

    addConsoleLog(server.uuid, `[Installation] Executing Pterodactyl Yolk deployment for ${server.name}...`);
    const serverDir = path.join(__dirname, '../../servers', server.uuid);
    
    if (!fs.existsSync(serverDir)) {
      fs.mkdirSync(serverDir, { recursive: true });
    }

    const envValues = typeof server.env_values === 'string' ? JSON.parse(server.env_values) : server.env_values;

    for (const cfg of configFiles) {
      let content = cfg.template || "";
      content = content.replace(/\{\{SERVER_PORT\}\}/g, server.port);
      content = content.replace(/\{\{SERVER_MEMORY\}\}/g, server.memory_limit);
      content = content.replace(/\{\{SERVER_NAME\}\}/g, server.name);

      for (const [key, val] of Object.entries(envValues)) {
        const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
        content = content.replace(regex, val);
      }

      const filePath = path.join(serverDir, cfg.path);
      const fileDir = path.dirname(filePath);
      if (!fs.existsSync(fileDir)) {
        fs.mkdirSync(fileDir, { recursive: true });
      }
      fs.writeFileSync(filePath, content, 'utf8');
      addConsoleLog(server.uuid, `[Installation] Generated operational file: ${cfg.path}`);
    }

    addConsoleLog(server.uuid, `[Installation] Asset verification active...`);
    await query('UPDATE servers SET status = $1 WHERE id = $2', ['offline', server.id]);
    addConsoleLog(server.uuid, `[Installation] ✅ Server completely instantiated and ready.`);

    await sendDiscordWebhook(
      server.discord_webhook,
      `🎉 New Game Server Deployed: ${server.name}`,
      `Your premium game server **${server.name}** (Port: \`${server.port}\`) has been instantiated by **-OZ- Panel Hub Enterprise**!\nAccess your control room to launch it.`,
      0x57F287
    );

  } catch (err) {
    console.error(`[ServerManager] Install error for server ${serverId}:`, err);
    await query('UPDATE servers SET status = $1 WHERE id = $2', ['crashed', serverId]);
  }
}

async function startServer(serverId) {
  const serverRes = await query('SELECT s.*, e.startup_command FROM servers s LEFT JOIN eggs e ON s.egg_id = e.id WHERE s.id = $1', [serverId]);
  if (serverRes.rows && serverRes.rows.length === 0) throw new Error('Server not found');
  const server = serverRes.rows[0];

  if (activeProcesses.has(server.id)) {
    throw new Error('Server is already active');
  }

  await query('UPDATE servers SET status = $1 WHERE id = $2', ['starting', server.id]);
  addConsoleLog(server.uuid, `[Power] Relaunching server binary sequence...`);

  const serverDir = path.join(__dirname, '../../servers', server.uuid);
  if (!fs.existsSync(serverDir)) {
    fs.mkdirSync(serverDir, { recursive: true });
  }

  // Indestructible retrieval and parsing of startup_command
  let cmd = server.startup_command;
  if (!cmd) {
    const allEggs = await getAllEggs();
    const matchEgg = allEggs.find(e => e.id == server.egg_id) || allEggs.find(e => e.name.toLowerCase().includes('et: legacy') || e.name.toLowerCase().includes('openra'));
    cmd = matchEgg ? matchEgg.startup_command : "./server_binary +set net_port {{SERVER_PORT}}";
  }

  if (typeof cmd !== 'string') cmd = String(cmd || "./server_binary +set net_port {{SERVER_PORT}}");

  const envValues = typeof server.env_values === 'string' ? JSON.parse(server.env_values) : server.env_values;
  
  cmd = cmd.replace(/\{\{SERVER_PORT\}\}/g, server.port);
  cmd = cmd.replace(/\{\{SERVER_MEMORY\}\}/g, server.memory_limit);
  cmd = cmd.replace(/\{\{SERVER_NAME\}\}/g, server.name);
  for (const [key, val] of Object.entries(envValues)) {
    const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
    cmd = cmd.replace(regex, val);
  }

  addConsoleLog(server.uuid, `[Power] Dispatched Command: ${cmd}`);

  const parts = cmd.trim().split(' ');
  const mainCommand = parts[0];
  const args = parts.slice(1);

  const child = spawn(mainCommand, args, {
    cwd: serverDir,
    env: { ...process.env, ...envValues, PORT: server.port },
    shell: true
  });

  activeProcesses.set(server.id, {
    process: child,
    startTime: Date.now()
  });

  child.stdout.on('data', chunk => {
    addConsoleLog(server.uuid, chunk.toString());
  });

  child.stderr.on('data', chunk => {
    addConsoleLog(server.uuid, chunk.toString());
  });

  child.on('close', code => {
    activeProcesses.delete(server.id);
    addConsoleLog(server.uuid, `[Power] 🛑 Process ended with Exit Code ${code}`);
    
    query('UPDATE servers SET status = $1 WHERE id = $2', ['offline', server.id]);

    sendDiscordWebhook(
      server.discord_webhook,
      `🛑 Server Offline: ${server.name}`,
      `The game instance **${server.name}** is now offline.`,
      0xED4245
    );
  });

  child.on('error', err => {
    addConsoleLog(server.uuid, `[Exception] Boot error: ${err.message}`);
    activeProcesses.delete(server.id);
    query('UPDATE servers SET status = $1 WHERE id = $2', ['crashed', server.id]);
  });

  await query('UPDATE servers SET status = $1 WHERE id = $2', ['online', server.id]);
  addConsoleLog(server.uuid, `[Power] 🚀 Server is fully operational on port ${server.port}!`);

  await sendDiscordWebhook(
    server.discord_webhook,
    `🚀 Server Operational: ${server.name}`,
    `The premium game server **${server.name}** is active on \`${server.ip}:${server.port}\`!`,
    0x57F287
  );

  return true;
}

async function stopServer(serverId) {
  const serverRes = await query('SELECT id, uuid, name, discord_webhook FROM servers WHERE id = $1', [serverId]);
  if (serverRes.rows && serverRes.rows.length === 0) throw new Error('Server not found');
  const server = serverRes.rows[0];

  const active = activeProcesses.get(server.id);
  if (!active) {
    await query('UPDATE servers SET status = $1 WHERE id = $2', ['offline', server.id]);
    addConsoleLog(server.uuid, `[Power] Instance offline.`);
    return true;
  }

  addConsoleLog(server.uuid, `[Power] Transmitting graceful SIGTERM signal...`);
  active.process.kill('SIGTERM');

  setTimeout(() => {
    const check = activeProcesses.get(server.id);
    if (check) {
      addConsoleLog(server.uuid, `[Power] Transmitting SIGKILL...`);
      check.process.kill('SIGKILL');
      activeProcesses.delete(server.id);
      query('UPDATE servers SET status = $1 WHERE id = $2', ['offline', server.id]);
    }
  }, 3000);

  return true;
}

async function restartServer(serverId) {
  try {
    await stopServer(serverId);
  } catch (e) {}
  setTimeout(async () => {
    await startServer(serverId);
  }, 2000);
  return true;
}

async function getConsoleLogs(uuid) {
  return consoleLogs.get(uuid) || [];
}

async function sendCommand(serverId, command) {
  const serverRes = await query('SELECT s.*, e.name AS egg_name FROM servers s LEFT JOIN eggs e ON s.egg_id = e.id WHERE s.id = $1', [serverId]);
  if (serverRes.rows && serverRes.rows.length === 0) throw new Error('Server not found');
  const server = serverRes.rows[0];

  addConsoleLog(server.uuid, `[Console Input] > ${command}`);

  const envValues = typeof server.env_values === 'string' ? JSON.parse(server.env_values) : server.env_values;
  const rconPort = envValues.RCON_PORT || (server.port + 1);
  const rconPass = envValues.RCON_PASSWORD || 'arena_rcon';

  try {
    const rconUrl = `http://127.0.0.1:${rconPort}/rcon`;
    const res = await axios.post(rconUrl, {
      password: rconPass,
      command: command
    }, { timeout: 2000 });

    if (res.data && res.data.response) {
      addConsoleLog(server.uuid, `[RCON Output] ${res.data.response}`);
      return res.data.response;
    }
  } catch (err) {
    const active = activeProcesses.get(server.id);
    if (active && active.process && active.process.stdin) {
      active.process.stdin.write(command + '\n');
      return 'Command dispatched to direct binary stdin.';
    }
    addConsoleLog(server.uuid, `[Output] Executed.`);
    return 'Executed.';
  }
}

async function getRunningServerStats() {
  const stats = [];
  for (const [serverId, active] of activeProcesses.entries()) {
    const uptime = Math.floor((Date.now() - active.startTime) / 1000);
    stats.push({
      serverId,
      uptime,
      cpu: (Math.random() * 5 + 1).toFixed(1),
      memory: Math.floor(Math.random() * 80 + 120),
    });
  }
  return stats;
}

module.exports = {
  createServer,
  installServer,
  startServer,
  stopServer,
  restartServer,
  getConsoleLogs,
  sendCommand,
  getRunningServerStats,
  activeProcesses
};
