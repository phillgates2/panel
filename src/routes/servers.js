const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { query } = require('../database/schema');
const { requireAuth } = require('../security/security');
const { createServer, startServer, stopServer, restartServer, getConsoleLogs, sendCommand, activeProcesses } = require('../daemon/serverManager');

// 1. Create Game Server Container
router.post('/create', requireAuth, async (req, res) => {
  const { name, port, memory_limit, discord_webhook, egg_id, ...rest } = req.body;
  const user = req.session.user;

  // Extract env variables
  const envValues = {};
  for (const [k, v] of Object.entries(rest)) {
    if (k.startsWith('env_')) {
      envValues[k.slice(4)] = v;
    }
  }

  try {
    await createServer({
      name,
      owner_id: user.id,
      egg_id: parseInt(egg_id),
      port: parseInt(port),
      memory_limit: parseInt(memory_limit),
      discord_webhook: discord_webhook || '',
      env_values: envValues
    });

    res.redirect('/dashboard?success=Game Server deployment successfully initiated! Automated background installation is active.');
  } catch (err) {
    console.error('[Servers] Create Error:', err);
    res.redirect(`/dashboard?error=Deployment Exception: ${encodeURIComponent(err.message)}`);
  }
});

// Helper to verify Server Ownership
async function getServerAuth(req, res, next) {
  const uuid = req.params.uuid;
  const user = req.session.user;

  try {
    const srvRes = await query('SELECT s.*, e.name AS egg_name, e.docker_image, u.username AS owner_name FROM servers s LEFT JOIN eggs e ON s.egg_id = e.id LEFT JOIN users u ON s.owner_id = u.id WHERE s.uuid = $1', [uuid]);
    if (srvRes.rows.length === 0) {
      return res.status(404).render('404', { message: 'Requested server process not found.' });
    }

    const server = srvRes.rows[0];
    if (server.owner_id !== user.id && user.role !== 'admin') {
      return res.status(403).render('404', { message: '403 Forbidden: You do not own this game server container.' });
    }

    req.server = server;
    next();
  } catch (err) {
    console.error('[Servers] Auth helper error:', err);
    res.status(500).send('Internal Server Error');
  }
}

// 2. Main Master Console Room View
router.get('/:uuid', requireAuth, getServerAuth, async (req, res) => {
  const server = req.server;
  const user = req.session.user;
  const logs = await getConsoleLogs(server.uuid);
  const isRunning = activeProcesses.has(server.id);

  // List File Manager Root Directory
  const serverDir = path.join(__dirname, '../../servers', server.uuid);
  if (!fs.existsSync(serverDir)) {
    fs.mkdirSync(serverDir, { recursive: true });
  }

  // Get File list
  let files = [];
  try {
    const activeSubDir = req.query.dir ? req.query.dir.replace(/\.\./g, '') : '';
    const inspectDir = path.join(serverDir, activeSubDir);
    
    if (fs.existsSync(inspectDir)) {
      const dirEntries = fs.readdirSync(inspectDir, { withFileTypes: true });
      files = dirEntries.map(e => {
        const fullPath = path.join(inspectDir, e.name);
        const stats = fs.statSync(fullPath);
        return {
          name: e.name,
          isDirectory: e.isDirectory(),
          size: e.isDirectory() ? '-' : (stats.size / 1024).toFixed(1) + ' KB',
          modified: new Date(stats.mtime).toLocaleString(),
          relativePath: path.join(activeSubDir, e.name)
        };
      });
      // Sort folders first
      files.sort((a, b) => (b.isDirectory ? 1 : 0) - (a.isDirectory ? 1 : 0) || a.name.localeCompare(b.name));
    }
  } catch (e) {
    console.error('[WebFileManager] Error loading files:', e);
  }

  // Fetch AI Watchdog reports for this server
  const aiReportsRes = await query('SELECT * FROM ai_watchdog_logs WHERE server_id = $1 ORDER BY created_at DESC LIMIT 15', [server.id]);

  res.render('server_room', {
    user,
    server,
    logs,
    isRunning,
    files,
    activeDir: req.query.dir ? req.query.dir.replace(/\.\./g, '') : '',
    aiReports: aiReportsRes.rows,
    activeTab: req.query.tab || 'console',
    error: req.query.error || null,
    success: req.query.success || null
  });
});

// 3. Power Control Routes
router.post('/:uuid/start', requireAuth, getServerAuth, async (req, res) => {
  try {
    await startServer(req.server.id);
    res.redirect(`/servers/${req.server.uuid}?success=Server power execution launched!`);
  } catch (err) {
    res.redirect(`/servers/${req.server.uuid}?error=Power Boot Exception: ${encodeURIComponent(err.message)}`);
  }
});

router.post('/:uuid/stop', requireAuth, getServerAuth, async (req, res) => {
  try {
    await stopServer(req.server.id);
    res.redirect(`/servers/${req.server.uuid}?success=Graceful shutdown signal dispatched.`);
  } catch (err) {
    res.redirect(`/servers/${req.server.uuid}?error=Shutdown Exception: ${encodeURIComponent(err.message)}`);
  }
});

router.post('/:uuid/restart', requireAuth, getServerAuth, async (req, res) => {
  try {
    await restartServer(req.server.id);
    res.redirect(`/servers/${req.server.uuid}?success=Server reboot sequence initiated.`);
  } catch (err) {
    res.redirect(`/servers/${req.server.uuid}?error=Reboot Exception: ${encodeURIComponent(err.message)}`);
  }
});

// 4. Update Settings & Discord Channel Linking
router.post('/:uuid/settings', requireAuth, getServerAuth, async (req, res) => {
  const { name, port, memory_limit, cpu_limit, discord_webhook } = req.body;
  try {
    await query(`
      UPDATE servers 
      SET name = $1, port = $2, memory_limit = $3, cpu_limit = $4, discord_webhook = $5 
      WHERE id = $6
    `, [name, parseInt(port), parseInt(memory_limit), parseInt(cpu_limit), discord_webhook, req.server.id]);

    res.redirect(`/servers/${req.server.uuid}?tab=settings&success=Server specifications and Discord links updated successfully!`);
  } catch (err) {
    res.redirect(`/servers/${req.server.uuid}?tab=settings&error=Update Exception: ${encodeURIComponent(err.message)}`);
  }
});

module.exports = router;
