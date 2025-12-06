# Security Remediation Guide

## ?? Removing Secrets from Git - Complete Guide

### Date: December 2024
### Status: IN PROGRESS

---

## WHAT WAS DONE

### ? Step 1: Security Audit Complete
- Created comprehensive security audit report
- Identified hardcoded credentials in config files
- Assessed risk level: MEDIUM (likely placeholders)
- See: `docs/SECURITY_AUDIT_REPORT.md`

### ? Step 2: Files Removed from Tracking
```bash
git rm --cached config/config.production.json
git rm --cached config/config.staging.json
```

**Result**: Files removed from git index but kept locally

### ? Step 3: Template Files Created
- `config/config.production.json.template` - Uses ${ENV_VAR} placeholders
- `config/config.staging.json.template` - Uses ${ENV_VAR} placeholders

### ? Step 4: Gitignore Updated
Already configured to ignore:
```
config/config.*.json
config/config.local.py
```

---

## WHAT NEEDS TO BE DONE

### Priority 1: VERIFY CREDENTIALS (CRITICAL)

**Are the exposed credentials real?**

```bash
# Test if database password works
psql postgresql://panel:prod_password@prod-db:5432/panel

# Check production environment
ssh production-server
echo $DATABASE_URL
# Compare with config file
```

**If credentials are REAL** ? Follow "Emergency Response" below  
**If credentials are PLACEHOLDERS** ? Continue with standard remediation

---

### Priority 2: COMMIT CHANGES (IMMEDIATE)

```bash
# Stage all changes
git add .gitignore
git add config/*.template
git add docs/SECURITY_AUDIT_REPORT.md
git add tools/scripts/remove_secrets_from_git.sh

# Commit
git commit -m "security: remove config files with secrets and add templates

- Removed config.production.json from git tracking
- Removed config.staging.json from git tracking  
- Added secure template files (.template)
- Created comprehensive security audit report
- Gitignore already prevents future commits

See docs/SECURITY_AUDIT_REPORT.md for complete audit"

# Push
git push origin main
```

---

### Priority 3: REMOVE FROM GIT HISTORY (HIGH)

**?? WARNING**: This rewrites git history. Coordinate with team first!

#### Option A: BFG Repo-Cleaner (RECOMMENDED)

```bash
# Install BFG
brew install bfg  # macOS
# or download from https://rtyley.github.io/bfg-repo-cleaner/

# Backup
git clone --mirror https://github.com/phillgates2/panel panel-backup.git

# Remove files
bfg --delete-files config.production.json panel-backup.git
bfg --delete-files config.staging.json panel-backup.git

# Cleanup
cd panel-backup.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (DANGEROUS - warn team!)
git push --force
```

#### Option B: git filter-branch

```bash
# Create backup first
git clone https://github.com/phillgates2/panel panel-backup

# Remove files from history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch config/config.production.json config/config.staging.json' \
  --prune-empty --tag-name-filter cat -- --all

# Cleanup
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Verify
git log --all --full-history -- config/*.json
# Should show no results

# Force push (DANGEROUS - warn team!)
git push origin --force --all
git push origin --force --tags
```

#### Option C: Start Fresh (NUCLEAR OPTION)

If repository is new or team agrees:

```bash
# 1. Export clean state
git checkout main
git archive --format=tar HEAD | tar -x -C /tmp/panel-clean

# 2. Remove .git
rm -rf .git

# 3. Initialize new repo
git init
git add .
git commit -m "Initial commit (history cleaned)"

# 4. Force push
git remote add origin https://github.com/phillgates2/panel
git push --force origin main
```

---

### Priority 4: UPDATE DEPLOYMENT (HIGH)

#### For Production:

1. **Set Environment Variables**:
```bash
# On production server
export DATABASE_URL="postgresql://panel:NEW_SECURE_PASSWORD@prod-db:5432/panel"
export REDIS_URL="redis://prod-redis:6379/0"
export GOOGLE_CLIENT_ID="real-google-client-id"
export GOOGLE_CLIENT_SECRET="real-google-client-secret"
export GITHUB_CLIENT_ID="real-github-client-id"
export GITHUB_CLIENT_SECRET="real-github-client-secret"
```

2. **Or use .env file** (NOT in git):
```bash
# /opt/panel/.env.production (chmod 600)
DATABASE_URL=postgresql://panel:NEW_SECURE_PASSWORD@prod-db:5432/panel
REDIS_URL=redis://prod-redis:6379/0
GOOGLE_CLIENT_ID=real-google-client-id
GOOGLE_CLIENT_SECRET=real-google-client-secret
```

3. **Update application to load from env**:
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
REDIS_URL = os.getenv('REDIS_URL')
```

---

### Priority 5: ENABLE SECRET SCANNING (MEDIUM)

#### GitHub Secret Scanning:

For public repos (already enabled):
- GitHub automatically scans for secrets
- Receives alerts for exposed credentials

For private repos:
1. Go to repository Settings
2. Security & analysis
3. Enable "Secret scanning"
4. Enable "Push protection"

#### Pre-commit Hooks:

```bash
# Install git-secrets
brew install git-secrets  # macOS
apt-get install git-secrets  # Ubuntu

# Setup in repo
cd /path/to/panel
git secrets --install
git secrets --register-aws

