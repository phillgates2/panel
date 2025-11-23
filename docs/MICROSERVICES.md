# Microservices Architecture Preparation

This guide explains the microservices architecture preparation implemented for the Panel application.

## Overview

The Panel application has been prepared for microservices deployment with separate services for different business domains:

- **API Gateway**: Central entry point and request routing
- **Auth Service**: User authentication and authorization
- **Forum Service**: Community forums and discussions
- **CMS Service**: Content management and blogging
- **Admin Service**: Administrative functions and monitoring

## Architecture Benefits

### Scalability
- **Independent Scaling**: Scale individual services based on load
- **Resource Optimization**: Allocate resources where needed
- **Horizontal Scaling**: Add multiple instances of services

### Maintainability
- **Service Isolation**: Changes in one service don't affect others
- **Technology Diversity**: Use different tech stacks per service
- **Independent Deployments**: Deploy services independently

### Reliability
- **Fault Isolation**: Service failures don't cascade
- **Graceful Degradation**: System continues with partial failures
- **Load Distribution**: Distribute load across service instances

## Service Structure

### API Gateway Service
**Port: 5000**
- Request routing and load balancing
- Authentication middleware
- Rate limiting and security
- API documentation aggregation

### Auth Service
**Port: 5001**
- User registration and login
- JWT token management
- Password reset functionality
- OAuth integration

### Forum Service
**Port: 5002**
- Thread and post management
- User interactions and replies
- Moderation tools
- Real-time notifications

### CMS Service
**Port: 5003**
- Blog post management
- Content creation and editing
- Media upload handling
- SEO optimization

### Admin Service
**Port: 5004**
- User management
- System monitoring
- Audit logging
- Configuration management

## Docker Deployment

### Prerequisites

1. **Docker and Docker Compose**:
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.17.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **SSL Certificates** (for production):
   ```bash
   # Using Let's Encrypt
   sudo certbot certonly --standalone -d yourdomain.com
   ```

### Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd panel
   cp config/config.py.example config/config.py
   ```

2. **Start services**:
   ```bash
   make microservices-up
   ```

3. **Check health**:
   ```bash
   make microservices-health
   ```

4. **View logs**:
   ```bash
   make microservices-logs
   ```

5. **Stop services**:
   ```bash
   make microservices-down
   ```

## Configuration

### Environment Variables

```bash
# Microservices
MICROSERVICES_ENABLED=true
API_GATEWAY_ENABLED=true

# Database (shared)
DATABASE_URL=postgresql://panel:password@postgres:5432/panel

# Redis (shared)
REDIS_URL=redis://redis:6379/0

# Service-specific configs
AUTH_SERVICE_URL=http://auth-service:5000
FORUM_SERVICE_URL=http://forum-service:5000
CMS_SERVICE_URL=http://cms-service:5000
ADMIN_SERVICE_URL=http://admin-service:5000
```

### Service Discovery

Services register themselves with the API gateway for automatic discovery:

```python
# Service registration
microservices_manager.register_service('auth', auth_blueprint, '/auth')
microservices_manager.register_service('forum', forum_blueprint, '/forum')
```

## Development Workflow

### Local Development

1. **Run individual services**:
   ```bash
   # Terminal 1 - Auth Service
   export FLASK_APP=services/auth/app.py
   export MICROSERVICES_ENABLED=true
   flask run --port=5001

   # Terminal 2 - Forum Service
   export FLASK_APP=services/forum/app.py
   export MICROSERVICES_ENABLED=true
   flask run --port=5002

   # Terminal 3 - API Gateway
   export FLASK_APP=services/api-gateway/app.py
   export API_GATEWAY_ENABLED=true
   flask run --port=5000
   ```

2. **Test service communication**:
   ```bash
   # Test API gateway
   curl http://localhost:5000/api/v2/health

   # Test service routing
   curl http://localhost:5000/api/v2/auth/login
   ```

### Testing Strategy

1. **Unit Tests**: Test individual service functions
2. **Integration Tests**: Test service-to-service communication
3. **End-to-End Tests**: Test complete user workflows
4. **Contract Tests**: Ensure API compatibility between services

## Monitoring and Observability

### Health Checks

Each service exposes health endpoints:

```bash
# API Gateway health
curl http://localhost:5000/api/v2/health

