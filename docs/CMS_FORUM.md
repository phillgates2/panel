# CMS, Forum and Mail integration

This folder contains a minimal scaffold for a simple CMS, forum and a
lightweight mail client. The implementation is intentionally small and
dependency-free (uses Python's standard library `smtplib`).

Files added:
- `tools/mail.py`: lightweight SMTP client wrapper. Configure mail via
  `app.config` (see below).
- `cms/`: blueprint providing a simple Page model and basic CRUD views.
- `forum/`: blueprint providing Thread/Post models and simple views.

Configuration
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` can be set in `config.py` or via env vars.

Usage
- The blueprints are registered automatically on the module-level app and on apps created via `create_app()` if present. Visit `/cms/` and `/forum/` in the running app to try the features.

Security
- These are minimal examples, not production-ready. Add authentication, CSRF protections, input sanitization, and rate limiting before using in a public site.
