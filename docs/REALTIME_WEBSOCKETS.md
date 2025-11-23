# Real-time Features with WebSockets

This guide explains the real-time WebSocket features implemented in the Panel application.

## Overview

The Panel application includes comprehensive real-time features using Flask-SocketIO:

- **Live Forum Updates** - Instant post notifications and activity feeds
- **User Status Tracking** - Online/offline indicators
- **Server Monitoring** - Real-time server status updates
- **Typing Indicators** - See when users are typing
- **Push Notifications** - Browser notifications for important events

## Prerequisites

1. Install required dependencies:
   ```bash
   pip install -r requirements/requirements-dev.txt
   ```

2. Redis server running (for SocketIO message queue in production)

3. WebSocket-compatible browser (all modern browsers)

## Configuration

Add to your `config.py`:

```python
# Real-time Features
REALTIME_ENABLED = True
SOCKETIO_CORS_ALLOWED_ORIGINS = "*"  # Configure for production
SOCKETIO_ASYNC_MODE = "threading"    # or "eventlet" for better performance
```

## Architecture

### Server-Side Components

#### SocketIO Manager (`src/panel/socket_handlers.py`)
- **Connection Management**: Handles client connections/disconnections
- **Room Management**: Organizes users into forum threads and groups
- **Event Routing**: Processes real-time events and broadcasts updates
- **Authentication**: Links WebSocket connections to user accounts

#### Real-time Manager
- **User Tracking**: Maintains online user lists and connection states
- **Forum Rooms**: Manages thread-specific communication channels
- **Broadcasting**: Sends targeted updates to relevant users
- **Caching**: Uses Redis for distributed state management

### Client-Side Integration

#### SocketIO Client
- **Auto-connection**: Connects on page load for authenticated users
- **Event Handling**: Processes server-sent events and updates UI
- **Error Recovery**: Handles connection drops and reconnections
- **Room Joining**: Automatically joins relevant communication rooms

## Real-time Features

### 1. Forum Live Updates

#### Features
- **New Post Notifications**: Instant alerts for new replies
- **Activity Feed**: Live feed of recent thread activity
- **Typing Indicators**: Shows when users are composing replies
- **Thread Highlights**: Visual indicators for new content

#### Implementation
```javascript
// Join forum thread
socket.emit('join_forum', {
    user_id: userId,
    thread_id: threadId
});

// Handle updates
socket.on('forum_update', (data) => {
    // Update UI with new content
});
```

### 2. User Status Tracking

#### Features
- **Online/Offline Indicators**: Real-time user presence
- **Status Broadcasting**: Automatic status updates on connect/disconnect
- **User Lists**: Live lists of online community members

#### Implementation
```javascript
// User comes online
socket.emit('authenticate', { user_id: userId });

// Receive status updates
socket.on('user_status_change', (data) => {
    updateUserStatus(data.user_id, data.online);
});
```

### 3. Server Status Monitoring

#### Features
- **Live Server Stats**: Real-time player counts, maps, ping
- **Status Changes**: Instant notifications of server state changes
- **Dashboard Integration**: Live updates on main dashboard

#### Implementation
```javascript
// Request server status
socket.emit('server_status_request', {
    server_ids: ['main', 'secondary']
});

// Receive updates
socket.on('server_status_update', (data) => {
    updateServerDisplay(data.server_id, data.status);
});
```

### 4. Push Notifications

#### Features
- **Browser Notifications**: Native browser notification API
- **Permission Management**: User-controlled notification preferences
- **Event-driven**: Notifications for forum replies, mentions, etc.

#### Implementation
```javascript
// Request notification permission
if ('Notification' in window) {
    Notification.requestPermission();
}

// Handle push events
socket.on('notification', (data) => {
    showBrowserNotification(data.title, data.body, data.url);
});
```

## Usage Examples

### Forum Thread Page

```html
<!-- Activity Feed -->
<div id="forum-activity" class="activity-list">
    <!-- Live updates appear here -->
</div>

<!-- Typing Indicators -->
<div id="typing-indicators">
    <!-- Shows "User is typing..." -->
</div>
```

### Dashboard Server Status

```html
<div class="server-status-item" data-server-id="main">
    <span class="server-players">Players: 15/32</span>
    <span class="server-map">Map: etl_sp_delivery</span>
    <span class="server-ping">Ping: 45ms</span>
</div>
```

## API Events

### Client to Server Events

| Event | Data | Description |
|-------|------|-------------|
| `authenticate` | `{user_id}` | Link connection to user account |
| `join_forum` | `{user_id, thread_id}` | Join forum thread room |
| `leave_forum` | `{user_id, thread_id}` | Leave forum thread room |
| `forum_post` | `{user_id, thread_id, content}` | Notify of new post |
| `typing_start` | `{user_id, thread_id}` | User started typing |
| `typing_stop` | `{user_id, thread_id}` | User stopped typing |
| `get_online_users` | - | Request online user list |
| `server_status_request` | `{server_ids}` | Request server status |

