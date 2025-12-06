# SECURITY AUDIT REPORT - Config Files

## ?? CRITICAL FINDINGS

### Date: December 2024
### Auditor: Automated Security Scan
### Status: **CRITICAL ISSUES FOUND**

---

## EXECUTIVE SUMMARY

**Status**: ?? **CRITICAL** - Hardcoded credentials found in git history  
**Severity**: HIGH  
**Immediate Action Required**: YES

### Summary of Findings:
- **3 files** contain hardcoded credentials
- **Exposed in git history** since commit 4b00701 (Nov 23, 2025)
- **Database passwords** exposed
- **OAuth secrets** exposed (placeholder values)
- **Risk Level**: MEDIUM-HIGH

---

## DETAILED FINDINGS

### 1. ?? CRITICAL: config/config.production.json

**Issue**: Hardcoded database password in production config

```json
"database_url": "postgresql://panel:prod_password@prod-db:5432/panel"
```

**Details**:
- Password: `prod_password` (hardcoded)
- OAuth secrets: `prod-google-client-secret`, `prod-github-client-secret` (placeholders)
- Exposed in git history: YES
- First appearance: commit 4b00701

**Risk Assessment**:
- If these are real production credentials: **CRITICAL**
- If these are placeholders: **MEDIUM** (still bad practice)

**Recommendation**:
1. Verify if `prod_password` is the actual production password
2. If YES: Rotate database password IMMEDIATELY
3. If NO: Still remove from git and use env vars
4. Rotate all OAuth secrets as a precaution

---

### 2. ?? MEDIUM: config/config.staging.json

**Issue**: Hardcoded database password in staging config

```json
"database_url": "postgresql://panel:staging_password@staging-db:5432/panel"
```

**Details**:
- Password: `staging_password` (hardcoded)
- OAuth secrets: `staging-google-client-secret`, `staging-github-client-secret` (placeholders)
- Exposed in git history: YES
- First appearance: commit 4b00701

**Risk Assessment**:
- If these are real staging credentials: **HIGH**
- If these are placeholders: **MEDIUM**

**Recommendation**:
1. Verify if actual staging credentials
2. Rotate if real
3. Remove from git and use env vars

---

### 3. ?? LOW: config/config.development.json

**Issue**: Placeholder OAuth secrets (not real credentials)

```json
"client_id": "dev-google-client-id",
"client_secret": "dev-google-client-secret"
```

**Details**:
- Database: SQLite (no password)
- OAuth secrets: Clear placeholders
- Exposed in git history: YES

**Risk Assessment**: **LOW** (these are clearly placeholders)

**Recommendation**:
- Keep as documentation/examples
- Consider renaming to .example extension

---

### 4. ? SAFE: config/config.testing.json

**Issue**: None

**Details**:
- Database: SQLite (no password)
- OAuth providers: Empty object
- No credentials present

**Status**: ? SAFE

---

## GIT HISTORY ANALYSIS

### Commits Containing Credentials:

```bash
$ git log --all --full-history -- config/*.json

commit 4b007018bdb87b5de776ce20dff5f9f5924b5919
Author: phillgates2 <phillgates2@gmail.com>
Date:   Sun Nov 23 19:43:50 2025 +1000
    Fix linting warnings and code quality issues
```

**Analysis**:
- Config files with credentials have been in git since Nov 23, 2025
- Repository is public: https://github.com/phillgates2/panel
- Credentials have been exposed for ~1 month

**Impact**:
- If real credentials: Anyone with repo access can see them
- If public repo: Entire internet can see them

---

## IMMEDIATE ACTIONS REQUIRED

### Priority 1: CRITICAL (Do NOW)

1. **Verify Credential Status**:
```bash
# Check if production password is real
ssh prod-db
psql -U panel -d panel
# Try password: prod_password
```

2. **If Real Credentials Found**:
```bash
# Rotate database password immediately
ALTER USER panel WITH PASSWORD 'new-secure-password-here';

# Rotate OAuth secrets
# - Google Cloud Console: Regenerate credentials
# - GitHub Settings: Regenerate OAuth app secrets
```

3. **Update .gitignore** (Already done ?):
```
config/config.*.json
config/config.local.json
```

4. **Remove from Git History**:
```bash
# WARNING: This rewrites history - coordinate with team
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch config/config.production.json \
   config/config.staging.json' \
  --prune-empty --tag-name-filter cat -- --all

# Force push (DANGEROUS - warn team first)
git push origin --force --all
```

### Priority 2: HIGH (Do Today)

5. **Create Template Files**:
```bash
# Rename existing files to templates
mv config/config.production.json config/config.production.json.template
mv config/config.staging.json config/config.staging.json.template

# Update templates to use env var placeholders
```

6. **Update Config Loading**:
```python
# Use environment variables instead
DATABASE_URL = os.getenv('DATABASE_URL')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
```

7. **Document Required Secrets**:
```bash
# Create .env.example with all required vars
# Already done ? - see .env.example
```

### Priority 3: MEDIUM (This Week)

8. **Security Audit Log**:
- Document this incident
- Record what actions were taken
- Update security policies

9. **Team Notification**:
- Notify team about credential rotation
- Update deployment documentation
- Train on secrets management

10. **Implement Secret Scanning**:
```yaml
# .github/workflows/security.yml
- uses: trufflesecurity/trufflehog@main
```

---

## RECOMMENDED FIXES

### Option 1: Use Environment Variables (RECOMMENDED)

**Remove JSON configs entirely**, use env vars:

