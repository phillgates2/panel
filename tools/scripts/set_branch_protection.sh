#!/usr/bin/env bash
set -euo pipefail

# set_branch_protection.sh
# Usage:
#   GITHUB_TOKEN=ghp_xxx bash tools/scripts/set_branch_protection.sh owner repo branch "context1,context2"
# Example:
#   GITHUB_TOKEN=$TOKEN bash tools/scripts/set_branch_protection.sh phillgates2 panel main "pip-audit-gate,Dependency Updates"

if [ "$#" -lt 4 ]; then
  echo "Usage: GITHUB_TOKEN=token $0 <owner> <repo> <branch> \"context1,context2\""
  exit 1
fi

OWNER="$1"
REPO="$2"
BRANCH="$3"
CONTEXTS_CSV="$4"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "Error: GITHUB_TOKEN environment variable must be set with a personal access token with repo admin permissions"
  exit 1
fi

API_URL="https://api.github.com/repos/$OWNER/$REPO/branches/$BRANCH/protection"
HEADER_AUTH="Authorization: token $GITHUB_TOKEN"
HEADER_ACCEPT="Accept: application/vnd.github+json"

# Backup current protection (if any)
echo "Fetching existing branch protection for $OWNER/$REPO:$BRANCH (if exists)"
curl -sS -H "$HEADER_AUTH" -H "$HEADER_ACCEPT" "$API_URL" -o /tmp/branch_protection_backup.json || true
if [ -s /tmp/branch_protection_backup.json ]; then
  echo "Saved existing protection to /tmp/branch_protection_backup.json"
else
  echo "No existing protection or fetch failed; continuing"
fi

# Build contexts array from CSV
IFS=',' read -r -a CONTEXTS_ARR <<< "$CONTEXTS_CSV"
CONTEXTS_JSON="[]"
CONTEXTS_JSON="["
first=true
for c in "${CONTEXTS_ARR[@]}"; do
  trimmed=$(echo "$c" | sed 's/^\s*//;s/\s*$//')
  if [ -z "$trimmed" ]; then
    continue
  fi
  if [ "$first" = true ]; then
    CONTEXTS_JSON+="\"$trimmed\""
    first=false
  else
    CONTEXTS_JSON+=",\"$trimmed\""
  fi
done
CONTEXTS_JSON+="]"

# Compose protection body
read -r -d '' BODY <<EOF || true
{
  "required_status_checks": {
    "strict": true,
    "contexts": $CONTEXTS_JSON
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null
}
EOF

# Apply protection
echo "Applying branch protection to $OWNER/$REPO:$BRANCH with contexts: $CONTEXTS_CSV"
curl -sS -X PUT -H "$HEADER_AUTH" -H "$HEADER_ACCEPT" -d "$BODY" "$API_URL" -o /tmp/branch_protection_result.json

if grep -q '"message"' /tmp/branch_protection_result.json 2>/dev/null; then
  echo "Result:"
  cat /tmp/branch_protection_result.json
  echo "If you see an error about 'resource not accessible by integration' or permission denied, ensure the GITHUB_TOKEN has 'repo' admin scopes or use a token with admin rights."
  exit 1
fi

echo "Branch protection applied successfully. Backup saved at /tmp/branch_protection_backup.json"
exit 0
