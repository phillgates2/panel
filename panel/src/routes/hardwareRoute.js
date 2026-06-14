const express = require('express');
const router = express.Router();
const { getLiveHardwareMetrics } = require('../daemon/hardwareMonitor');
const { requireAuth, requireAdmin } = require('../security/security');
const { query } = require('../database/schema');

// Main Master Hardware Monitor Control Room View
router.get('/', requireAuth, async (req, res) => {
  const user = req.session.user;
  try {
    const initialMetrics = await getLiveHardwareMetrics();
    
    // Fetch running or configured alarms
    const alarmsRes = await query("SELECT * FROM ai_watchdog_logs WHERE event_type = 'hardware_alarm' ORDER BY created_at DESC LIMIT 10");

    res.render('hardware_monitoring', {
      user,
      initialMetrics,
      alarms: alarmsRes.rows || [],
      success: req.query.success || null,
      error: req.query.error || null
    });
  } catch (err) {
    console.error('[HardwareRoute] Error loading hardware view:', err);
    res.status(500).send('Internal Server Error');
  }
});

// JSON API endpoint for active live polling / streaming or AJAX diagnostics
router.get('/metrics', requireAuth, async (req, res) => {
  try {
    const metrics = await getLiveHardwareMetrics();
    res.json(metrics);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update threshold parameters
router.post('/alarms', requireAdmin, async (req, res) => {
  const { cpu_alarm, mem_alarm, disk_alarm, alarm_webhook } = req.body;
  try {
    const { setSetting } = require('../database/schema');
    await setSetting('ALARM_CPU', cpu_alarm);
    await setSetting('ALARM_MEM', mem_alarm);
    await setSetting('ALARM_DISK', disk_alarm);
    await setSetting('ALARM_WEBHOOK', alarm_webhook);

    res.redirect('/hardware?success=Server hardware alarm thresholds and emergency Discord link updated successfully!');
  } catch (err) {
    res.redirect(`/hardware?error=${encodeURIComponent(err.message)}`);
  }
});

module.exports = router;
