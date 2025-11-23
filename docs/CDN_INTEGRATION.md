# Content Delivery Network (CDN) Integration

This guide explains the CDN integration implemented for global asset delivery and performance optimization.

## Overview

The Panel application supports multiple CDN providers for improved global performance:

- **Cloudflare**: Full-featured CDN with security and optimization
- **AWS CloudFront**: Enterprise-grade CDN with extensive features
- **Generic CDN**: Support for any CDN provider with custom URLs

## Benefits

### Performance Improvements
- **Global Distribution**: Assets served from edge locations worldwide
- **Reduced Latency**: Faster loading times for international users
- **Bandwidth Savings**: Offload traffic from origin servers
- **Caching**: Automatic asset caching and optimization

### Reliability
- **DDoS Protection**: Built-in protection against attacks
- **Failover**: Automatic failover to healthy edge servers
- **Uptime**: 99.9%+ uptime guarantees
- **Monitoring**: Real-time performance monitoring

### Cost Optimization
- **Reduced Server Load**: Fewer requests to application servers
- **Bandwidth Costs**: Lower egress costs with CDN pricing
- **Scalability**: Handle traffic spikes without infrastructure changes

## Configuration

### Environment Variables

```bash
# CDN Configuration
CDN_ENABLED=true
CDN_URL=https://cdn.yourdomain.com
CDN_PROVIDER=cloudflare  # 'cloudflare', 'cloudfront', or 'generic'

# Cloudflare (if using Cloudflare)
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_ZONE_ID=your_zone_id

# AWS CloudFront (if using CloudFront)
AWS_CLOUDFRONT_DISTRIBUTION_ID=your_distribution_id
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

### Provider-Specific Setup

#### Cloudflare Setup

1. **Create Cloudflare Account**:
   ```bash
   # Sign up at https://cloudflare.com
   ```

2. **Add Domain**:
   - Add your domain to Cloudflare
   - Update DNS records

3. **Generate API Token**:
   - Go to My Profile ? API Tokens
   - Create token with Zone permissions

4. **Get Zone ID**:
   ```bash
   curl -X GET "https://api.cloudflare.com/client/v4/zones" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -H "Content-Type: application/json"
   ```

#### AWS CloudFront Setup

1. **Create Distribution**:
   ```bash
   aws cloudfront create-distribution --distribution-config file://distribution.json
   ```

2. **Configure Origins**:
   - Set your application server as origin
   - Configure SSL and security settings

3. **Set up IAM User**:
   ```bash
   aws iam create-user --user-name cdn-manager
   aws iam attach-user-policy --user-name cdn-manager \
       --policy-arn arn:aws:iam::aws:policy/CloudFrontFullAccess
   ```

## Asset Management

### Automatic Asset Handling

The CDN integration automatically handles:

- **URL Generation**: Converts local URLs to CDN URLs
- **Cache Busting**: Adds version parameters for updates
- **Preloading**: Critical assets loaded to CDN on startup
- **Invalidation**: Cache clearing when assets change

### Template Integration

```html
<!-- Static assets -->
<link rel="stylesheet" href="{{ 'css/style.css'|cdn_static }}">
<script src="{{ 'js/app.js'|cdn_static }}"></script>

<!-- Media files -->
<img src="{{ 'uploads/avatar.jpg'|cdn_media }}" alt="Avatar">

<!-- Custom URLs -->
<link rel="icon" href="{{ 'favicon.ico'|cdn_url }}">
```

### Cache Management

#### Automatic Cache Busting

Assets get version parameters based on modification time:

```html
<!-- Original -->
<link rel="stylesheet" href="/static/css/style.css">

<!-- With CDN and versioning -->
<link rel="stylesheet" href="https://cdn.yourdomain.com/css/style.css?v=1640995200">
```

#### Manual Cache Invalidation

```bash
# Invalidate specific asset
make cdn-invalidate ASSET=css/style.css

# Check CDN status
make cdn-stats
```

## Performance Optimization

### Asset Optimization

CDN providers automatically optimize:

- **Image Compression**: WebP, AVIF format support
- **Minification**: CSS and JavaScript minification
- **Gzip Compression**: Automatic content compression
- **HTTP/2**: Modern protocol support

### Caching Strategies

| Asset Type | Cache Duration | Strategy |
|------------|----------------|----------|
| CSS/JS | 1 year | Cache-first |
| Images | 1 year | Cache-first |
| Fonts | 1 year | Cache-first |
| API responses | 5 minutes | Network-first |
| HTML pages | No cache | Network-first |

### Monitoring Performance

```bash
# CDN statistics
make cdn-stats

