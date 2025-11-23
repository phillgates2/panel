# Docker Optimization and Security Guide

## Overview

This document describes the optimized Docker setup for the Panel application, featuring multi-stage builds, security hardening, monitoring, and development tools.

## Architecture

### Multi-Stage Dockerfile

The production Dockerfile uses multiple stages for optimization:

1. **Builder Stage**: Compiles Python dependencies and creates wheels
2. **Security Scan Stage**: Runs vulnerability scanning (safety, bandit)
3. **Production Stage**: Final optimized runtime image
4. **Development Stage**: Development image with hot reload

### Key Security Features

- **Non-root user**: Application runs as `panel` user (UID 1000)
- **Minimal base image**: Uses `python:3.11-slim` for smaller attack surface
- **No privileged containers**: `no-new-privileges:true` security option
- **Read-only root filesystem**: Prevents file system modifications
- **Security scanning**: Automated vulnerability detection in CI/CD

### Performance Optimizations

- **Multi-stage builds**: Reduces final image size by ~60%
- **Layer caching**: Optimized for build speed and size
- **Gunicorn**: Production WSGI server with 4 workers
- **Connection pooling**: Database and Redis connection optimization
- **Health checks**: Automated container health monitoring

## Production Deployment

### Prerequisites

1. **Environment Variables**:
   ```bash
   export PANEL_DB_PASSWORD="your_secure_db_password"
   export PANEL_SECRET_KEY="your_very_long_secret_key"
   export REDIS_PASSWORD="your_redis_password"
   export GRAFANA_PASSWORD="your_grafana_password"
   ```

2. **SSL Certificates**:
   ```bash
   mkdir -p nginx/ssl
   # Place your SSL certificate and key files:
   # nginx/ssl/cert.pem
   # nginx/ssl/key.pem
   ```

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd panel

# Start production stack
docker-compose up -d

# View logs
docker-compose logs -f panel

# Scale application
docker-compose up -d --scale panel=3
```

### Services Overview

| Service | Port | Description |
|---------|------|-------------|
| Panel App | 8080 | Main Flask application |
| Nginx | 80/443 | Reverse proxy with SSL |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache and session store |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Monitoring dashboard |
| Loki | 3100 | Log aggregation |

## Development Setup

### Enhanced Development Environment

```bash
# Start development stack with additional tools
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Access development tools:
# - Application: http://localhost:8080
# - PgAdmin: http://localhost:5050 (admin@panel.local / admin)
# - Redis Commander: http://localhost:8081
# - MailHog: http://localhost:8025
# - Grafana: http://localhost:3000
# - Prometheus: http://localhost:9090
```

### Development Tools Included

- **PgAdmin**: PostgreSQL database management
- **Redis Commander**: Redis key-value browser
- **MailHog**: Email testing and capture
- **Node Exporter**: System metrics collection
- **Hot Reload**: Automatic code reloading on changes

## Security Hardening

### Container Security

```yaml
# Applied security options
security_opt:
  - no-new-privileges:true

read_only: true
tmpfs:
  - /tmp

# Non-root user
user: panel
```

### Network Security

- **Internal networks**: Services communicate on isolated networks
- **No exposed databases**: Database ports not exposed externally
- **Rate limiting**: Nginx-based request rate limiting
- **SSL/TLS**: Enforced HTTPS with modern cipher suites

### Application Security

- **Security headers**: HSTS, CSP, X-Frame-Options
- **Input validation**: Comprehensive schema validation
- **Rate limiting**: API and authentication endpoint protection
- **Audit logging**: Comprehensive security event logging

## Monitoring and Observability

### Metrics Collection

- **Application metrics**: Response times, error rates, throughput
- **System metrics**: CPU, memory, disk, network
- **Database metrics**: Connection pools, query performance
- **Cache metrics**: Hit rates, memory usage

### Logging Pipeline

```
Application Logs → Promtail → Loki → Grafana
System Logs     → Promtail → Loki → Grafana
Nginx Logs      → Promtail → Loki → Grafana
```

### Dashboards

- **Application Overview**: Response times, error rates, throughput
- **System Resources**: CPU, memory, disk usage
- **Database Performance**: Connections, query times
- **Security Events**: Failed logins, suspicious activity

## Performance Tuning

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Database Optimization

- **Connection pooling**: SQLAlchemy with optimized pool settings
- **Indexes**: Automatic index creation for performance
- **Vacuum settings**: Optimized PostgreSQL maintenance

### Cache Configuration

- **Redis persistence**: AOF and RDB snapshots
- **Memory limits**: 256MB with LRU eviction
- **Multiple databases**: Separate DBs for cache, sessions, rate limiting

## Backup and Recovery

### Database Backups

```bash
# Create backup
docker exec panel_postgres pg_dump -U panel_user panel > backup.sql

# Restore backup
docker exec -i panel_postgres psql -U panel_user panel < backup.sql
```

### Configuration Backups

```bash
# Backup volumes
docker run --rm -v panel_postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz -C /data .
```

## Troubleshooting

### Common Issues

1. **Container won't start**:
   ```bash
   docker-compose logs <service_name>
   docker-compose ps
   ```

2. **Database connection issues**:
   ```bash
   docker-compose exec postgres pg_isready -U panel_user -d panel
   ```

3. **Application errors**:
   ```bash
   docker-compose logs panel
   docker-compose exec panel flask shell
   ```

4. **Performance issues**:
   ```bash
   docker stats
   docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
   ```

### Health Checks

```bash
# Check all services
docker-compose ps

# Check application health
curl http://localhost/health

# Check database connectivity
docker-compose exec panel python -c "from app import db; db.engine.execute('SELECT 1')"
```

## CI/CD Integration

### Build Pipeline

```yaml
# .github/workflows/docker.yml
name: Build and Push Docker Images

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker images
      run: docker-compose build

    - name: Run security scans
      run: |
        docker run --rm -v $(pwd):/app security-scan

    - name: Run tests
      run: docker-compose -f docker-compose.test.yml up --abort-on-container-exit

    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker-compose push
```

### Security Scanning

- **Container scanning**: Trivy or Clair
- **Dependency scanning**: Safety, pip-audit
- **Code scanning**: Bandit, semgrep
- **Secrets detection**: GitLeaks

## Scaling

### Horizontal Scaling

```bash
# Scale application instances
docker-compose up -d --scale panel=3

# Load balancer configuration (nginx.conf)
upstream panel_backend {
    server panel:8080;
    server panel:8080;
    server panel:8080;
}
```

### Database Scaling

- **Read replicas**: Add PostgreSQL replicas for read scaling
- **Connection pooling**: PgBouncer for connection management
- **Sharding**: Database sharding for massive scale

## Maintenance

### Updates

```bash
# Update all images
docker-compose pull

# Update specific service
docker-compose pull panel
docker-compose up -d panel

# Zero-downtime updates
docker-compose up -d --no-deps panel
```

### Cleanup

```bash
# Remove unused images and volumes
docker image prune -f
docker volume prune -f

# Clean up logs
docker-compose exec loki rm -rf /loki/chunks/*
```

## Production Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database backups configured
- [ ] Monitoring alerts set up
- [ ] Log rotation configured
- [ ] Security scans passing
- [ ] Performance benchmarks met
- [ ] Backup restoration tested