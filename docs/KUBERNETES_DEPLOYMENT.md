# Kubernetes Deployment for Panel Application

This directory contains production-ready Kubernetes manifests for deploying the Flask panel application with high availability, auto-scaling, and security best practices.

## 🏗️ **Architecture Overview**

- **Web Application**: 3 replicas with rolling updates and health checks
- **Background Workers**: 2 RQ worker instances for job processing
- **Auto-scaling**: Horizontal Pod Autoscaler (3-10 replicas based on CPU/memory)
- **Load Balancing**: Nginx Ingress with SSL termination
- **Security**: Network policies, secrets management, and RBAC
- **Storage**: Persistent volumes for data persistence
- **Monitoring**: Health checks and resource monitoring

## 📁 **Manifest Structure**

```
k8s/
├── deployment.yaml          # Main application deployment
├── service.yaml            # ClusterIP service
├── configmap.yaml          # Application configuration
├── secrets.yaml            # Sensitive data (base64 encoded)
├── ingress.yaml            # External access with SSL
├── hpa.yaml               # Auto-scaling configuration
├── worker-deployment.yaml # Background job workers
├── network-policy.yaml     # Security policies
├── pvc.yaml               # Persistent storage
├── migration-job.yaml      # Database migrations
├── kustomization.yaml      # Kustomize configuration
└── patches/               # Kustomize patches
    ├── env-patches.yaml
    └── deployment-patches.yaml
```

## 🚀 **Quick Start**

### Prerequisites
- Kubernetes cluster (v1.19+)
- kubectl configured
- Docker registry access
- cert-manager (for SSL certificates)
- nginx-ingress controller

### 1. Build and Push Docker Image
```bash
# Build the image
docker build -t panel:latest .

# Tag for your registry
docker tag panel:latest your-registry.com/panel:latest

# Push to registry
docker push your-registry.com/panel:latest
```

### 2. Configure Secrets
Edit `secrets.yaml` and update the base64 encoded values:

```bash
# Generate base64 encoded secrets
echo -n "your-database-url" | base64
echo -n "your-jwt-secret" | base64
echo -n "your-google-client-id" | base64
# ... etc
```

### 3. Update Configuration
Edit the following files with your environment values:
- `ingress.yaml`: Update domain name
- `configmap.yaml`: Adjust resource limits and configuration
- `secrets.yaml`: Update all secret values

### 4. Deploy with Kustomize
```bash
# Deploy to Kubernetes
kubectl apply -k .

# Or deploy individual components
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml
kubectl apply -f worker-deployment.yaml
kubectl apply -f network-policy.yaml
kubectl apply -f pvc.yaml
```

### 5. Run Database Migrations
```bash
# Run the migration job
kubectl apply -f migration-job.yaml

# Check migration status
kubectl logs job/panel-migration
```

## 🔧 **Configuration**

### Environment Variables

#### Application Settings
- `FLASK_ENV`: Set to "production"
- `SECRET_KEY`: Flask secret key for sessions
- `JWT_SECRET_KEY`: Secret for JWT token signing

#### Database
- `DATABASE_URL`: PostgreSQL connection string
- `SQLALCHEMY_TRACK_MODIFICATIONS`: Set to "false"

#### Redis/Caching
- `REDIS_URL`: Redis connection string
- `CACHE_REDIS_URL`: Redis URL for Flask-Caching
- `RQ_REDIS_URL`: Redis URL for RQ job queues

#### OAuth Providers
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `GITHUB_CLIENT_ID`: GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET`: GitHub OAuth client secret

#### Monitoring
- `METRICS_ENABLED`: Enable Prometheus metrics
- `SENTRY_DSN`: Sentry error tracking DSN

### Resource Limits
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## 📊 **Monitoring & Observability**

### Health Checks
- **Liveness Probe**: `/health` endpoint
- **Readiness Probe**: `/health` endpoint
- **Startup Probe**: Ensures app starts correctly

### Metrics
The application exposes metrics at `/metrics` endpoint for Prometheus.

### Logs
```bash
# View application logs
kubectl logs -l app=panel,component=web

# View worker logs
kubectl logs -l app=panel,component=worker

# Follow logs in real-time
kubectl logs -f deployment/panel-app
```

## 🔒 **Security Features**

### Network Policies
- Restricts ingress/egress traffic
- Allows only necessary communication between pods
- Blocks unauthorized access

### Secrets Management
- All sensitive data stored in Kubernetes secrets
- Base64 encoded for additional security
- Separate secrets for different environments

### SSL/TLS
- Automatic SSL certificate provisioning with cert-manager
- SSL redirect enabled
- Secure headers configured

## 📈 **Scaling**

### Horizontal Pod Autoscaler
- Scales based on CPU (70%) and memory (80%) utilization
- Minimum 3 replicas, maximum 10 replicas
- Stabilization windows prevent thrashing

### Manual Scaling
```bash
# Scale deployment
kubectl scale deployment panel-app --replicas=5

# Scale workers
kubectl scale deployment panel-worker --replicas=3
```

## 🔄 **Updates & Rollbacks**

### Rolling Updates
```bash
# Update image
kubectl set image deployment/panel-app panel=panel:v2.0.0

# Check rollout status
kubectl rollout status deployment/panel-app

# Rollback if needed
kubectl rollout undo deployment/panel-app
```

### Blue-Green Deployment
```bash
# Create new deployment with different label
kubectl apply -f deployment-v2.yaml

# Switch service selector
kubectl patch service panel-service -p '{"spec":{"selector":{"version":"v2.0.0"}}}'

# Remove old deployment
kubectl delete deployment panel-app-v1
```

## 🐛 **Troubleshooting**

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
kubectl get pods -l app=panel

# Check pod events
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name> --previous
```

#### Database Connection Issues
```bash
# Test database connectivity
kubectl exec -it <pod-name> -- python -c "import psycopg2; psycopg2.connect(os.environ['DATABASE_URL'])"
```

#### Redis Connection Issues
```bash
# Test Redis connectivity
kubectl exec -it <pod-name> -- python -c "import redis; redis.Redis.from_url(os.environ['REDIS_URL']).ping()"
```

### Health Checks
```bash
# Manual health check
curl https://your-domain.com/health

# Check all pods health
kubectl get pods -l app=panel
```

## 📚 **Additional Resources**

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kubectl.docs.kubernetes.io/references/kustomize/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [nginx-ingress Documentation](https://kubernetes.github.io/ingress-nginx/)

## 🎯 **Production Checklist**

- [ ] Update all secret values in `secrets.yaml`
- [ ] Configure domain in `ingress.yaml`
- [ ] Set up cert-manager for SSL certificates
- [ ] Configure external DNS
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backup solutions
- [ ] Set up log aggregation
- [ ] Configure alerting
- [ ] Test auto-scaling
- [ ] Perform load testing
- [ ] Set up CI/CD pipeline