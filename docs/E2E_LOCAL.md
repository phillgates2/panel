Playwright E2E — Run Locally Using Docker
=========================================

This project uses Playwright for end-to-end (E2E) tests. Playwright requires browser binaries and native dependencies that are not available in Alpine-based developer containers. The easiest way to run E2E locally is to use the official Playwright Docker image which bundles the browsers and required libraries.

Quick start (uses the official Playwright Python image):

1. Run an interactive container with your repo mounted:

```bash
docker run -it --rm \
  -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright/python:latest bash
```

2. Inside the container, install Python dependencies and run tests:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt || true
pip install -r requirements-dev.txt || pip install pytest

# Run the full test suite (includes Playwright e2e)
pytest -q
```

Notes
- The Playwright image already includes browser binaries. Using this image avoids installing browsers or system deps on your host machine.
- If your CI or local environment requires caching, add pip cache mounts or CI cache keys to speed up subsequent runs.
- If Playwright tests need environment variables (API keys, credentials), provide them to the `docker run` command using `-e VAR=value` or via a `.env` file.

If you want, I can add a `Makefile` target `make e2e` that runs the above `docker run` command for convenience.
