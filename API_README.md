# Panel REST API

The Panel provides a comprehensive REST API for programmatic access to server management features.

## Quick Start

1. **Generate an API Token**
   - Log in to the panel
   - Navigate to "API Tokens" in the menu
   - Click "Generate New Token"
   - Copy the token (keep it secure!)

2. **Make your first API call**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
        http://your-panel-url/api/v1/servers
   ```

## Authentication

All API requests require authentication using Bearer tokens:

```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     http://your-panel-url/api/v1/endpoint
```

## Endpoints

### Servers

#### List Servers
```http
GET /api/v1/servers
```

**Response:**
```json
{
  "servers": [
    {
      "id": 1,
      "name": "My Server",
      "host": "127.0.0.1",
      "port": 27960,
      "game_type": "etlegacy",
      "status": "online",
      "player_count": 5,
      "max_players": 32,
      "map": "oasis",
      "created_at": "2025-11-20T10:00:00Z",
      "updated_at": "2025-11-20T10:30:00Z"
    }
  ],
  "total": 1,
  "api_version": "v1"
}
```

#### Get Server Details
```http
GET /api/v1/servers/{server_id}
```

#### Send RCON Command
```http
POST /api/v1/servers/{server_id}/command
Content-Type: application/json

{
  "command": "status"
}
```

**Response:**
```json
{
  "success": true,
  "command": "status",
  "response": "map: oasis\nplayers: 5\n...",
  "timestamp": "2025-11-20T10:30:00Z"
}
```

### Webhooks

#### Receive Webhook
```http
POST /api/v1/webhooks
Content-Type: application/json

{
  "type": "player_event",
  "server_id": 1,
  "player_name": "Player123",
  "event": "join",
  "timestamp": "2025-11-20T10:30:00Z"
}
```

### Health Check

#### API Health
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-20T10:30:00Z",
  "version": "1.0.0",
  "api_version": "v1"
}
```

## Rate Limits

- **Server List/Details**: 60/120 requests per minute
- **RCON Commands**: 30 requests per minute
- **Webhooks**: 1000 requests per minute
- **Health Checks**: 1000 requests per minute

## Error Codes

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (access denied)
- `404` - Not Found
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

## Testing

Use the included testing script:

```bash
python api_test.py --token YOUR_TOKEN --base-url http://your-panel-url
```

Or test manually with curl:

```bash
# Health check
curl http://your-panel-url/api/v1/health

# List servers
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://your-panel-url/api/v1/servers

# Send command
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"command": "status"}' \
     http://your-panel-url/api/v1/servers/1/command
```

## SDKs and Libraries

### Python
```python
import requests

class PanelAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })

    def get_servers(self):
        response = self.session.get(f'{self.base_url}/api/v1/servers')
        return response.json()

    def send_command(self, server_id, command):
        data = {'command': command}
        response = self.session.post(
            f'{self.base_url}/api/v1/servers/{server_id}/command',
            json=data
        )
        return response.json()

# Usage
api = PanelAPI('http://your-panel-url', 'your_token')
servers = api.get_servers()
result = api.send_command(1, 'status')
```

## Webhook Integration

Set up webhooks to receive real-time notifications:

1. Configure your external service to POST to `/api/v1/webhooks`
2. Handle different event types in your application

**Example webhook payload:**
```json
{
  "type": "player_event",
  "server_id": 1,
  "player_name": "Player123",
  "event": "join",
  "timestamp": "2025-11-20T10:30:00Z"
}
```

## Security Best Practices

1. **Keep tokens secure** - Never commit tokens to version control
2. **Use HTTPS** - Always use HTTPS in production
3. **Rotate tokens regularly** - Generate new tokens periodically
4. **Monitor usage** - Check token last-used times in the panel
5. **Rate limiting** - Respect API rate limits to avoid being blocked

## Support

For API support:
- Check the API documentation in the panel (`/api/docs`)
- Review the testing script for examples
- Check server logs for detailed error information
