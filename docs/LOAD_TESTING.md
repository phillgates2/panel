# Load Testing & Performance Monitoring

This guide explains the load testing and performance monitoring setup for the Panel application.

## Overview

The performance testing suite includes:
- **Load Testing**: Stress testing with Locust
- **Performance Monitoring**: Real-time metrics collection
- **APM Integration**: New Relic and DataDog support
- **CI/CD Integration**: Automated performance validation

## Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install -r requirements/requirements-dev.txt
   ```

2. **Locust Installation**:
   ```bash
   pip install locust
   ```

3. **APM Services** (optional):
   - New Relic account and API key
   - DataDog account and API keys

4. **Monitoring Infrastructure**:
   - Redis for metrics storage
   - Grafana for dashboards (optional)

## Load Testing with Locust

### Test Scenarios

#### WebsiteUser (70% of traffic)
- **Homepage visits**: Basic navigation
- **Forum browsing**: Read-only forum access
- **Login attempts**: Authentication testing
- **Static assets**: CSS, JS, image loading

#### AuthenticatedUser (20% of traffic)
- **Dashboard access**: Personal dashboard
- **Profile management**: User settings
- **Forum interaction**: Posting and replying
- **API calls**: RESTful API usage

#### APIUser (7% of traffic)
- **Health checks**: System monitoring
- **User data**: Profile API calls
- **Forum data**: Content API access
- **GDPR endpoints**: Compliance API testing

#### AdminUser (3% of traffic)
- **Admin dashboard**: Administrative access
- **User management**: CRUD operations
- **System monitoring**: Audit logs and metrics
- **Configuration**: Settings management

### Running Load Tests

#### Web Interface

```bash
# Start Locust web UI
make test-load-web

# Access at http://localhost:8089
# Configure test parameters and start
```

#### Command Line

```bash
# Basic load test
make test-load

# Custom parameters
locust -f tests/load/locustfile.py \
  --host=http://localhost:8080 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=5m \
  --headless
```

#### Distributed Testing

```bash
# Master node
locust -f tests/load/locustfile.py --master --host=http://app-server

# Worker nodes
locust -f tests/load/locustfile.py --worker --master-host=master-server
```

### Test Configuration

#### Environment Variables

```bash
# Load test settings
LOAD_TEST_USERS=100          # Number of concurrent users
LOAD_TEST_SPAWN_RATE=10      # Users spawned per second
LOAD_TEST_DURATION=5m        # Test duration

# Test credentials
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=test123
TEST_ADMIN_EMAIL=admin@example.com
TEST_ADMIN_PASSWORD=admin123
```

#### Custom Test Scenarios

```python
class CustomUser(FastHttpUser):
    wait_time = between(1, 3)

    @task
    def custom_scenario(self):
        # Define custom test behavior
        self.client.get("/custom/endpoint")
        # Add assertions and validations
```

## Performance Monitoring

### Built-in Monitoring

#### System Metrics
- **CPU Usage**: Core and per-process monitoring
- **Memory Usage**: RAM and swap utilization
- **Disk I/O**: Read/write operations
- **Network I/O**: Bandwidth consumption

#### Application Metrics
- **Response Times**: Request latency tracking
- **Error Rates**: HTTP error monitoring
- **Throughput**: Requests per second
- **Database Queries**: SQL performance tracking

#### Custom Metrics
- **Cache Performance**: Hit/miss ratios
- **User Sessions**: Active session tracking
- **Background Jobs**: Queue performance

### Monitoring Endpoints

```bash
# Performance metrics
curl http://localhost:8080/api/monitoring/metrics

# Health check
curl http://localhost:8080/api/monitoring/health

# System information
curl http://localhost:8080/api/monitoring/system
```

### APM Integration

#### New Relic Setup

```python
# Configuration
NEW_RELIC_API_KEY=your_api_key
NEW_RELIC_APP_NAME=Panel Application

# Automatic instrumentation
# - Request timing
# - Database queries
# - External API calls
# - Error tracking
```

#### DataDog Setup

```python
# Configuration
DATADOG_API_KEY=your_api_key
DATADOG_APP_KEY=your_app_key