# Provider-specific analytics
# Cloudflare: Dashboard ? Analytics
# CloudFront: AWS Console ? CloudFront ? Monitoring
```

## Security Features

### SSL/TLS
- **Free SSL**: Automatic HTTPS certificates
- **Custom Certificates**: Upload your own certificates
- **HSTS**: HTTP Strict Transport Security

### DDoS Protection
- **Rate Limiting**: Automatic attack mitigation
- **Bot Management**: Block malicious bots
- **Web Application Firewall**: SQL injection and XSS protection

### Access Control
- **Geo-blocking**: Restrict access by country
- **IP Whitelisting**: Allow only specific IPs
- **Hotlink Protection**: Prevent direct linking to assets

## Implementation Details

### CDN Manager Class

```python
from src.panel.cdn_integration import get_cdn_manager

cdn = get_cdn_manager()

# Get CDN URL
url = cdn.get_asset_url('css/style.css')

# Invalidate cache
cdn.invalidate_asset('css/style.css')

# Get statistics
stats = cdn.get_cache_manifest()
```

### Template Filters

Jinja2 filters for easy CDN integration:

```python
# In templates
{{ 'css/style.css'|cdn_static }}     # /static/css/style.css
{{ 'avatar.jpg'|cdn_media }}          # /static/uploads/avatar.jpg
{{ 'favicon.ico'|cdn_url }}           # /static/favicon.ico
```

### Service Provider Classes

- **CloudflareCDN**: Cloudflare-specific features
- **AWSCloudFrontCDN**: CloudFront-specific features
- **CDNManager**: Generic CDN support

## Troubleshooting

### Common Issues

1. **Assets not loading from CDN**:
   ```bash
   # Check CDN configuration
   make cdn-status

   # Verify asset URLs
   curl -I https://cdn.yourdomain.com/css/style.css
   ```

2. **Stale cached content**:
   ```bash
   # Invalidate cache
   make cdn-invalidate ASSET=path/to/asset

   # Or purge all (provider-specific)
   ```

3. **SSL certificate issues**:
   - Check certificate validity
   - Verify domain ownership
   - Contact CDN provider support

### Debug Tools

```python
# Check CDN configuration
from src.panel.cdn_integration import get_cdn_stats
stats = get_cdn_stats()
print(stats)

# Test URL generation
from src.panel.cdn_integration import cdn_url_for
url = cdn_url_for('css/style.css')
print(url)
```

## Cost Optimization

### Pricing Considerations

| Provider | Free Tier | Paid Plans | Features |
|----------|-----------|------------|----------|
| Cloudflare | Yes | $20+/month | Full-featured |
| CloudFront | No | $0.085/GB | Enterprise |
| Generic | Varies | Varies | Basic |

### Usage Monitoring

- **Bandwidth Tracking**: Monitor data transfer costs
- **Request Counting**: Track number of requests
- **Cache Hit Ratio**: Optimize caching strategies
- **Cost Alerts**: Set up billing alerts

## Migration Strategy

### Gradual Rollout

1. **Test Environment**:
   ```bash
   export CDN_ENABLED=true
   export CDN_URL=https://cdn-test.yourdomain.com
   ```

2. **Staged Rollout**:
   - Enable for static assets first
   - Gradually enable for dynamic content
   - Monitor performance and costs

3. **Full Production**:
   - Enable for all assets
   - Set up monitoring and alerts
   - Configure backup CDN if needed

## Best Practices

### Asset Organization
- **Logical Grouping**: Group related assets together
- **Version Control**: Use asset versioning for updates
- **Compression**: Pre-compress assets when possible

### Performance
- **Critical Assets**: Preload important resources
- **Lazy Loading**: Load non-critical assets on demand
- **Resource Hints**: Use preload/prefetch hints

### Security
- **HTTPS Only**: Always use HTTPS for CDN URLs
- **Access Tokens**: Use signed URLs for private content
- **CORS Headers**: Configure appropriate CORS policies

## Future Enhancements

1. **Multi-CDN**: Use multiple CDNs for redundancy
2. **Edge Computing**: Run code at edge locations
3. **Real-time Analytics**: Live performance monitoring
4. **AI Optimization**: Machine learning-based optimizations
5. **Video Streaming**: Support for video content delivery