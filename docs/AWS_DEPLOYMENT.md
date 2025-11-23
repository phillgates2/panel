# AWS Production Deployment Guide

This guide provides step-by-step instructions for deploying the Panel application to AWS using best practices for scalability, security, and cost optimization.

## Architecture Overview

```
Internet
    ?
CloudFront (CDN)
    ?
Application Load Balancer
    ?
ECS Fargate (Application)
    ?
RDS PostgreSQL (Database)
    ?
ElastiCache Redis (Cache)
    ?
S3 (File Storage)
    ?
CloudWatch (Monitoring)
```

## Prerequisites

### AWS Account Setup
1. **AWS Account**: Create an AWS account with appropriate permissions
2. **IAM User**: Create an IAM user with programmatic access
3. **AWS CLI**: Install and configure AWS CLI
4. **Terraform**: Install Terraform for infrastructure as code

### Domain and SSL
1. **Route 53**: Register domain or transfer existing domain
2. **ACM Certificate**: Request SSL certificate for your domain

### Application Preparation
1. **Environment Variables**: Configure production environment variables
2. **Secrets**: Store sensitive data in AWS Secrets Manager
3. **Build Application**: Create production Docker image

## Infrastructure Setup

### 1. VPC and Networking

```hcl
# vpc.tf
resource "aws_vpc" "panel_vpc" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true

  tags = {
    Name = "panel-vpc"
  }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.panel_vpc.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "panel-public-${count.index + 1}"
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.panel_vpc.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "panel-private-${count.index + 1}"
  }
}
```

### 2. Security Groups

```hcl
# security.tf
resource "aws_security_group" "alb" {
  name_prefix = "panel-alb-"
  vpc_id      = aws_vpc.panel_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs" {
  name_prefix = "panel-ecs-"
  vpc_id      = aws_vpc.panel_vpc.id

  ingress {
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### 3. RDS PostgreSQL Database

```hcl
# rds.tf
resource "aws_db_subnet_group" "panel" {
  name       = "panel-db-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "panel-db-subnet"
  }
}

resource "aws_db_instance" "panel" {
  identifier             = "panel-db"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  db_name                = "panel"
  username               = "panel"
  password               = aws_secretsmanager_secret_version.db_password.secret_string
  db_subnet_group_name   = aws_db_subnet_group.panel.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  skip_final_snapshot    = true

  tags = {
    Name = "panel-database"
  }
}
```

### 4. ElastiCache Redis

```hcl
# redis.tf
resource "aws_elasticache_subnet_group" "panel" {
  name       = "panel-redis-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_cluster" "panel" {
  cluster_id           = "panel-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  subnet_group_name    = aws_elasticache_subnet_group.panel.name
  security_group_ids   = [aws_security_group.redis.id]

  tags = {
    Name = "panel-redis"
  }
}
```

### 5. ECS Fargate Cluster

```hcl
# ecs.tf
resource "aws_ecs_cluster" "panel" {
  name = "panel-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "panel-cluster"
  }
}

