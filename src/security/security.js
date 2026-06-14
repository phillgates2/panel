const { query, getSetting } = require('../database/schema');

async function checkInstallerMiddleware(req, res, next) {
  // Allow static assets and the setup routes
  if (req.path.startsWith('/install') || req.path.startsWith('/assets') || req.path.startsWith('/favicon')) {
    return next();
  }

  try {
    const installed = await getSetting('INSTALLED');
    if (installed !== 'true') {
      return res.redirect('/install');
    }
    next();
  } catch (err) {
    console.error('[Security] Error checking installation state:', err);
    res.redirect('/install');
  }
}

function requireAuth(req, res, next) {
  if (!req.session || !req.session.user) {
    if (req.xhr || req.path.startsWith('/api/')) {
      return res.status(401).json({ error: 'Authentication required.' });
    }
    return res.redirect('/login');
  }
  // Check 2FA if enabled
  if (req.session.user.two_factor_enabled && !req.session.twoFactorPassed) {
    if (req.path !== '/verify-2fa' && req.path !== '/logout') {
      return res.redirect('/verify-2fa');
    }
  }
  next();
}

function requireAdmin(req, res, next) {
  if (!req.session || !req.session.user || req.session.user.role !== 'admin') {
    if (req.xhr || req.path.startsWith('/api/')) {
      return res.status(403).json({ error: 'Administrative privileges required.' });
    }
    return res.status(403).send('403 Forbidden: Administrative Privileges Required.');
  }
  next();
}

async function logAudit(userId, action, req, details = '') {
  try {
    const ip = req ? (req.headers['x-forwarded-for'] || req.socket.remoteAddress) : '127.0.0.1';
    await query('INSERT INTO audit_logs (user_id, action, ip_address, details) VALUES ($1, $2, $3, $4)', [
      userId || null,
      action,
      ip,
      String(details)
    ]);
  } catch (err) {
    console.error('[Security] Failed to write audit log:', err);
  }
}

// Minimal CSRF helper or Security Headers
function securityHeaders(req, res, next) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  next();
}

module.exports = {
  checkInstallerMiddleware,
  requireAuth,
  requireAdmin,
  logAudit,
  securityHeaders
};
