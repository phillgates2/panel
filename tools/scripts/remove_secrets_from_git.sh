#!/bin/bash
# remove_secrets_from_git.sh - Remove config files with potential secrets from git

set -e

echo "????????????????????????????????????????????????????????????????"
echo "?                                                              ?"
echo "?     Remove Config Files with Secrets from Git History       ?"
echo "?                                                              ?"
echo "????????????????????????????????????????????????????????????????"
echo ""

# Files to remove from git
FILES_TO_REMOVE=(
    "config/config.production.json"
    "config/config.staging.json"
)

echo "??  WARNING: This will rewrite git history!"
echo ""
echo "Files to be removed from git:"
for file in "${FILES_TO_REMOVE[@]}"; do
    echo "  - $file"
done
echo ""
echo "These files will still exist locally but will be gitignored."
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Step 1: Remove files from git tracking..."
for file in "${FILES_TO_REMOVE[@]}"; do
    if git ls-files --error-unmatch "$file" &>/dev/null; then
        echo "  Removing $file from git..."
        git rm --cached "$file" 2>/dev/null || true
    else
        echo "  $file not in git (already removed or never added)"
    fi
done

echo ""
echo "Step 2: Update .gitignore..."
cat >> .gitignore << 'EOF'

# Config files with potential secrets
config/config.production.json
config/config.staging.json
config/config.local.json
config/config.*.local.json
EOF
echo "  ? Updated .gitignore"

echo ""
echo "Step 3: Commit changes..."
git add .gitignore
git commit -m "security: remove config files with potential secrets from git

- Removed config.production.json from tracking
- Removed config.staging.json from tracking
- Added template files instead (.template)
- Updated .gitignore to prevent future commits
- See docs/SECURITY_AUDIT_REPORT.md for details"

echo ""
echo "????????????????????????????????????????????????????????????????"
echo "?                                                              ?"
echo "?                  ? Files Removed from Git                   ?"
echo "?                                                              ?"
echo "????????????????????????????????????????????????????????????????"
echo ""
echo "Next steps:"
echo "1. Push changes: git push origin main"
echo "2. (OPTIONAL) Remove from history:"
echo "   git filter-branch --force --index-filter \\"
echo "     'git rm --cached --ignore-unmatch config/config.production.json config/config.staging.json' \\"
echo "     --prune-empty --tag-name-filter cat -- --all"
echo "3. Use template files: config/*.json.template"
echo "4. Set environment variables for production"
echo ""
echo "See docs/SECURITY_AUDIT_REPORT.md for complete remediation steps."
