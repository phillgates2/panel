const express = require('express');
const router = express.Router();
const { query } = require('../database/schema');
const { requireAuth } = require('../security/security');
const { getRunningServerStats, activeProcesses } = require('../daemon/serverManager');
const { getAllEggs } = require('../daemon/eggManager');

router.get('/', requireAuth, async (req, res) => {
  const user = req.session.user;

  try {
    let servers = [];
    if (user.role === 'admin') {
      const srvRes = await query('SELECT s.*, u.username AS owner_name FROM servers s LEFT JOIN users u ON s.owner_id = u.id ORDER BY s.created_at DESC');
      servers = srvRes.rows || [];
    } else {
      const srvRes = await query('SELECT s.*, u.username AS owner_name FROM servers s LEFT JOIN users u ON s.owner_id = u.id WHERE s.owner_id = $1 ORDER BY s.created_at DESC', [user.id]);
      servers = srvRes.rows || [];
    }

    const runningStats = await getRunningServerStats();
    
    // Dynamically load all 24 Pterodactyl Game Eggs
    const allEggs = await getAllEggs();

    servers = servers.map(srv => {
      const st = runningStats.find(r => r.serverId === srv.id);
      const matchingEgg = allEggs.find(e => e.id == srv.egg_id);
      return {
        ...srv,
        egg_name: matchingEgg ? matchingEgg.name : 'Game Engine',
        docker_image: matchingEgg ? matchingEgg.docker_image : 'ghcr.io/pterodactyl/yolks:debian',
        runtime: st ? { cpu: st.cpu, memory: st.memory, uptime: st.uptime } : null,
        isRunning: activeProcesses.has(srv.id)
      };
    });

    res.render('dashboard', {
      user,
      servers,
      eggs: allEggs,
      error: req.query.error || null,
      success: req.query.success || null
    });

  } catch (err) {
    console.error('[Dashboard] Error fetching dashboard:', err);
    res.status(500).send('Internal Server Error');
  }
});

module.exports = router;