resource "aws_ecs_task_definition" "panel" {
  family                   = "panel"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "panel"
      image = "${aws_ecr_repository.panel.repository_url}:latest"

      environment = [
        { name = "FLASK_ENV", value = "production" },
        { name = "DATABASE_URL", value = "postgresql://${aws_db_instance.panel.username}:${aws_db_instance.panel.password}@${aws_db_instance.panel.endpoint}/${aws_db_instance.panel.db_name}" },
        { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.panel.cache_nodes[0].address}:${aws_elasticache_cluster.panel.cache_nodes[0].port}" }
      ]

      secrets = [
        { name = "SECRET_KEY", valueFrom = aws_secretsmanager_secret.panel_secret.arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.panel.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "panel-task"
  }
}

resource "aws_ecs_service" "panel" {
  name            = "panel-service"
  cluster         = aws_ecs_cluster.panel.id
  task_definition = aws_ecs_task_definition.panel.arn
  desired_count   = 2

  network_configuration {
    security_groups  = [aws_security_group.ecs.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.panel.arn
    container_name   = "panel"
    container_port   = 5000
  }

  depends_on = [aws_lb_listener.panel]
}
```

### 6. Application Load Balancer

```hcl
# alb.tf
resource "aws_lb" "panel" {
  name               = "panel-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = {
    Name = "panel-alb"
  }
}

resource "aws_lb_target_group" "panel" {
  name        = "panel-tg"
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.panel_vpc.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/api/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}

resource "aws_lb_listener" "panel" {
  load_balancer_arn = aws_lb.panel.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate.panel.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.panel.arn
  }
}
```

### 7. CloudFront CDN

```hcl
# cloudfront.tf
resource "aws_cloudfront_distribution" "panel" {
  origin {
    domain_name = aws_lb.panel.dns_name
    origin_id   = "panel-alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = ""

  aliases = [var.domain_name]

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "panel-alb"

    forwarded_values {
      query_string = true
      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.panel.arn
    ssl_support_method  = "sni-only"
  }

  tags = {
    Name = "panel-cdn"
  }
}
```

## Application Deployment

### 1. Build Docker Image

```dockerfile
# Dockerfile.production
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

EXPOSE 5000

CMD ["python", "app.py"]
```

### 2. Build and Push to ECR

```bash
# Build image
docker build -f Dockerfile.production -t panel:latest .

# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag panel:latest <account>.dkr.ecr.us-east-1.amazonaws.com/panel:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/panel:latest
```

### 3. Environment Configuration

```bash
# .env.production
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://panel:password@panel-db.endpoint/panel
REDIS_URL=redis://panel-redis.endpoint:6379
S3_BUCKET=panel-uploads-production
CLOUDFRONT_URL=https://cdn.panel.com
BACKUP_S3_BUCKET=panel-backups-production
```

## Monitoring and Logging

### CloudWatch Setup

```hcl
# monitoring.tf
resource "aws_cloudwatch_log_group" "panel" {
  name              = "/ecs/panel"
  retention_in_days = 30

  tags = {
    Name = "panel-logs"
  }
}

resource "aws_cloudwatch_metric_alarm" "cpu_utilization" {
  alarm_name          = "panel-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ecs cpu utilization"

  dimensions = {
    ClusterName = aws_ecs_cluster.panel.name
    ServiceName = aws_ecs_service.panel.name
  }
}
```

### X-Ray Integration

```python
# src/panel/aws_monitoring.py
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask import XRayMiddleware

def init_xray(app):
    """Initialize AWS X-Ray monitoring"""
    xray_recorder.configure(
        service='panel-application',
        sampling=False,
        context_missing='LOG_ERROR'
    )

    XRayMiddleware(app, xray_recorder)
```

## Backup and Recovery

### Automated Backups

```hcl
# backup.tf
resource "aws_backup_vault" "panel" {
  name = "panel-backup-vault"
}

resource "aws_backup_plan" "panel" {
  name = "panel-backup-plan"

  rule {
    rule_name         = "panel-daily-backup"
    target_vault_name = aws_backup_vault.panel.name
    schedule          = "cron(0 2 ? * * *)"

    lifecycle {
      delete_after = 30
    }
  }
}

resource "aws_backup_selection" "panel_rds" {
  name         = "panel-rds-backup"
  iam_role_arn = aws_iam_role.backup.arn
  plan_id      = aws_backup_plan.panel.id

  resources = [
    aws_db_instance.panel.arn
  ]
}
```

## Security Configuration

### IAM Roles

```hcl
# iam.tf
resource "aws_iam_role" "ecs_execution_role" {
  name = "panel-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name = "panel-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_role_policy" {
  name = "panel-ecs-task-role-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Effect = "Allow"
        Resource = [
          "${aws_s3_bucket.panel_uploads.arn}/*"
        ]
      },
      {
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Effect = "Allow"
        Resource = [
          aws_secretsmanager_secret.panel_secret.arn
        ]
      }
    ]
  })
}
```

### Secrets Manager

```hcl
# secrets.tf
resource "aws_secretsmanager_secret" "panel_secret" {
  name = "panel/secret-key"
}

