# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Added Theme Editor: admin can edit site CSS via `/admin/theme`.
- Hide `Dashboard` and `RCON` links on the public site unless a user is logged in.

## [scaffold-initial-2025-11-14] - 2025-11-14

- Initial scaffold merge: Flask backend, admin UI templates, deploy/systemd examples.
- Authentication flows (register/login/forgot), local captcha generation, and password rules.
- Server model, role-based access, admin server CRUD, and audit logging with streaming CSV export.
- Confirmation modal with accessibility improvements and keyboard handling.
- Tests: unit tests for auth/models/server UI and a Playwright E2E test scaffold for modal behavior.
- CI workflow and example `requirements.txt` including Playwright.
- Utility scripts and systemd units for RQ workers, memwatch, and autodeploy.

*(This file follows Keep a Changelog format in a minimal form.)*
