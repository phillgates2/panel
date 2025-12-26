# Branch Protection Guidance

This repository added a new CI status check workflow `pip-audit-gate` that runs `pip-audit` on pull requests and fails the check if any HIGH or CRITICAL Python dependency vulnerabilities are detected.

To enforce this check and block merges when the gate fails, add a branch protection rule for `main` with the following settings:

1. Go to: https://github.com/<owner>/<repo>/settings/branches
2. Click "Add branch protection rule" and set: Branch name pattern: `main`
3. Under "Protect matching branches":
   - Require a pull request before merging: checked
   - Require approvals: as appropriate (e.g., 1 or 2 reviewers)
   - Require status checks to pass before merging: checked
     - Select the following required status checks:
       - `pip-audit-gate` (the job name appears as a status check)
       - Any other checks you already require (e.g., `ci/cd`, `code-quality`)
   - Include administrators: optional (recommended to block direct pushes)
4. Save the branch protection rule.

Notes:
- The `pip-audit-gate` workflow is triggered on pull requests and will create a failing status if pip-audit reports HIGH/CRITICAL issues. Marking it as a required check prevents merging PRs that introduce critical dependency vulnerabilities.
- If you use additional CI workflows that must pass before merging, add them as required checks too.
- If you use GitHub Apps or different names for checks, confirm the exact status check label shown in PRs and add that to the required list.

Automation tip (optional): Use the GitHub REST API or terraform/github provider to programmatically create branch protection rules for automation and reproducibility.
