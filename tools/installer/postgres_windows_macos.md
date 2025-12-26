Notes for cross-platform Postgres installation:

- macOS: prefer `brew install postgres` and `brew services start postgresql`. Ensure Homebrew exists.
- Windows: prefer `choco install postgresql` or `winget install --id PostgreSQL` when available.
- For installers we will keep Linux apt/dnf/yum/pacman/apk flows and extend to use brew/choco/winget where available.
