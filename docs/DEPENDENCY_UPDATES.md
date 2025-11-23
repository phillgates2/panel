# Automated Dependency Updates

This guide explains the automated dependency management setup using Dependabot and Renovate for the Panel application.

## Overview

The Panel application includes comprehensive dependency management with:

- **Dependabot**: GitHub's dependency update service
- **Renovate**: Advanced dependency automation
- **Security Updates**: Automated vulnerability patching
- **Update Scheduling**: Configurable update frequencies
- **Change Validation**: Automated testing and validation

## Dependabot Configuration

### Setup

Dependabot is configured via `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    reviewers:
      - "phillgates2"
    labels:
      - "dependencies"
      - "python"
```

### Features

#### Automated PR Creation
- **Weekly Updates**: Regular dependency checks
- **Security Alerts**: Immediate security patch PRs
- **Version Groups**: Group related package updates
- **Custom Labels**: Organized PR categorization

#### Update Types
- **Patch Updates**: Bug fixes and security patches
- **Minor Updates**: New features (backward compatible)
- **Major Updates**: Breaking changes (manual review required)

### Configuration Options

```yaml
# Package ecosystems
- package-ecosystem: "pip"        # Python
- package-ecosystem: "github-actions"  # GitHub Actions
- package-ecosystem: "docker"     # Docker images
- package-ecosystem: "npm"        # Node.js (for testing)

# Update schedules
schedule:
  interval: "weekly"    # daily, weekly, monthly
  day: "monday"        # For weekly updates
  time: "09:00"        # UTC time

# PR management
open-pull-requests-limit: 10    # Max open PRs
reviewers: ["username"]        # Required reviewers
assignees: ["username"]         # Auto-assign PRs

# Version constraints
ignore:
  - dependency-name: "flask"
    update-types: ["version-update:semver-major"]
```

## Renovate Configuration

### Advanced Features

Renovate provides more sophisticated dependency management:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:base",
    ":dependencyDashboard",
    ":semanticPrefixFixDepsChoreOthers",
    "group:monorepos",
    "group:recommended"
  ],
  "packageRules": [
    {
      "description": "Group Python dependencies",
      "matchManagers": ["pip_requirements"],
      "groupName": "Python dependencies"
    },
    {
      "description": "Security updates get priority",
      "matchUpdateTypes": ["patch"],
      "schedule": ["at any time"],
      "labels": ["security"]
    }
  ]
}
```

### Renovate Advantages

#### Intelligent Grouping
- **Monorepo Support**: Handle complex repository structures
- **Dependency Groups**: Update related packages together
- **Branch Management**: Create separate branches for different update types

#### Advanced Scheduling
- **Timezone Support**: Schedule updates in your timezone
- **Conditional Updates**: Update based on conditions
- **Dependency Dashboard**: Web interface for managing updates

## Security Updates

### Automated Security Patching

```yaml
# Dependabot security updates
vulnerabilityAlerts:
  enabled: true
  schedule: ["at any time"]
  labels: ["security", "vulnerability"]

# Renovate security handling
osvVulnerabilityAlerts: true
```

### Security Workflow

1. **Vulnerability Detection**: Automated scanning of dependencies
2. **PR Creation**: Immediate security update PRs
3. **Testing**: Automated test execution on security PRs
4. **Review**: Security team review and approval
5. **Deployment**: Automated deployment after approval

## Update Management Scripts

### Dependency Update Script

The `scripts/update-dependencies.sh` script provides manual control:

```bash
# Check for outdated packages
./scripts/update-dependencies.sh check

# Update specific package
./scripts/update-dependencies.sh update requests 2.28.0

# Run security audit
./scripts/update-dependencies.sh security

# Generate update report
./scripts/update-dependencies.sh report
```

### Features

#### Package Analysis
- **Outdated Detection**: Identify packages needing updates
- **Security Scanning**: Check for known vulnerabilities
- **Breaking Changes**: Identify potential breaking updates
- **Compatibility Checking**: Verify package compatibility

#### Update Strategies
- **Conservative**: Only patch and minor updates
- **Balanced**: Include major updates with testing
- **Aggressive**: Update all packages (with caution)

## CI/CD Integration

### Automated Testing

All dependency update PRs trigger automated testing:

```yaml
# GitHub Actions workflow
name: Dependency Updates
on:
  pull_request:
    paths:
      - 'requirements/**'
      - 'package.json'
      - 'Dockerfile'

jobs:
  test-updates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test dependency updates
        run: |
          pip install -r requirements/requirements-dev.txt
          python -m pytest tests/ -x