# Custom metrics
# - Business KPIs
# - User behavior
# - System health
```

## Performance Analysis

### Key Metrics

#### Response Time
- **Average**: Overall system responsiveness
- **95th Percentile**: Typical user experience
- **99th Percentile**: Worst-case performance

#### Throughput
- **Requests/Second**: System capacity
- **Concurrent Users**: Supported user load
- **Error Rate**: System reliability

#### Resource Usage
- **CPU Utilization**: Processing capacity
- **Memory Usage**: RAM requirements
- **Database Connections**: Connection pool usage

### Performance Benchmarks

| Metric | Target | Critical |
|--------|--------|----------|
| Response Time (avg) | <500ms | <2s |
| Response Time (95th) | <1s | <5s |
| Error Rate | <1% | <5% |
| CPU Usage | <70% | <90% |
| Memory Usage | <80% | <95% |

### Load Test Results Analysis

```python
# Analyze results from load_test_report.json
{
    "total_requests": 10000,
    "total_failures": 50,
    "requests_per_second": 150.5,
    "average_response_time": 450.2,
    "95th_percentile": 890.1,
    "99th_percentile": 2100.5
}
```

## CI/CD Integration

### Automated Performance Testing

```yaml
# GitHub Actions workflow
name: Performance Tests
on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements/requirements-dev.txt

      - name: Run load tests
        run: make test-load

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: load_test_results_*.csv
```

### Performance Regression Detection

```python
def check_performance_regression(current_metrics, baseline_metrics):
    """Check for performance regressions"""

    thresholds = {
        'avg_response_time': 1.1,  # 10% degradation allowed
        'error_rate': 2.0,         # 2x error rate allowed
        '95th_percentile': 1.2     # 20% degradation allowed
    }

    regressions = []
    for metric, threshold in thresholds.items():
        current = current_metrics.get(metric, 0)
        baseline = baseline_metrics.get(metric, 0)

        if baseline > 0 and current > baseline * threshold:
            regressions.append({
                'metric': metric,
                'current': current,
                'baseline': baseline,
                'degradation': (current - baseline) / baseline * 100
            })

    return regressions
```

## Monitoring Dashboards

### Grafana Setup

```yaml
# docker-compose.grafana.yml
version: '3.8'
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
```

### Custom Dashboards

#### Application Performance
- Response time graphs
- Error rate monitoring
- Throughput metrics
- Database performance

#### System Resources
- CPU and memory usage
- Disk I/O statistics
- Network traffic
- Container metrics

#### Business Metrics
- User registrations
- Forum activity
- API usage
- Geographic distribution

## Alerting

### Performance Alerts

```python
# Alert conditions
alerts = {
    'high_response_time': {
        'condition': 'avg_response_time > 1000',
        'severity': 'warning',
        'message': 'Average response time above 1 second'
    },
    'high_error_rate': {
        'condition': 'error_rate > 0.05',
        'severity': 'error',
        'message': 'Error rate above 5%'
    },
    'high_cpu_usage': {
        'condition': 'cpu_usage > 0.9',
        'severity': 'critical',
        'message': 'CPU usage above 90%'
    }
}
```

### Notification Channels

- **Email**: Critical alerts
- **Slack**: Team notifications
- **PagerDuty**: On-call alerts
- **Webhooks**: Custom integrations

## Optimization Strategies

### Database Optimization

```sql
-- Query performance analysis
EXPLAIN ANALYZE SELECT * FROM users WHERE email = $1;

-- Index optimization
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_posts_thread_id ON posts(thread_id);
```

### Caching Strategies

```python
# Redis caching
@app.cache.memoize(timeout=300)
def get_user_profile(user_id):
    return User.query.get(user_id)

# CDN integration
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)
```

### Code Profiling

```python
import cProfile

def profile_function(func):
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        profiler.print_stats(sort='cumulative')
        return result
    return wrapper
```

## Troubleshooting

### Common Performance Issues

1. **Slow Database Queries**:
   ```sql
   -- Find slow queries
   SELECT query, total_time, calls, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;
   ```

2. **Memory Leaks**:
   ```python
   # Memory profiling
   from memory_profiler import profile

   @profile
   def memory_intensive_function():
       # Function code here
       pass
   ```

3. **High CPU Usage**:
   ```bash
   # CPU profiling
   python -m cProfile -s cumulative app.py
   ```

### Debug Tools

```bash
# Database connection analysis
pg_stat_activity;

# Cache hit analysis
redis-cli info stats

# Application profiling
py-spy top --pid $(pgrep -f "python app.py")
```

## Scaling Strategies

### Horizontal Scaling

```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: panel-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: panel
  template:
    metadata:
      labels:
        app: panel
    spec:
      containers:
      - name: panel
        image: panel:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Load Balancing

```nginx
upstream panel_app {
    server app1:5000;
    server app2:5000;
    server app3:5000;
}

server {
    listen 80;
    location / {
        proxy_pass http://panel_app;
        proxy_set_header Host $host;
    }
}
```

### Database Scaling

- **Read Replicas**: Separate read and write workloads
- **Connection Pooling**: Efficient connection management
- **Query Optimization**: Index and query performance tuning

This comprehensive performance testing and monitoring setup ensures the Panel application can handle production loads while maintaining excellent user experience.