# Individual service health
curl http://localhost:5001/health
curl http://localhost:5002/health
```

### Logging

- **Centralized Logging**: All services log to shared volumes
- **Structured Logs**: JSON format for easy parsing
- **Log Aggregation**: Use ELK stack or similar for log analysis

### Metrics

- **Prometheus**: Collects metrics from all services
- **Grafana**: Visualizes metrics and creates dashboards
- **Custom Metrics**: Service-specific performance indicators

## Database Considerations

### Shared Database (Current)
- All services access the same PostgreSQL database
- Schema migrations managed centrally
- Potential bottleneck for high-traffic applications

### Database per Service (Future)
- Each service has its own database
- Event-driven data synchronization
- Improved scalability and fault isolation

## API Gateway Features

### Request Routing

```nginx
# Route to appropriate service
location /auth/ {
    proxy_pass http://auth_service/;
}

location /forum/ {
    proxy_pass http://forum_service/;
}
```

### Middleware

- **Authentication**: JWT token validation
- **Rate Limiting**: Per-service and global limits
- **CORS**: Cross-origin request handling
- **Caching**: Response caching and CDN integration

### Load Balancing

- **Round Robin**: Default load balancing
- **Health Checks**: Automatic removal of unhealthy instances
- **Session Affinity**: Sticky sessions for stateful services

## Migration Strategy

### Phase 1: Preparation
- [x] Service blueprint creation
- [x] API gateway implementation
- [x] Docker configuration
- [x] Configuration management

### Phase 2: Gradual Migration
- [ ] Extract auth service
- [ ] Extract forum service
- [ ] Extract CMS service
- [ ] Extract admin service

### Phase 3: Full Microservices
- [ ] Independent deployments
- [ ] Service mesh implementation
- [ ] Event-driven architecture

## Troubleshooting

### Common Issues

1. **Service Communication**:
   ```bash
   # Check service connectivity
   docker-compose exec api-gateway curl http://auth-service:5000/health
   ```

2. **Database Connection**:
   ```bash
   # Check database connectivity
   docker-compose exec postgres pg_isready -U panel
   ```

3. **Port Conflicts**:
   ```bash
   # Check port usage
   netstat -tulpn | grep :500
   ```

### Debug Commands

```bash
# View service logs
docker-compose logs auth-service

# Enter service container
docker-compose exec auth-service bash

# Restart specific service
docker-compose restart auth-service

# Scale service
docker-compose up -d --scale auth-service=3
```

## Security Considerations

### Service-to-Service Communication
- **mTLS**: Mutual TLS for service authentication
- **API Keys**: Service-specific authentication
- **Network Policies**: Restrict inter-service communication

### Data Protection
- **Encryption**: Encrypt data in transit and at rest
- **Access Control**: Principle of least privilege
- **Audit Logging**: Comprehensive logging of all operations

## Performance Optimization

### Caching Strategy
- **Redis**: Shared caching layer
- **CDN**: Static asset delivery
- **Service Caching**: Per-service cache management

### Database Optimization
- **Connection Pooling**: Efficient database connections
- **Read Replicas**: Separate read and write workloads
- **Query Optimization**: Database performance tuning

## Future Enhancements

1. **Service Mesh**: Istio or Linkerd for advanced traffic management
2. **Event Streaming**: Apache Kafka for event-driven architecture
3. **API Versioning**: Semantic versioning for API compatibility
4. **Circuit Breakers**: Resilience patterns for service communication
5. **Distributed Tracing**: Jaeger or Zipkin for request tracing