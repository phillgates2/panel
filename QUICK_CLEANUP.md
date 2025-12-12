# Quick Cleanup Commands

Run these commands immediately to clean up your repository:

## ?? Immediate Cleanup (Safe)

### Python Cache
```bash
# Remove all __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Remove all .pyc files
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
```

### Log Files
```bash
# Remove all .log files
find . -type f -name "*.log" -delete 2>/dev/null

# Clear log directories (keep directories)
rm -rf logs/*.log 2>/dev/null
rm -rf instance/logs/*.log 2>/dev/null
```

### IDE Files
```bash
# Remove VS Code settings (will regenerate)
rm -rf .vscode 2>/dev/null

# Remove PyCharm settings (will regenerate)
rm -rf .idea 2>/dev/null

# Remove vim swap files
find . -name "*.swp" -delete 2>/dev/null
find . -name "*.swo" -delete 2>/dev/null
```

### OS Metadata
```bash
# Remove macOS files
find . -name ".DS_Store" -delete 2>/dev/null

# Remove Windows files
find . -name "Thumbs.db" -delete 2>/dev/null
find . -name "desktop.ini" -delete 2>/dev/null
```

### Backup Files
```bash
# Remove backup files
find . -name "*.backup" -delete 2>/dev/null
find . -name "*.bak" -delete 2>/dev/null
find . -name "*.old" -delete 2>/dev/null
find . -name "*~" -delete 2>/dev/null
```

## ?? One-Line Full Cleanup

### Linux/macOS
```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; find . -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.log" -o -name "*.swp" -o -name "*.swo" -o -name ".DS_Store" -o -name "Thumbs.db" -o -name "*.backup" -o -name "*.bak" -o -name "*.old" -o -name "*~" \) -delete 2>/dev/null; rm -rf .vscode .idea logs/*.log instance/logs/*.log 2>/dev/null; echo "? Cleanup complete!"
```

### Windows PowerShell
```powershell
Get-ChildItem -Path . -Include __pycache__,*.pyc,*.pyo,*.log,*.swp,.DS_Store,Thumbs.db,*.backup,*.bak,*.old -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue; Remove-Item .vscode,.idea -Recurse -Force -ErrorAction SilentlyContinue; Write-Host "? Cleanup complete!" -ForegroundColor Green
```

## ?? Git Cleanup
```bash
# Remove untracked files (dry run first)
git clean -n -d

# Actually remove untracked files
git clean -f -d

# Optimize git repository
git gc --aggressive --prune=now
```

## ?? Specific Issues

### "Too many files changed" in Git
```bash
# This is often due to __pycache__ and .pyc files
# Add to .gitignore first, then:
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
git rm -r --cached . 
git add .
git commit -m "Remove cached files"
```

### Large Repository Size
```bash
# Find largest files
find . -type f -exec du -h {} + | sort -rh | head -20

# Check git object size
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | sed -n 's/^blob //p' | sort --numeric-sort --key=2 -r | head -20
```

### Disk Space Check
```bash
# Before cleanup
du -sh .

# After cleanup (compare)
du -sh .
```

## ? Quick Validation

After cleanup, verify everything still works:

```bash
# Check Python environment
python3 --version

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Test import
python -c "import flask; print('Flask OK')"

# Run tests if available
pytest tests/ -v 2>/dev/null || echo "No tests found"

# Check git status
git status

# Check for remaining unwanted files
find . -name "*.pyc" -o -name "*.log" -o -name "__pycache__"
```

## ?? Update .gitignore (Quick)

Add these essential lines to `.gitignore`:

```bash
cat >> .gitignore << 'EOF'

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Backups
*.backup
*.bak
EOF
```

## ?? Regular Maintenance

Add this to your workflow (run weekly):

```bash
# Quick weekly cleanup
find . -name "*.pyc" -delete && \
find . -name "*.log" -delete && \
find . -name ".DS_Store" -delete && \
git gc --quiet && \
echo "? Weekly cleanup done!"
```

---

**?? Pro Tip**: Add these commands as Git aliases in `~/.gitconfig`:

```ini
[alias]
    cleanup = !git clean -fd && find . -name '*.pyc' -delete && find . -name '__pycache__' -type d -exec rm -rf {} +
    optimize = gc --aggressive --prune=now
```

Then use: `git cleanup` and `git optimize`
