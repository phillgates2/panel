# GCP Deployment Quick Start

This guide provides a quick start for deploying the Panel application to Google Cloud Platform using the automated deployment scripts.

## Prerequisites

1. **Google Cloud Account**: Create a GCP account with billing enabled
2. **Google Cloud SDK**: Install `gcloud` CLI (`gcloud init`)
3. **Terraform**: Install Terraform (v1.0+)
4. **Docker**: Install Docker for container builds
5. **Project**: Create a GCP project or use existing one
6. **Domain Name**: Register domain or transfer existing domain

## Quick Deployment

### 1. Clone and Setup

```bash
git clone https://github.com/phillgates2/panel.git
cd panel
```

### 2. Configure GCP Credentials

```bash
# Authenticate with Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 3. Update Configuration

Edit `infrastructure/gcp/production.tfvars`:

```hcl
project_id     = "your-gcp-project-id"  # Your GCP project ID
region         = "us-central1"
environment    = "production"
domain_name    = "yourdomain.com"  # Your actual domain
billing_account = "your-billing-account-id"  # Your billing account ID
db_password    = "your-secure-db-password"
secret_key     = "your-super-secret-flask-key"
```

### 4. Deploy Everything

```bash
make gcp-deploy-full
```

This single command will:
- Set up all GCP infrastructure (VPC, Cloud SQL, Cloud Run, etc.)
- Build and push Docker image to Google Container Registry
- Deploy application to Cloud Run
- Configure Cloud Load Balancer
- Set up Cloud Monitoring and alerts

## Manual Step-by-Step Deployment

If you prefer more control:

```bash
# 1. Plan infrastructure
make gcp-deploy-plan

# 2. Review and apply infrastructure
make gcp-deploy-apply

# 3. Build and push image
make gcp-deploy-build

# 4. Deploy application
make gcp-deploy-app

# 5. Run health checks
make gcp-health
```

## Post-Deployment Configuration

### 1. DNS Configuration

The deployment creates a Cloud Load Balancer. Update your DNS:

```bash
# The Terraform output will show the load balancer IP
# Create an A record pointing your domain to this IP
```

### 2. SSL Certificate

The deployment automatically provisions SSL certificates via Google-managed certificates.

### 3. Environment Variables

Sensitive configuration is stored in Google Secret Manager automatically.

## AI Features

The deployment includes Google Vertex AI integration for advanced AI capabilities:

- **Image Analysis**: Content analysis and moderation for uploaded images
- **Behavior Prediction**: User engagement and churn prediction
- **Personalized Content**: AI-generated personalized recommendations
- **Anomaly Detection**: System metrics anomaly detection
- **Trend Analysis**: Forum and user activity trend analysis

## Accessing Your Application

After deployment:

1. **Application URL**: `https://yourdomain.com`
2. **API Documentation**: `https://yourdomain.com/api/docs`
3. **Health Check**: `https://yourdomain.com/api/health`

## Monitoring and Maintenance

### Check Deployment Status

```bash
make gcp-status
```

### View Logs

```bash
# Application logs
gcloud logging read "resource.type=cloud_run_revision" --limit 10

# Cloud Run logs
gcloud run services logs read panel-app --region us-central1

# Infrastructure logs
cd infrastructure/gcp && terraform output
```

### Update Application

For application updates:

```bash
make gcp-deploy-update
```

## Troubleshooting

### Common Issues

1. **API Not Enabled**
   ```bash
   # Enable required APIs
   gcloud services enable run.googleapis.com sqladmin.googleapis.com
   ```

2. **Quota Exceeded**
   ```bash
   # Check quotas
   gcloud compute regions describe us-central1 --format "value(quotas)"
   ```

3. **Permission Denied**
   ```bash
   # Check IAM permissions
   gcloud projects get-iam-policy YOUR_PROJECT_ID
   ```

### Logs and Debugging

```bash
# View Cloud Run logs
gcloud run services logs read panel-app --region us-central1

# Check Cloud SQL status
gcloud sql instances describe panel-db --project YOUR_PROJECT_ID

# Monitor with Cloud Monitoring
gcloud monitoring dashboards list
```

## Cost Optimization

### GCP Cost Management

- **Cloud Run**: Scales to zero when not in use
- **Cloud SQL**: Pay only for what you use
- **Storage**: Automatic cost optimization
- **Budgets**: Automatic budget monitoring and alerts

## Security Considerations

### Network Security
- **VPC**: Isolated networking environment
- **Cloud NAT**: Secure outbound connections
- **Firewall Rules**: Restrictive security policies

### Data Security
- **Encryption**: Data encrypted at rest and in transit
- **Secret Manager**: Secure credential storage
- **IAM**: Principle of least privilege

### Compliance
- **Security Command Center**: Continuous security monitoring
- **Compliance**: SOC 2, ISO 27001, GDPR compliance

## Scaling

### Horizontal Scaling
Cloud Run automatically scales based on:
- **CPU Utilization**: Scales when CPU > 60%
- **Concurrent Requests**: Scales with request volume
- **Custom Metrics**: Configurable scaling rules

### Database Scaling
- **vCPUs**: Scale compute resources
- **Storage**: Automatic storage scaling
- **Read Replicas**: Add read replicas for performance

## Backup and Recovery

### Automated Backups
- **Cloud SQL**: Daily automated backups
- **Cloud Storage**: Object versioning
- **Infrastructure**: Terraform state backups

### Manual Backups
```bash
# Create additional backup
gcloud sql backups create panel-db-backup --instance panel-db
```

### Disaster Recovery
```bash
# Full recovery (if needed)
gcloud sql instances restore panel-db --backup panel-db-backup
```

## Support

For issues or questions:
1. Check the [GCP Deployment Guide](docs/GCP_DEPLOYMENT.md)
2. Review Cloud Logging
3. Check Cloud Run status
4. Contact Google Cloud support if needed

## Next Steps

After successful deployment:
1. Configure monitoring alerts
2. Set up log-based metrics
3. Configure budget alerts
4. Test auto-scaling
5. Set up CI/CD pipeline
6. Configure domain and SSL
7. Test all application features including AI

Your Panel application is now running on Google Cloud Platform with enterprise-grade infrastructure and advanced AI capabilities! ????