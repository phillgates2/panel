const express = require('express');
const router = express.Router();
const { getAiWatchdogLogs, queryAiAssistant } = require('../ai/aiWatchdog');
const { requireAuth } = require('../security/security');

router.get('/', async (req, res) => {
  const user = req.session ? req.session.user : null;
  try {
    const aiReports = await getAiWatchdogLogs(30);
    res.render('ai_assistant_view', {
      user,
      aiReports,
      error: req.query.error || null,
      success: req.query.success || null
    });
  } catch (err) {
    console.error('[AIAssistant] Error loading view:', err);
    res.status(500).send('Internal Server Error');
  }
});

router.post('/prompt', async (req, res) => {
  const { prompt, server_uuid } = req.body;
  try {
    const advice = await queryAiAssistant(prompt, server_uuid || null);
    res.json({ advice });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
