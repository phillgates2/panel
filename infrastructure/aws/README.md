# AWS Deployment Quick Start

This guide provides a quick start for deploying the Panel application to AWS using the automated deployment scripts.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Terraform** installed (v1.0+)
4. **Docker** installed
5. **Domain name** registered (Route 53 or external)

## Quick Deployment

### 1. Clone and Setup

```bash
git clone https://github.com/phillgates2/panel.git
cd panel
```

### 2. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and default region (us-east-1)
```

### 3. Update Configuration

Edit `infrastructure/aws/production.tfvars`:

```hcl
aws_region  = "us-east-1"
environment = "production"
domain_name = "yourdomain.com"  # Your actual domain
db_password = "your-secure-db-password"
secret_key  = "your-super-secret-flask-key"
```

### 4. Deploy Everything

```bash
make aws-deploy-full
```

This single command will:
- Set up all AWS infrastructure (VPC, RDS, ECS, etc.)
- Build and push Docker image to ECR
- Deploy application to ECS Fargate
- Configure CloudFront CDN
- Set up monitoring and alerts

## Manual Step-by-Step Deployment

If you prefer more control:

```bash
# 1. Plan infrastructure
make aws-deploy-plan

# 2. Review and apply infrastructure
make aws-deploy-apply

# 3. Build and push image
make aws-deploy-build

# 4. Deploy application
make aws-deploy-app

# 5. Run health checks
make aws-health
```

## Post-Deployment Configuration

### 1. DNS Configuration

The deployment script creates a CloudFront distribution. Update your DNS:

```bash
# If using Route 53 (automatically configured)
# If using external DNS, point your domain to the CloudFront domain
```

### 2. SSL Certificate

The script creates an ACM certificate. Complete DNS validation if needed.

### 3. Environment Variables

Update sensitive configuration in AWS Secrets Manager:

```bash
# The deployment creates secrets for database password and Flask secret key
# Update additional secrets as needed
```

## Accessing Your Application

After deployment:

1. **Application URL**: `https://yourdomain.com`
2. **API Documentation**: `https://yourdomain.com/api/docs`
3. **Health Check**: `https://yourdomain.com/api/health`

## Monitoring and Maintenance

### Check Deployment Status

```bash
make aws-status
```

### View Logs

```bash
# ECS logs
aws logs tail /ecs/panel --follow --region us-east-1

# CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --start-time 2023-12-01T00:00:00Z \
  --end-time 2023-12-02T00:00:00Z \
  --period 300 \
  --statistics Average
```

### Update Application

For application updates:

```bash
make aws-deploy-update
```

## Troubleshooting

### Common Issues

1. **Terraform State Lock**
   ```bash
   # Force unlock if needed
   terraform force-unlock LOCK_ID
   ```

2. **ECS Service Issues**
   ```bash
   # Check service events
   aws ecs describe-services --cluster panel-cluster --services panel-service
   ```

3. **Health Check Failures**
   ```bash
   # Check target group health
   aws elbv2 describe-target-health --target-group-arn YOUR_TG_ARN
   ```

### Logs and Debugging

```bash
# Application logs
aws logs tail /ecs/panel --region us-east-1

# Infrastructure logs
cd infrastructure/aws && terraform output

# Docker build logs
docker build -f Dockerfile.production -t panel:latest .
```

## Cost Optimization

### Reserved Instances
Consider purchasing reserved instances for production workloads to save up to 75%.

### Auto Scaling
The deployment includes CPU-based auto scaling. Monitor and adjust as needed.

### Storage Optimization
- Use S3 lifecycle policies for old backups
- Configure RDS backup retention appropriately

## Security Considerations

### Network Security
- All resources are in private subnets
- Security groups restrict access
- No public IPs on ECS tasks

### Data Security
- RDS encryption enabled
- S3 bucket encryption
- Secrets stored in Secrets Manager

### Access Control
- IAM roles with minimal permissions
- CloudTrail logging enabled
- VPC flow logs for network monitoring

## Backup and Recovery

### Automated Backups
- Database: Daily RDS snapshots
- Filesystem: S3 versioning
- Application: ECR image history

### Manual Backups
```bash
# Create additional backup
make backup-create TYPE=database NAME=manual
```

### Disaster Recovery
```bash
# Full recovery (if needed)
make backup-recovery DIR=s3://panel-backups-production/
```

## Support

For issues or questions:
1. Check the [AWS Deployment Guide](docs/AWS_DEPLOYMENT.md)
2. Review CloudWatch logs
3. Check ECS service events
4. Contact AWS support if needed

## Next Steps

After successful deployment:
1. Configure monitoring alerts
2. Set up log aggregation
3. Configure backup notifications
4. Test auto-scaling
5. Set up CI/CD pipeline
6. Configure domain and SSL
7. Test all application features

Your Panel application is now running on AWS with enterprise-grade infrastructure! ??