resource "aws_secretsmanager_secret_version" "panel_secret" {
  secret_id     = aws_secretsmanager_secret.panel_secret.id
  secret_string = "your-super-secret-key-here"
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "panel/db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = "your-db-password-here"
}
```

## Cost Optimization

### Auto Scaling

```hcl
# autoscaling.tf
resource "aws_appautoscaling_target" "panel" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.panel.name}/${aws_ecs_service.panel.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "panel_cpu" {
  name               = "panel-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.panel.resource_id
  scalable_dimension = aws_appautoscaling_target.panel.scalable_dimension
  service_namespace  = aws_appautoscaling_target.panel.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

### Reserved Instances

```hcl
# For production workloads, consider reserved instances
# This can save up to 75% on EC2 costs
```

## Deployment Process

### 1. Infrastructure Deployment

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file=production.tfvars

# Apply changes
terraform apply -var-file=production.tfvars
```

### 2. Application Deployment

```bash
# Build and push Docker image
./scripts/deploy.sh

# Update ECS service
aws ecs update-service --cluster panel-cluster --service panel-service --force-new-deployment
```

### 3. DNS Configuration

```hcl
# route53.tf
resource "aws_route53_record" "panel" {
  zone_id = aws_route53_zone.panel.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.panel.domain_name
    zone_id                = aws_cloudfront_distribution.panel.hosted_zone_id
    evaluate_target_health = false
  }
}
```

## Monitoring and Maintenance

### Health Checks

```bash
# Application health
curl https://yourdomain.com/api/health

# Database connectivity
aws rds describe-db-instances --db-instance-identifier panel-db

# ECS service status
aws ecs describe-services --cluster panel-cluster --services panel-service
```

### Log Analysis

```bash
# View application logs
aws logs tail /ecs/panel --follow

# CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=panel-cluster Name=ServiceName,Value=panel-service \
  --start-time 2023-12-01T00:00:00Z \
  --end-time 2023-12-02T00:00:00Z \
  --period 300 \
  --statistics Average
```

### Backup Verification

```bash
# List RDS backups
aws rds describe-db-snapshots --db-instance-identifier panel-db

# Test backup restoration
aws backup list-recovery-points-by-backup-vault --backup-vault-name panel-backup-vault
```

## Troubleshooting

### Common Issues

1. **ECS Service Won't Start**
   ```bash
   # Check task logs
   aws ecs describe-tasks --cluster panel-cluster --tasks $(aws ecs list-tasks --cluster panel-cluster --service-name panel-service --query taskArns[0] --output text)
   ```

2. **Database Connection Issues**
   ```bash
   # Check security groups
   aws ec2 describe-security-groups --group-ids $(aws rds describe-db-instances --db-instance-identifier panel-db --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text)
   ```

3. **Load Balancer Health Checks Failing**
   ```bash
   # Check target group health
   aws elbv2 describe-target-health --target-group-arn $(aws elbv2 describe-target-groups --names panel-tg --query 'TargetGroups[0].TargetGroupArn' --output text)
   ```

## Cost Monitoring

### AWS Cost Explorer

```bash
# Get cost by service
aws ce get-cost-and-usage \
  --time-period Start=2023-12-01,End=2023-12-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

### Budget Alerts

```hcl
# budget.tf
resource "aws_budgets_budget" "panel" {
  name         = "panel-monthly-budget"
  budget_type  = "COST"
  limit_amount = "100.0"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "Service"
    values = ["Amazon Elastic Compute Cloud - Compute", "Amazon Relational Database Service"]
  }
}
```

This AWS deployment provides a production-ready, scalable, and secure infrastructure for the Panel application with comprehensive monitoring, backup, and cost optimization features.