# GitHub Secrets Configuration Guide

This document lists all secrets required for the Panel application's GitHub Actions workflows.

## Overview

Secrets are encrypted environment variables used by GitHub Actions workflows. They should never be committed to the repository.

## How to Add Secrets

1. Go to repository **Settings** ? **Secrets and variables** ? **Actions**
2. Click **"New repository secret"**
3. Enter the secret name and value
4. Click **"Add secret"**

For environment-specific secrets:
1. Go to **Settings** ? **Environments**
2. Create or select an environment (staging/production)
3. Add environment-specific secrets

---

## Required Secrets

### Core CI/CD Secrets

#### `CODECOV_TOKEN` (Optional)
- **Purpose**: Upload code coverage reports to Codecov
- **Used in**: `ci-cd.yml`
- **Required**: No (workflow continues without it)
- **How to get**: 
  1. Sign up at [codecov.io](https://codecov.io)
  2. Link your repository
  3. Copy the upload token
- **Example**: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

---

### Docker Registry Secrets

#### `DOCKER_USERNAME`
- **Purpose**: Docker Hub username for pushing images
- **Used in**: `release.yml`
- **Required**: Yes (for releases)
- **How to get**: Your Docker Hub username
- **Example**: `myusername`

#### `DOCKER_PASSWORD`
- **Purpose**: Docker Hub password or access token (recommended)
- **Used in**: `release.yml`
- **Required**: Yes (for releases)
- **How to get**: 
  1. Go to Docker Hub ? Account Settings ? Security
  2. Create New Access Token
  3. Copy the token (not your password)
- **Example**: `dckr_pat_1234567890abcdef`
- **Security note**: Use access tokens instead of passwords

---

### AWS Deployment Secrets

#### `AWS_ACCESS_KEY_ID`
- **Purpose**: AWS access key for staging environment
- **Used in**: `aws-deploy.yml`
- **Required**: Yes (for AWS deployment)
- **How to get**:
  1. Go to AWS IAM ? Users ? Your user
  2. Security credentials tab
  3. Create access key
- **Example**: `AKIAIOSFODNN7EXAMPLE`
- **Permissions needed**:
  - `ecr:*` - ECR repository access
  - `ecs:*` - ECS service updates
  - `elasticloadbalancing:*` - Load balancer access
  - `cloudwatch:*` - CloudWatch logs

#### `AWS_SECRET_ACCESS_KEY`
- **Purpose**: AWS secret key for staging environment
- **Used in**: `aws-deploy.yml`
- **Required**: Yes (for AWS deployment)
- **Example**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
- **Security note**: Never share or commit this key

#### `AWS_ACCESS_KEY_ID_PROD`
- **Purpose**: AWS access key for production environment
- **Used in**: `aws-deploy.yml` (production deploy)
- **Required**: Yes (for production deployment)
- **Security note**: Use separate AWS account or IAM user for production
- **Best practice**: Use AWS Organizations with separate accounts

#### `AWS_SECRET_ACCESS_KEY_PROD`
- **Purpose**: AWS secret key for production environment
- **Used in**: `aws-deploy.yml` (production deploy)
- **Required**: Yes (for production deployment)
- **Security note**: Rotate these keys every 90 days

---

### Notification Secrets

#### `SLACK_WEBHOOK`
- **Purpose**: General Slack webhook for deployment notifications
- **Used in**: `aws-deploy.yml`, `release.yml`
- **Required**: No (workflows continue without it)
- **How to get**:
  1. Go to Slack workspace ? Apps ? Incoming Webhooks
  2. Create new webhook
  3. Select channel (#deployments recommended)
  4. Copy webhook URL
- **Example**: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`

#### `SLACK_SECURITY_WEBHOOK_URL`
- **Purpose**: Slack webhook for security alerts
- **Used in**: `security-monitoring.yml`
- **Required**: No
- **Recommended**: Use separate channel (#security-alerts)
- **Example**: `https://hooks.slack.com/services/T00000000/B00000000/YYYYYYYYYYYYYYYYYYYY`

#### `SLACK_RELEASE_WEBHOOK_URL`
- **Purpose**: Slack webhook for release announcements
- **Used in**: `release.yml`
- **Required**: No
- **Recommended**: Use separate channel (#releases)
- **Example**: `https://hooks.slack.com/services/T00000000/B00000000/ZZZZZZZZZZZZZZZZZZZZ`

#### `EMAIL_USERNAME`
- **Purpose**: SMTP username for sending email notifications
- **Used in**: `aws-deploy.yml` (failure notifications)
- **Required**: No
- **Example**: `notifications@yourdomain.com`
- **Recommended**: Use SendGrid, AWS SES, or Gmail App Password

#### `EMAIL_PASSWORD`
- **Purpose**: SMTP password for sending emails
- **Used in**: `aws-deploy.yml`
- **Required**: No
- **Example**: `app-specific-password-1234`
- **Security note**: Use app-specific passwords, not account passwords

#### `ALERT_EMAILS`
- **Purpose**: Comma-separated list of email addresses for critical alerts
- **Used in**: `aws-deploy.yml`
- **Required**: No
- **Example**: `admin@example.com,devops@example.com,oncall@example.com`

---

### GitHub Tokens

#### `GITHUB_TOKEN`
- **Purpose**: Automatically provided by GitHub Actions
- **Used in**: Multiple workflows
- **Required**: Yes (automatically available)
- **How to get**: Automatically provided - no action needed
- **Permissions**: Configured in workflow files
- **Note**: This is NOT a secret you need to add

#### `GH_TOKEN` (Optional)
- **Purpose**: Personal Access Token for advanced GitHub API operations
- **Used in**: Release workflows (if standard token lacks permissions)
- **Required**: No (only if `GITHUB_TOKEN` permissions are insufficient)
- **How to get**:
  1. Go to GitHub Settings ? Developer settings ? Personal access tokens
  2. Generate new token (classic)
  3. Select scopes: `repo`, `write:packages`, `workflow`
- **Example**: `ghp_1234567890abcdefghijklmnopqrstuvwxyz`

---

## Environment-Specific Secrets

### Staging Environment

Create in: Settings ? Environments ? staging

- `AWS_ACCESS_KEY_ID` (staging-specific)
- `AWS_SECRET_ACCESS_KEY` (staging-specific)
- Database credentials (if needed)
- API keys for staging services

### Production Environment

Create in: Settings ? Environments ? production

- `AWS_ACCESS_KEY_ID_PROD`
- `AWS_SECRET_ACCESS_KEY_PROD`
- Database credentials (if needed)
- API keys for production services
- **Require reviewers**: Enable this for production safety

---

## Security Best Practices

### 1. Secret Rotation

Rotate secrets regularly:
- **AWS keys**: Every 90 days
- **Tokens**: Every 6 months
- **Webhooks**: As needed
- **Passwords**: Every 90 days

### 2. Least Privilege

- Use IAM roles with minimal required permissions
- Create separate AWS users for staging and production
- Use AWS Organizations for account isolation

### 3. Monitoring

- Enable AWS CloudTrail for API call logging
- Monitor secret usage in Actions logs
- Set up alerts for unusual activity

### 4. Backup & Recovery

- Document all secrets in a secure password manager
- Keep emergency contact list for credential resets
- Test secret rotation procedures

### 5. Never Commit Secrets

```bash
# Add to .gitignore
.env
.env.local
.env.*.local
secrets.yml
*.key
*.pem
```

---

## Verification Checklist

Use this checklist to verify your secrets are properly configured:

### Required for Basic CI/CD
- [ ] `GITHUB_TOKEN` (automatically provided)
- [ ] No additional secrets needed for basic testing

### Required for Docker Releases
- [ ] `DOCKER_USERNAME`
- [ ] `DOCKER_PASSWORD`

### Required for AWS Deployment
- [ ] `AWS_ACCESS_KEY_ID`
- [ ] `AWS_SECRET_ACCESS_KEY`
- [ ] `AWS_ACCESS_KEY_ID_PROD`
- [ ] `AWS_SECRET_ACCESS_KEY_PROD`

### Optional but Recommended
- [ ] `CODECOV_TOKEN`
- [ ] `SLACK_WEBHOOK`
- [ ] `SLACK_SECURITY_WEBHOOK_URL`
- [ ] `SLACK_RELEASE_WEBHOOK_URL`
- [ ] `EMAIL_USERNAME`
- [ ] `EMAIL_PASSWORD`
- [ ] `ALERT_EMAILS`

---

## Testing Secrets

### Test Slack Webhooks

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test message from Panel CI/CD"}' \
  YOUR_SLACK_WEBHOOK_URL
```

### Test AWS Credentials

```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="us-east-1"

aws sts get-caller-identity
```

### Test Docker Credentials

```bash
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
```

---

## Troubleshooting

### Secret Not Found Error

```
Error: The secret `SECRET_NAME` was not found
```

**Solution**: 
1. Verify secret is created in repository settings
2. Check secret name matches exactly (case-sensitive)
3. For environment secrets, ensure workflow specifies environment

### Permission Denied Error

```
Error: Permission denied (publickey)
```

**Solution**:
1. Verify AWS IAM permissions
2. Check key is not expired
3. Verify secret value is correct (no extra spaces)

### Webhook Not Receiving Notifications

**Solution**:
1. Test webhook URL manually (see Testing Secrets above)
2. Verify workflow is actually running
3. Check Slack channel permissions
4. Verify webhook is not rate-limited

---

## Secrets Management Tools

For team environments, consider using:

1. **AWS Secrets Manager**
   - Centralized secret storage
   - Automatic rotation
   - Fine-grained access control

2. **HashiCorp Vault**
   - Dynamic secrets
   - Audit logging
   - Multi-cloud support

3. **1Password for Teams**
   - Shared secret management
   - Emergency access
   - Audit trails

---

## Emergency Procedures

### Lost or Compromised Secret

1. **Immediately rotate the secret**:
   - Generate new key/token
   - Update in GitHub Secrets
   - Revoke old key/token

2. **Check for unauthorized access**:
   - Review AWS CloudTrail logs
   - Check Docker Hub activity
   - Review GitHub Actions logs

3. **Update dependent services**:
   - Update local development environments
   - Notify team members
   - Update documentation

### Workflow Fails Due to Secret Issue

1. **Verify secret exists**: Settings ? Secrets ? Actions
2. **Check secret name**: Must match exactly in workflow
3. **Test secret locally**: Use testing procedures above
4. **Check workflow permissions**: Ensure environment access is granted
5. **Review workflow logs**: Look for specific error messages

---

## Additional Resources

- [GitHub Actions Encrypted Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Docker Hub Access Tokens](https://docs.docker.com/docker-hub/access-tokens/)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)

---

## Support

For questions about secrets configuration:
1. Check this documentation first
2. Review workflow logs for specific errors
3. Consult team lead or DevOps engineer
4. Create issue in repository with [secrets] tag

---

**Last Updated**: $(date)
**Maintainer**: DevOps Team
**Version**: 1.0
