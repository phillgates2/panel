# Contributing

Thanks for your interest in contributing to this project. This document explains how to contribute code, tests, and documentation.

1. Setup
 - Create a Python virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

 - If you plan to run the E2E tests, install Playwright browsers:

```bash
python -m playwright install
```

2. Branching and issues
 - Work from feature branches named `feat/your-feature`, `fix/issue-123`, or `chore/whatever`.
 - Reference issues in PR titles or descriptions (e.g. `Fixes #123`).

3. Commit messages
 - Use Conventional Commits style for messages (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`).
 - The repository uses a Developer Certificate of Origin (DCO). Please sign-off your commits with:

```
Signed-off-by: Your Name <your.email@example.com>
```

You can add the trailer automatically when committing:

```bash
git commit -s -m "feat: add example"
```

4. Tests
 - Add unit tests for new functionality and run the test suite locally:

```bash
pytest -q
```

 - If adding browser E2E tests, use Playwright and run them in headless mode in CI. Example:

```bash
pytest tests/test_modal_e2e.py -q
```

5. Code style
 - Follow standard Python formatting (use `black` and `isort` in your editor/CI).

6. Pull requests
 - Open a PR against `main` with a clear description, testing notes, and links to relevant issues.
 - Add labels and request reviews (the repository maintainers will assign reviewers).

7. Security and sensitive data
 - Do not commit credentials, secrets, or production configuration to the repository. Use environment variables or secrets in CI.

8. Release notes
 - After merging a significant set of changes, update `CHANGELOG.md` with a short summary and tag the release (e.g., `scaffold-initial-2025-11-14`).

Thank you for contributing — we appreciate careful PRs and good tests.