# Add custom patterns
git secrets --add 'password.*=.*"[^"]{8,}"'
git secrets --add 'client_secret.*=.*"[^"]{8,}"'
git secrets --add 'postgresql://[^:]+:[^@]+@'
```

#### Pre-commit Hook Script:

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Check for secrets before commit

if git diff --cached --name-only | grep -q "config.*\.json$"; then
  echo "??  Checking for secrets in config files..."
  
  if git diff --cached config/ | grep -E "(password|secret|key).*[:=].*['\"][^'\"]{8,}"; then
    echo ""
    echo "? ERROR: Potential secret found in config file!"
    echo ""
    echo "Please:"
    echo "1. Remove the secret"
    echo "2. Use environment variables or .env files"
    echo "3. Update .gitignore"
    echo ""
    exit 1
  fi
fi

echo "? No secrets detected"
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## EMERGENCY RESPONSE

### If Real Credentials Were Exposed:

#### Immediate Actions (Within 1 Hour):

1. **Rotate Database Password**:
```sql
-- On production database
ALTER USER panel WITH PASSWORD 'NEW-SECURE-PASSWORD-HERE';

-- Update connection strings everywhere
-- - Production servers
-- - CI/CD secrets
-- - Team password managers
```

2. **Rotate OAuth Secrets**:

**Google**:
- Go to https://console.cloud.google.com/
- APIs & Services ? Credentials
- Find your OAuth client
- Click "Reset Secret"
- Update everywhere

**GitHub**:
- Go to https://github.com/settings/developers
- OAuth Apps ? Your App
- "Generate a new client secret"
- Update everywhere

3. **Audit Access Logs**:
```sql
-- Check for unauthorized database access
SELECT * FROM pg_stat_activity WHERE usename = 'panel';
SELECT * FROM pg_stat_statements ORDER BY calls DESC LIMIT 50;
```

4. **Notify Team**:
```
Subject: URGENT - Security Incident - Credentials Rotated

Team,

We discovered hardcoded credentials in our git repository that may have
been exposed. As a precaution, we have rotated:

- Database password
- Google OAuth secrets  
- GitHub OAuth secrets

Action required:
1. Pull latest code
2. Update your local .env files
3. Check password manager for new credentials
4. Report any suspicious activity

Timeline:
- Exposure: Since Nov 23, 2025
- Discovery: Dec 2024
- Remediation: Dec 2024

See docs/SECURITY_AUDIT_REPORT.md for details.
```

#### Follow-up Actions (Within 24 Hours):

5. **Audit User Accounts**:
```sql
-- Check for suspicious new users
SELECT * FROM users WHERE created_at > '2025-11-23' ORDER BY created_at DESC;

-- Check for privilege escalations
SELECT * FROM audit_log WHERE action = 'ROLE_CHANGE' AND created_at > '2025-11-23';
```

6. **Review Application Logs**:
```bash
# Check for unusual activity
grep -i "authentication failed" /var/log/panel/*.log | grep -A 5 "2025-11-2[3-9]"
grep -i "unauthorized" /var/log/panel/*.log
```

7. **Document Incident**:
- What was exposed
- How long it was exposed
- Who had access
- What actions were taken
- Lessons learned

---

## PREVENTION CHECKLIST

### Immediate (Done):
- [x] Create security audit report
- [x] Remove files from git tracking
- [x] Create template files
- [x] Update gitignore
- [ ] Commit and push changes

### Short Term (This Week):
- [ ] Verify credentials are not real
- [ ] Remove from git history
- [ ] Enable secret scanning
- [ ] Add pre-commit hooks
- [ ] Update deployment docs

### Medium Term (This Month):
- [ ] Implement secrets management (Vault/AWS Secrets Manager)
- [ ] Security training for team
- [ ] Update security policies
- [ ] Regular security audits

### Long Term (Next Quarter):
- [ ] Automated security scanning in CI/CD
- [ ] Regular penetration testing
- [ ] Security incident response plan
- [ ] Compliance certification (SOC 2, ISO 27001)

---

## VERIFICATION

After completing remediation:

```bash
# 1. Verify files not in git
git ls-files config/*.json
# Should only show .template files

# 2. Verify no secrets in history
git log --all --full-history -- config/config.production.json
# Should show removal commit only

# 3. Verify gitignore works
touch config/config.production.json
git status
# Should not show in untracked files

# 4. Verify templates exist
ls -la config/*.template
# Should show both templates

# 5. Test application with env vars
export DATABASE_URL="postgresql://user:pass@localhost/db"
python -c "from config import config; print(config.DATABASE_URL)"
# Should print the env var
```

---

## RESOURCES

### Documentation:
- `docs/SECURITY_AUDIT_REPORT.md` - Full audit report
- `docs/CONFIG_FOLDER_ANALYSIS.md` - Config system analysis
- `.github/SECRETS.md` - Required secrets for CI/CD
- `.env.example` - Environment variable template

### Scripts:
- `tools/scripts/remove_secrets_from_git.sh` - Automated removal
- `cleanup.sh` - Workspace verification

### External Resources:
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [git-secrets](https://github.com/awslabs/git-secrets)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [12 Factor App - Config](https://12factor.net/config)

---

## NEXT STEPS

1. **Commit Changes** (see Priority 2 above)
2. **Push to GitHub**
3. **Verify Credentials** (see Priority 1)
4. **Remove from History** (see Priority 3 if needed)
5. **Update Deployment** (see Priority 4)

---

**Status**: Ready to commit and push  
**Risk Level**: MEDIUM (assuming placeholders)  
**Action Required**: Follow priorities 1-5 above  
**Timeline**: Complete within 1 week