```

### Validation Checks

#### Pre-Merge Validation
- **Unit Tests**: Ensure functionality still works
- **Integration Tests**: Verify component interactions
- **E2E Tests**: Confirm end-to-end functionality
- **Performance Tests**: Check for performance regressions

#### Post-Merge Monitoring
- **Error Tracking**: Monitor for new errors
- **Performance Metrics**: Watch for performance changes
- **User Feedback**: Monitor user reports

## Best Practices

### Update Strategy

#### Risk-Based Updates
- **Critical Dependencies**: Update immediately (Flask, SQLAlchemy)
- **Development Tools**: Update regularly (pytest, black)
- **Optional Dependencies**: Update when needed

#### Testing Strategy
- **Automated Testing**: All updates must pass CI
- **Manual Testing**: Major updates require manual verification
- **Staging Deployment**: Test in staging before production

### Branch Management

```bash
# Dependabot branches
dependabot/pip/flask-2.3.0
dependabot/pip/requests-2.31.0
dependabot/security/pip/requests-2.28.1

# Renovate branches
renovate/flask-2.3.x
renovate/major-flask-monorepo
```

### PR Management

#### Labeling Strategy
- `dependencies`: All dependency updates
- `security`: Security-related updates
- `major`: Breaking changes requiring attention
- `patch`: Safe updates (patches and minor)

#### Review Process
- **Automated PRs**: Light review for patch/minor updates
- **Security PRs**: Priority review and immediate action
- **Major Updates**: Thorough review and testing

## Monitoring and Alerts

### Dependency Health

#### Dependency Dashboard
- **Outdated Packages**: Track packages needing updates
- **Security Vulnerabilities**: Monitor security issues
- **Update Frequency**: Track update cadence
- **Failure Rates**: Monitor update success rates

#### Metrics to Track
- **Update Success Rate**: Percentage of successful updates
- **Time to Update**: Average time from alert to deployment
- **Security Response Time**: Time to patch security issues
- **Breaking Change Frequency**: Rate of breaking updates

### Alert Configuration

```yaml
# Slack notifications for security updates
- name: Security Updates
  conditions:
    - labels: ["security"]
  actions:
    - slack_notification:
        channel: "#security"
        message: "Security update available: {{ .Title }}"

# Email alerts for major updates
- name: Major Updates
  conditions:
    - labels: ["major"]
  actions:
    - email_notification:
        to: ["dev-team@company.com"]
        subject: "Major dependency update requires review"
```

## Troubleshooting

### Common Issues

#### Update Conflicts
```bash
# Resolve merge conflicts
git checkout main
git pull origin main
git checkout dependabot/pr-branch
git rebase main
# Resolve conflicts manually
git add .
git rebase --continue
```

#### Test Failures
```bash
# Debug failing tests
pytest tests/ -v --tb=long
# Check dependency compatibility
pip check
# Review changelog for breaking changes
```

#### Security Scan Failures
```bash
# Check vulnerability details
safety check --full-report
# Review fix availability
pip list --outdated
# Consider temporary workarounds
```

### Recovery Procedures

#### Rollback Strategy
1. **Identify Issue**: Determine which update caused problems
2. **Revert Changes**: Rollback to previous version
3. **Pin Version**: Temporarily pin problematic dependency
4. **Investigate**: Find root cause and proper fix
5. **Reapply**: Update with corrected version

#### Emergency Updates
1. **Assess Impact**: Evaluate security risk vs. stability
2. **Test Fix**: Verify fix works in staging
3. **Schedule Update**: Plan deployment during low-traffic
4. **Monitor Closely**: Watch for issues post-deployment
5. **Document**: Record incident and resolution

## Advanced Configuration

### Custom Update Rules

```json
{
  "packageRules": [
    {
      "description": "Flask ecosystem careful updates",
      "matchPackageNames": ["flask", "flask-*", "werkzeug", "jinja2"],
      "schedule": ["before 4am on first day of month"],
      "groupName": "Flask ecosystem"
    },
    {
      "description": "Database libraries need testing",
      "matchPackageNames": ["sqlalchemy", "psycopg2", "pymysql"],
      "extends": ["schedule:monthly"],
      "groupName": "Database libraries"
    }
  ]
}
```

### Custom Managers

```yaml
# Custom package managers
updates:
  - package-ecosystem: "pip"
    directory: "/subproject"
    schedule:
      interval: "weekly"
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
```

### Integration with Tools

#### Pre-commit Hooks
```bash
# Check dependencies before commit
pre-commit run --all-files
```

#### Automated Merging
```yaml
# Auto-merge safe updates
pull-requests:
  auto-merge:
    - labels: ["dependencies", "patch"]
      required-status-checks: ["tests", "security"]
```

This automated dependency management system ensures the Panel application stays secure and up-to-date while minimizing manual maintenance overhead.