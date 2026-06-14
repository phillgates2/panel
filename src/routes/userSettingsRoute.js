const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const crypto = require('crypto');
const { query } = require('../database/schema');
const { requireAuth, logAudit } = require('../security/security');

router.get('/', requireAuth, async (req, res) => {
  const user = req.session.user;
  try {
    const userRes = await query('SELECT * FROM users WHERE id = $1', [user.id]);
    const refreshedUser = userRes.rows[0];
    req.session.user = refreshedUser;

    const auditRes = await query('SELECT * FROM audit_logs WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20', [user.id]);

    res.render('user_settings', {
      user: refreshedUser,
      auditLogs: auditRes.rows,
      success: req.query.success || null,
      error: req.query.error || null,
      activeTab: req.query.tab || 'profile'
    });
  } catch (err) {
    console.error('[Settings] Error loading profile:', err);
    res.status(500).send('Internal Server Error');
  }
});

router.post('/profile', requireAuth, async (req, res) => {
  const { bio, avatar } = req.body;
  const user = req.session.user;
  try {
    await query('UPDATE users SET bio = $1, avatar = $2 WHERE id = $3', [bio, avatar, user.id]);
    await logAudit(user.id, 'user_update_profile', req);
    res.redirect('/settings?tab=profile&success=Profile bio and Avatar URL updated successfully!');
  } catch (err) {
    res.redirect(`/settings?tab=profile&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/password', requireAuth, async (req, res) => {
  const { password_old, password_new, password_confirm } = req.body;
  const user = req.session.user;

  if (password_new !== password_confirm) {
    return res.redirect('/settings?tab=security&error=New passwords do not match');
  }

  if (password_new.length < 8) {
    return res.redirect('/settings?tab=security&error=New password must be at least 8 characters');
  }

  try {
    const userRes = await query('SELECT password_hash FROM users WHERE id = $1', [user.id]);
    const match = await bcrypt.compare(password_old, userRes.rows[0].password_hash);
    if (!match) {
      return res.redirect('/settings?tab=security&error=Incorrect current password');
    }

    const hashed = await bcrypt.hash(password_new, 10);
    await query('UPDATE users SET password_hash = $1 WHERE id = $2', [hashed, user.id]);
    await logAudit(user.id, 'user_change_password', req);

    res.redirect('/settings?tab=security&success=Master authentication password changed successfully!');
  } catch (err) {
    res.redirect(`/settings?tab=security&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/sftp-password', requireAuth, async (req, res) => {
  const { sftp_password } = req.body;
  const user = req.session.user;

  try {
    const hashed = await bcrypt.hash(sftp_password, 10);
    await query('UPDATE users SET sftp_password = $1 WHERE id = $2', [hashed, user.id]);
    await logAudit(user.id, 'user_update_sftp_password', req);

    res.redirect('/settings?tab=sftp&success=Standalone SFTP Direct Connection password successfully configured!');
  } catch (err) {
    res.redirect(`/settings?tab=sftp&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/toggle-2fa', requireAuth, async (req, res) => {
  const user = req.session.user;

  try {
    if (user.two_factor_enabled) {
      await query('UPDATE users SET two_factor_enabled = FALSE, two_factor_secret = NULL WHERE id = $1', [user.id]);
      await logAudit(user.id, 'user_disable_2fa', req);
      return res.redirect('/settings?tab=security&success=Two-Factor Authentication (2FA) disabled successfully.');
    } else {
      const secret = crypto.randomBytes(6).toString('hex').toUpperCase().slice(0, 6);
      await query('UPDATE users SET two_factor_enabled = TRUE, two_factor_secret = $1 WHERE id = $2', [secret, user.id]);
      await logAudit(user.id, 'user_enable_2fa', req);
      return res.redirect('/settings?tab=security&success=Two-Factor Authentication activated! Your secret token has been generated.');
    }
  } catch (err) {
    res.redirect(`/settings?tab=security&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/api-key', requireAuth, async (req, res) => {
  const user = req.session.user;
  try {
    const apiKey = 'tc_' + crypto.randomBytes(16).toString('hex');
    await query('UPDATE users SET api_key = $1 WHERE id = $2', [apiKey, user.id]);
    await logAudit(user.id, 'user_generate_api_key', req);
    res.redirect('/settings?tab=api&success=New Enterprise API Key generated successfully!');
  } catch (err) {
    res.redirect(`/settings?tab=api&error=${encodeURIComponent(err.message)}`);
  }
});

module.exports = router;
