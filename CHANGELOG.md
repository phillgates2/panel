# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Added Theme Editor: admin can edit site CSS via `/admin/theme`.
- Hide `Dashboard` and `RCON` links on the public site unless a user is logged in.
 - Add server logo support in Theme Editor: upload/store logos and serve at `/theme_asset/<filename>`.
 - Captcha hardening across auth flows:
	 - Add captcha to Forgot Password form (required in non-testing environments).
	 - Enforce captcha on Login and Reset Password; provide audio via espeak.
	 - Captcha expiry (3 minutes) and per-IP rate limiting for login/forgot/reset and captcha image.
	 - Skip captcha validation in TESTING mode and hide captcha UI in tests to unblock Playwright E2E.
	 - Fix Pillow 10+ compatibility for captcha text sizing (use `textbbox` with fallbacks).
 - SQLAlchemy deprecations resolved: replace `Query.get()` with `db.session.get()`.

## [scaffold-initial-2025-11-14] - 2025-11-14

- Initial scaffold merge: Flask backend, admin UI templates, deploy/systemd examples.
- Authentication flows (register/login/forgot), local captcha generation, and password rules.
- Server model, role-based access, admin server CRUD, and audit logging with streaming CSV export.
- Confirmation modal with accessibility improvements and keyboard handling.
- Tests: unit tests for auth/models/server UI and a Playwright E2E test scaffold for modal behavior.
- CI workflow and example `requirements.txt` including Playwright.
- Utility scripts and systemd units for RQ workers, memwatch, and autodeploy.

*(This file follows Keep a Changelog format in a minimal form.)*
