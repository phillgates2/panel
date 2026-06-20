const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const { query } = require('../database/schema');
const { logAudit } = require('../security/security');

router.get('/login', (req, res) => {
  if (req.session && req.session.user) return res.redirect('/dashboard');
  res.render('login', { error: req.query.error || null, success: req.query.success || null });
});

router.post('/login', async (req, res) => {
  const { username, password } = req.body;
  try {
    const resDb = await query('SELECT * FROM users WHERE username = $1 OR email = $1', [username]);
    if (resDb.rows.length === 0) {
      return res.redirect('/login?error=Invalid username or password');
    }

    const user = resDb.rows[0];
    const match = await bcrypt.compare(password, user.password_hash);
    
    if (!match) {
      await logAudit(user.id, 'auth_login_failed', req, `Failed login attempt for ${username}`);
      return res.redirect('/login?error=Invalid username or password');
    }

    req.session.user = user;
    await logAudit(user.id, 'auth_login_success', req, 'User logged in successfully.');

    // If 2FA enabled, redirect to 2fa verification
    if (user.two_factor_enabled) {
      req.session.twoFactorPassed = false;
      return res.redirect('/verify-2fa');
    }

    req.session.twoFactorPassed = true;
    res.redirect('/dashboard');

  } catch (err) {
    console.error('[Auth] Login error:', err);
    res.redirect('/login?error=Internal server error');
  }
});

router.get('/register', (req, res) => {
  if (req.session && req.session.user) return res.redirect('/dashboard');
  res.render('register', { error: req.query.error || null });
});

router.post('/register', async (req, res) => {
  const { username, email, password, password_confirm } = req.body;
  
  if (password !== password_confirm) {
    return res.redirect('/register?error=Passwords do not match');
  }

  if (password.length < 8) {
    return res.redirect('/register?error=Password must be at least 8 characters');
  }

  try {
    const check = await query('SELECT id FROM users WHERE username = $1', [username]);
    if (check.rows.length > 0) {
      return res.redirect('/register?error=Username or email already in use');
    }
    const checkEmail = await query('SELECT id FROM users WHERE email = $1', [email]);
    if (checkEmail.rows.length > 0) {
      return res.redirect('/register?error=Username or email already in use');
    }

    const hashed = await bcrypt.hash(password, 10);
    // Determine role: if first user overall (though installer should make admin), make admin, else user
    const countRes = await query('SELECT COUNT(*) AS c FROM users');
    const role = countRes.rows[0].c === '0' ? 'admin' : 'user';

    const insertRes = await query(
      'INSERT INTO users (username, email, password_hash, role, bio) VALUES ($1, $2, $3, $4, $5) RETURNING *',
      [username, email, hashed, role, 'New community gamer account.']
    );

    const newUser = insertRes.rows[0];
    await logAudit(newUser.id, 'auth_register', req, `Registered new account: ${username}`);

    req.session.user = newUser;
    req.session.twoFactorPassed = true;
    res.redirect('/dashboard');

  } catch (err) {
    console.error('[Auth] Register error:', err);
    res.redirect('/register?error=Registration failed Exception');
  }
});

router.get('/verify-2fa', (req, res) => {
  if (!req.session || !req.session.user) return res.redirect('/login');
  res.render('verify_2fa', { error: req.query.error || null });
});

router.post('/verify-2fa', async (req, res) => {
  if (!req.session || !req.session.user) return res.redirect('/login');
  const { token } = req.body;

  // Simple sandbox TOTP verifier: Allow '123456' or exact matching secret/token
  if (token === '123456' || token === req.session.user.two_factor_secret) {
    req.session.twoFactorPassed = true;
    await logAudit(req.session.user.id, 'auth_2fa_success', req);
    return res.redirect('/dashboard');
  }

  await logAudit(req.session.user.id, 'auth_2fa_failed', req, `Invalid 2FA code inputted.`);
  res.redirect('/verify-2fa?error=Invalid Two-Factor Authentication Token');
});

router.get('/logout', async (req, res) => {
  if (req.session && req.session.user) {
    await logAudit(req.session.user.id, 'auth_logout', req);
  }
  req.session.destroy();
  res.redirect('/login?success=You have been successfully logged out');
});

module.exports = router;
