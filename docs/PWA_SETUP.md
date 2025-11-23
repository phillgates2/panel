# Progressive Web App (PWA) Setup

This guide explains how to configure and deploy the Panel application as a Progressive Web App.

## Overview

The Panel PWA provides:
- **Offline functionality** - Access cached content without internet
- **Installable app** - Add to home screen on mobile devices
- **Push notifications** - Real-time updates and alerts
- **Background sync** - Sync data when connection is restored
- **Fast loading** - Cached resources for instant loading

## Prerequisites

1. Install required dependencies:
   ```bash
   pip install -r requirements/requirements-dev.txt
   ```

2. HTTPS required for service workers and push notifications in production

3. Generate VAPID keys for push notifications:
   ```bash
   python -c "
   from pywebpush import vapid
   vapid_keys = vapid.Vapid().generate_keys()
   print('VAPID_PRIVATE_KEY=' + vapid_keys[0].decode())
   print('VAPID_PUBLIC_KEY=' + vapid_keys[1].decode())
   "
   ```

## Configuration

Add to your `config.py`:

```python
# PWA Configuration
PWA_ENABLED = True
PWA_CACHE_NAME = 'panel-v1.0.0'
PWA_OFFLINE_PAGE = '/offline'

# Push Notifications
VAPID_PUBLIC_KEY = 'your_vapid_public_key'
VAPID_PRIVATE_KEY = 'your_vapid_private_key'
VAPID_SUBJECT = 'mailto:admin@yourdomain.com'
```

## Icons and Assets

### Required Icons
Create the following icons in `static/icons/`:
- `icon-192.png` (192x192px)
- `icon-512.png` (512x512px)

### Generation Script
```bash
# Using ImageMagick
convert static/logo.png -resize 192x192 static/icons/icon-192.png
convert static/logo.png -resize 512x512 static/icons/icon-512.png

# Or use online tools like:
# https://favicon.io/favicon-converter/
```

## Service Worker

The service worker (`static/sw.js`) provides:
- **Cache-first strategy** for static assets
- **Network-first strategy** for dynamic content
- **Offline fallback** to cached pages
- **Background sync** for offline actions
- **Push notification handling**

### Cache Strategies

| Content Type | Strategy | TTL |
|-------------|----------|-----|
| Static assets (CSS, JS, images) | Cache-first | Until update |
| API responses | Network-first | 5 minutes |
| Pages | Network-first | 1 hour |
| Offline page | Cache-first | Always |

## Push Notifications

### Browser Support
- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Limited support (iOS 16.4+)
- Mobile browsers: Good support

### Setup Steps

1. **Generate VAPID keys** (see prerequisites)

2. **Configure environment variables**:
   ```bash
   export VAPID_PUBLIC_KEY="your_public_key"
   export VAPID_PRIVATE_KEY="your_private_key"
   export VAPID_SUBJECT="mailto:admin@yourdomain.com"
   ```

3. **Test notifications**:
   ```bash
   # From user profile page
   # Click "Test Notification" button
   ```

### Notification Types

- **Server alerts** - Server status changes
- **Forum updates** - New replies, mentions
- **System notifications** - Maintenance, updates
- **Custom notifications** - Admin-defined messages

## Offline Functionality

### Cached Resources
- Main application pages
- Static assets (CSS, JS, images)
- User profile and settings
- Frequently accessed forum threads

### Offline Features
- View cached content
- Access user profile
- Read saved forum posts
- View server status (if cached)

### Background Sync
- Sync forum posts created offline
- Upload files when connection restored
- Send pending messages
- Update user activity

## Installation

### Mobile Installation
1. Open the site in a supported browser
2. Look for "Add to Home Screen" prompt
3. Or use browser menu ? "Add to Home Screen"
4. The app will install with custom icon

### Desktop Installation
1. In Chrome/Edge, click address bar icon
2. Select "Install Panel"
3. App appears in desktop app launcher

## Testing

### PWA Validation
```bash
# Test PWA features
make pwa-test

# Check Lighthouse score
# Use Chrome DevTools ? Lighthouse
# Run PWA audit
```

### Manual Testing

1. **Offline test**:
   - Go offline in DevTools
   - Navigate to cached pages
   - Verify offline page appears

2. **Install test**:
   - Check "Add to Home Screen" prompt
   - Install the app
   - Verify it launches correctly

3. **Push notification test**:
   - Subscribe to notifications
   - Send test notification
   - Verify delivery

## Performance Optimization

### Cache Optimization
- **Preload critical resources**
- **Lazy load non-critical assets**
- **Optimize image sizes**
- **Minify CSS/JS**

### Network Optimization
- **HTTP/2** for multiplexing
- **CDN** for global distribution
- **Compression** enabled
- **Cache headers** properly set

## Security Considerations

### HTTPS Required
- Service workers require HTTPS in production
- Push notifications require HTTPS
- Mixed content blocked

### Content Security Policy
```javascript
// In service worker
const csp = "default-src 'self'; script-src 'self' 'unsafe-inline';";
```

### Push Notification Security
- VAPID keys properly secured
- Subscription data encrypted
- User consent required

## Troubleshooting

### Common Issues

1. **Service worker not registering**:
   - Check HTTPS requirement
   - Verify SW file path
   - Check browser console for errors

2. **Push notifications not working**:
   - Verify VAPID keys
   - Check browser permissions
   - Test with different browsers

3. **Offline not working**:
   - Check cache storage
   - Verify SW is active
   - Test with different pages

4. **Install prompt not showing**:
   - Must be HTTPS
   - User interaction required
   - Check PWA criteria met

### Debug Commands

```bash
# Check service worker status
navigator.serviceWorker.getRegistrations().then(registrations => {
  console.log('SW registrations:', registrations);
});

# Clear all caches
caches.keys().then(names => {
  names.forEach(name => caches.delete(name));
});

# Check push subscription
navigator.serviceWorker.getRegistration().then(reg => {
  reg.pushManager.getSubscription().then(sub => console.log(sub));
});
```

## Deployment Checklist

- [ ] HTTPS certificate installed
- [ ] VAPID keys generated and configured
- [ ] PWA icons created and optimized
- [ ] Service worker tested
- [ ] Push notifications tested
- [ ] Offline functionality verified
- [ ] Installation prompt working
- [ ] Performance optimized
- [ ] Security headers configured

## Browser Support

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Service Worker | ? | ? | ? | ? |
| Push API | ? | ? | ? (16.4+) | ? |
| Background Sync | ? | ? | ? | ? |
| Web App Manifest | ? | ? | ? | ? |
| Install Prompt | ? | ? | ? | ? |

## Future Enhancements

1. **Advanced caching strategies**
2. **Offline data synchronization**
3. **Progressive loading**
4. **App shortcuts**
5. **Badge notifications**
6. **Periodic background updates**