### Server to Client Events

| Event | Data | Description |
|-------|------|-------------|
| `connected` | `{status, timestamp}` | Connection confirmed |
| `authenticated` | `{status, online_users}` | Authentication successful |
| `user_status_change` | `{user_id, online, timestamp}` | User status changed |
| `notification` | `{title, body, url}` | Push notification |
| `forum_update` | `{type, thread_id, data}` | Forum content update |
| `forum_activity` | `{thread_id, activity}` | Recent forum activity |
| `user_typing` | `{user_id, username, action}` | Typing indicator |
| `online_users_list` | `{users, count}` | Online users list |
| `server_status_update` | `{server_id, status}` | Server status update |

## Security Considerations

### Authentication
- **Token-based**: WebSocket connections require valid user sessions
- **Room Access**: Users can only join authorized rooms
- **Rate Limiting**: WebSocket events are rate-limited

### Data Validation
- **Input Sanitization**: All event data is validated
- **Permission Checks**: Users can only send authorized events
- **Content Filtering**: Forum content is moderated

### Privacy
- **User Consent**: Notifications require explicit permission
- **Data Minimization**: Only necessary data is transmitted
- **Secure Transport**: WebSocket connections use WSS in production

## Performance Optimization

### Connection Management
- **Connection Pooling**: Efficient handling of multiple connections
- **Room-based Messaging**: Targeted broadcasts reduce overhead
- **Heartbeat Monitoring**: Automatic cleanup of stale connections

### Caching Strategy
- **Redis Backend**: Distributed state management
- **Message Queuing**: Asynchronous event processing
- **Connection State**: Cached user and room information

### Scalability
- **Horizontal Scaling**: Multiple server instances supported
- **Load Balancing**: WebSocket connections can be load balanced
- **Message Broadcasting**: Efficient cross-server communication

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check WebSocket server is running
   - Verify CORS configuration
   - Check browser WebSocket support

2. **Events Not Received**
   - Confirm user authentication
   - Check room membership
   - Verify event handler attachment

3. **High Latency**
   - Check Redis connection
   - Monitor server resources
   - Review network configuration

4. **Memory Usage**
   - Monitor connection counts
   - Implement connection limits
   - Clean up stale connections

### Debug Tools

```javascript
// Check connection status
console.log('Socket connected:', socket.connected);

// Monitor events
socket.onAny((event, ...args) => {
    console.log('Event received:', event, args);
});

// Test connection
socket.emit('test', { message: 'Hello Server' });
```

### Server Logs

```bash
# Monitor WebSocket connections
tail -f logs/panel.log | grep -i socket

# Check connection counts
netstat -an | grep :5000 | wc -l
```

## Deployment Considerations

### Production Setup

1. **WebSocket Server**
   ```bash
   # Using Gunicorn with eventlet
   pip install eventlet
   gunicorn -k eventlet -w 1 app:app
   ```

2. **Redis Configuration**
   ```python
   SOCKETIO_MESSAGE_QUEUE = 'redis://localhost:6379/0'
   ```

3. **Load Balancing**
   - Use sticky sessions for WebSocket connections
   - Configure Redis adapter for cross-server communication

4. **SSL/TLS**
   - WebSocket Secure (WSS) required for production
   - Configure SSL certificates properly

### Monitoring

- **Connection Metrics**: Track active connections and rooms
- **Event Rates**: Monitor event frequency and types
- **Performance**: Measure latency and throughput
- **Error Rates**: Track failed connections and events

## Future Enhancements

1. **Video Chat**: WebRTC integration for voice/video
2. **File Sharing**: Real-time file transfer capabilities
3. **Collaborative Editing**: Live document editing
4. **Advanced Presence**: Detailed user status (busy, away, etc.)
5. **Message History**: Persistent chat history
6. **Offline Sync**: Queue messages for offline users

## Browser Support

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| WebSocket | ? | ? | ? | ? |
| SocketIO | ? | ? | ? | ? |
| Push API | ? | ? | ? (16.4+) | ? |
| Notifications | ? | ? | ? | ? |

## Integration Examples

### Custom Event Handling

```javascript
// Custom event listener
socket.on('custom_event', (data) => {
    console.log('Custom event received:', data);
    // Handle custom logic
});

// Send custom event
socket.emit('custom_action', {
    user_id: userId,
    action: 'custom',
    data: customData
});
```

### Server-side Custom Events

```python
from src.panel.socket_handlers import socketio

# Send custom event to specific user
socketio.emit('custom_notification', data, room=user_socket_id)

# Broadcast to room
socketio.emit('room_update', data, room='room_name')
```

This comprehensive real-time system provides a modern, interactive user experience while maintaining security, performance, and scalability.