```python
# config/base.py
DATABASE_URL = os.getenv('PANEL_DATABASE_URL')
GOOGLE_CLIENT_ID = os.getenv('PANEL_GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('PANEL_GOOGLE_CLIENT_SECRET')
```

**Advantages**:
- No secrets in git
- 12-factor app compliant
- Works with Docker, K8s, cloud platforms

**Disadvantages**:
- More env vars to manage
- Requires .env files for local dev

### Option 2: Template Files (ACCEPTABLE)

**Keep JSON configs as templates**:

```json
// config/config.production.json.template
{
  "database_url": "${DATABASE_URL}",
  "oauth_providers": {
    "google": {
      "client_id": "${GOOGLE_CLIENT_ID}",
      "client_secret": "${GOOGLE_CLIENT_SECRET}"
    }
  }
}
```

**Advantages**:
- Clear structure
- Easy to see what's needed

**Disadvantages**:
- Requires processing templates
- Two sources of truth

### Option 3: Secrets Management (BEST FOR PRODUCTION)

**Use dedicated secrets manager**:

- **AWS Secrets Manager**
- **Azure Key Vault**
- **HashiCorp Vault**
- **Google Secret Manager**

**Advantages**:
- Centralized secrets
- Automatic rotation
- Audit logging
- Access control

**Disadvantages**:
- Additional infrastructure
- Cost
- Complexity

---

## CREDENTIAL ASSESSMENT

### Are These Real Credentials?

**Evidence AGAINST (likely placeholders)**:
- `prod_password` - too simple for production
- `staging_password` - obvious placeholder
- `dev-google-client-id` - clearly marked as dev
- Pattern suggests these are examples

**Evidence FOR (might be real)**:
- In production config file
- Not marked as .example or .template
- Specific service URLs (smtp.panel.com)

**Verdict**: **LIKELY PLACEHOLDERS** but should be verified

### Verification Steps:

```bash
# 1. Check if database is accessible
psql postgresql://panel:prod_password@prod-db:5432/panel

# 2. Check if OAuth credentials work
curl -X POST https://oauth2.googleapis.com/token \
  -d "client_id=prod-google-client-id" \
  -d "client_secret=prod-google-client-secret" \
  -d "grant_type=client_credentials"

# 3. Check environment variables
echo $DATABASE_URL
echo $GOOGLE_CLIENT_SECRET
```

---

## FIXED FILES

I will now create secure versions of these config files:

### config/config.production.json.template
```json
{
  "name": "production",
  "debug": false,
  "testing": false,
  "database_url": "${DATABASE_URL}",
  "redis_url": "${REDIS_URL}",
  "mail_server": "${MAIL_SERVER}",
  "mail_port": 587,
  "mail_use_tls": true,
  "cdn_enabled": true,
  "cdn_url": "${CDN_URL}",
  "cdn_provider": "cloudflare",
  "oauth_providers": {
    "google": {
      "client_id": "${GOOGLE_CLIENT_ID}",
      "client_secret": "${GOOGLE_CLIENT_SECRET}"
    },
    "github": {
      "client_id": "${GITHUB_CLIENT_ID}",
      "client_secret": "${GITHUB_CLIENT_SECRET}"
    }
  }
}
```

---

## PREVENTION MEASURES

### 1. Pre-commit Hooks

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -q "config.*\.json$"; then
  if git diff --cached | grep -q "password\|secret\|key"; then
    echo "ERROR: Potential secret in config file"
    exit 1
  fi
fi
```

### 2. Git-secrets

```bash
# Install git-secrets
brew install git-secrets  # macOS
apt-get install git-secrets  # Ubuntu

# Setup
git secrets --install
git secrets --register-aws
git secrets --add 'password.*=.*[0-9a-zA-Z]{8,}'
```

### 3. GitHub Secret Scanning

Already enabled for public repos. For private repos:
- Settings ? Code security and analysis
- Enable "Secret scanning"

### 4. Code Review Checklist

- [ ] No passwords in code
- [ ] No API keys in code
- [ ] No OAuth secrets in code
- [ ] All secrets use env vars
- [ ] .env not in git
- [ ] .env.example documented

---

## SUMMARY & NEXT STEPS

### Security Score: ?? MEDIUM RISK

**What's Good**:
- ? Credentials appear to be placeholders
- ? .gitignore already updated
- ? .env.example created
- ? Development config safe

**What's Bad**:
- ?? Credentials in git history
- ?? Production config has hardcoded values
- ?? No secret scanning enabled
- ?? No pre-commit hooks

### Immediate Actions:
1. ? Verify credentials are placeholders
2. ? Create template files
3. ? Remove from git history
4. ? Add pre-commit hooks
5. ? Enable secret scanning

### Timeline:
- **TODAY**: Verify credentials, create templates
- **THIS WEEK**: Remove from git history, enable scanning
- **THIS MONTH**: Implement secrets manager

---

## CONCLUSION

**Status**: ?? **MEDIUM RISK** - Likely placeholders but needs verification

**Recommendation**: 
1. Verify credentials are not real (HIGH PRIORITY)
2. Move to template files or env vars (IMMEDIATE)
3. Remove from git history (URGENT)
4. Implement proper secrets management (IMPORTANT)

If credentials are verified as placeholders, risk drops to LOW.
If credentials are real, risk is CRITICAL and requires immediate action.

---

**Report Generated**: December 2024  
**Next Audit**: After remediation  
**Status**: AWAITING VERIFICATION AND REMEDIATION
