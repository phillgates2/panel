# Azure Deployment Quick Start

This guide provides a quick start for deploying the Panel application to Microsoft Azure using the automated deployment scripts.

## Prerequisites

1. **Azure Account**: Create an Azure account with appropriate subscriptions
2. **Azure CLI**: Install and configure Azure CLI (`az login`)
3. **Terraform**: Install Terraform (v1.0+)
4. **Docker**: Install Docker for container builds
5. **Domain Name**: Register domain or transfer existing domain

## Quick Deployment

### 1. Clone and Setup

```bash
git clone https://github.com/phillgates2/panel.git
cd panel
```

### 2. Configure Azure Credentials

```bash
az login
# Select your subscription
az account set --subscription "your-subscription-id"
```

### 3. Update Configuration

Edit `infrastructure/azure/production.tfvars`:

```hcl
location     = "East US"
environment  = "production"
domain_name  = "yourdomain.com"  # Your actual domain
alert_email  = "admin@yourdomain.com"  # Your alert email
db_password  = "your-secure-db-password"
secret_key   = "your-super-secret-flask-key"
```

### 4. Deploy Everything

```bash
make azure-deploy-full
```

This single command will:
- Set up all Azure infrastructure (VNet, AKS, PostgreSQL, etc.)
- Build and push Docker image to Azure Container Registry
- Deploy application to Azure Container Apps
- Configure Azure Front Door CDN
- Set up Azure Monitor and alerts

## Manual Step-by-Step Deployment

If you prefer more control:

```bash
# 1. Plan infrastructure
make azure-deploy-plan

# 2. Review and apply infrastructure
make azure-deploy-apply

# 3. Build and push image
make azure-deploy-build

# 4. Deploy application
make azure-deploy-app

# 5. Run health checks
make azure-health
```

## Post-Deployment Configuration

### 1. DNS Configuration

The deployment creates an Azure Front Door endpoint. Update your DNS:

```bash
# The Terraform output will show the Front Door endpoint
# Point your domain's CNAME record to this endpoint
```

### 2. SSL Certificate

Azure Front Door automatically provisions SSL certificates for custom domains.

### 3. Environment Variables

Sensitive configuration is stored in Azure Key Vault automatically.

## Accessing Your Application

After deployment:

1. **Application URL**: `https://yourdomain.com`
2. **API Documentation**: `https://yourdomain.com/api/docs`
3. **Health Check**: `https://yourdomain.com/api/health`

## AI Features

The deployment includes Azure OpenAI integration for:

- **Content Moderation**: Automatic moderation of forum posts
- **AI Assistant**: Intelligent chat support for users
- **Tag Suggestions**: AI-powered tag suggestions for posts
- **Sentiment Analysis**: Analysis of user feedback
- **Content Summarization**: Automatic content summaries

## Monitoring and Maintenance

### Check Deployment Status

```bash
make azure-status
```

### View Logs

```bash
# Application logs
az monitor app-insights query \
  --app "panel-app-insights" \
  --analytics-query "requests | limit 10"

# Container logs
az containerapp logs show \
  --name panel-app \
  --resource-group panel-rg
```

### Update Application

For application updates:

```bash
make azure-deploy-update
```

## Troubleshooting

### Common Issues

1. **Terraform State Lock**
   ```bash
   # Force unlock if needed
   terraform force-unlock LOCK_ID
   ```

2. **Container App Issues**
   ```bash
   # Check container status
   az containerapp show --name panel-app --resource-group panel-rg
   ```

3. **Database Connection Issues**
   ```bash
   # Check PostgreSQL status
   az postgres flexible-server show --name panel-db --resource-group panel-rg
   ```

### Logs and Debugging

```bash
# View application logs
az containerapp logs show --name panel-app --resource-group panel-rg

# Check Azure Monitor
az monitor metrics list \
  --resource /subscriptions/.../resourceGroups/panel-rg/providers/Microsoft.App/containerApps/panel-app \
  --metric "Requests"

# Infrastructure logs
cd infrastructure/azure && terraform output
```

## Cost Optimization

### Azure Cost Management

- **Auto-scaling**: Container Apps scale to zero when not in use
- **Reserved Instances**: Consider reservations for predictable workloads
- **Storage Tiers**: Use appropriate storage tiers for cost optimization
- **Monitoring**: Set up budgets and alerts

## Security Considerations

### Network Security
- **Virtual Network**: All resources in private VNet
- **NSG Rules**: Restrictive network security groups
- **Private Endpoints**: Secure database connections

### Data Security
- **Encryption**: Data encrypted at rest and in transit
- **Key Vault**: Secrets stored securely
- **RBAC**: Role-based access control

### Compliance
- **Azure Security Center**: Continuous security monitoring
- **Compliance Certifications**: SOC 2, ISO 27001, etc.

## Scaling

### Horizontal Scaling
Container Apps automatically scale based on:
- CPU utilization (>70%)
- Concurrent requests (>10)
- Custom metrics

### Database Scaling
- **vCores**: Scale compute resources
- **Storage**: Increase storage capacity
- **Read Replicas**: Add read replicas for performance

## Backup and Recovery

### Automated Backups
- **Database**: Daily PostgreSQL backups
- **Files**: Azure Storage versioning
- **Infrastructure**: Terraform state backups

### Manual Backups
```bash
# Create additional backup
make backup-create TYPE=database NAME=manual
```

### Disaster Recovery
```bash
# Full recovery (if needed)
make backup-recovery DIR=abfss://backups@panelstorage.dfs.core.windows.net/
```

## Support

For issues or questions:
1. Check the [Azure Deployment Guide](docs/AZURE_DEPLOYMENT.md)
2. Review Azure Monitor logs
3. Check Container App status
4. Contact Azure support if needed

## Next Steps

After successful deployment:
1. Configure monitoring alerts
2. Set up log aggregation
3. Configure backup notifications
4. Test auto-scaling
5. Set up CI/CD pipeline
6. Configure domain and SSL
7. Test all application features including AI

Your Panel application is now running on Azure with enterprise-grade infrastructure and AI capabilities! ??