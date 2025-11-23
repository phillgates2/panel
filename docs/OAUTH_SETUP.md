# OAuth 2.0 Social Login Setup

This guide explains how to configure OAuth 2.0 social login for Google, GitHub, and Discord.

## Prerequisites

1. Install required dependencies:
   ```bash
   pip install -r requirements/requirements-dev.txt
   ```

2. Run database migration:
   ```bash
   make db-upgrade
   ```

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to "Credentials" ? "Create Credentials" ? "OAuth 2.0 Client IDs"
5. Set authorized redirect URI: `https://yourdomain.com/oauth/callback/google`
6. Set environment variables:
   ```bash
   export GOOGLE_CLIENT_ID="your_client_id"
   export GOOGLE_CLIENT_SECRET="your_client_secret"
   ```

## GitHub OAuth Setup

1. Go to GitHub Settings ? Developer settings ? OAuth Apps
2. Click "New OAuth App"
3. Set Authorization callback URL: `https://yourdomain.com/oauth/callback/github`
4. Set environment variables:
   ```bash
   export GITHUB_CLIENT_ID="your_client_id"
   export GITHUB_CLIENT_SECRET="your_client_secret"
   ```

## Discord OAuth Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "OAuth2" ? "General"
4. Add redirect: `https://yourdomain.com/oauth/callback/discord`
5. Set environment variables:
   ```bash
   export DISCORD_CLIENT_ID="your_client_id"
   export DISCORD_CLIENT_SECRET="your_client_secret"
   ```

## Configuration

Add to your `config.py`:

```python
# OAuth Configuration
OAUTH_ENABLED = True

# Google
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

# GitHub
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

# Discord
DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET')
```

## Testing

1. Start the application:
   ```bash
   make dev-server
   ```

2. Check OAuth setup:
   ```bash
   make oauth-setup
   ```

3. Visit login page and test social login buttons

## Security Considerations

- OAuth tokens are stored encrypted in the database
- Users can unlink social accounts from their profile
- Failed OAuth attempts are logged for security monitoring
- Rate limiting applies to OAuth endpoints

## Troubleshooting

### Common Issues

1. **"OAuth provider not configured"**
   - Check that client ID/secret environment variables are set
   - Verify the provider is enabled in config

2. **"Invalid OAuth access token"**
   - Check that redirect URIs match exactly
   - Verify client secret is correct

3. **"State parameter mismatch"**
   - This is usually a CSRF-related issue
   - Clear browser cookies and try again

### Logs

Check application logs for OAuth-related errors:
```bash
tail -f logs/panel.log | grep oauth
```

## User Experience

- Users can link multiple social accounts
- Social login works for both registration and login
- Users can unlink accounts from their profile
- Existing password accounts remain functional
- OAuth users get randomly generated passwords (can be changed later)