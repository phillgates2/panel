# Panel AWS Infrastructure
# Terraform configuration for production deployment

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "panel-terraform-state"
    key    = "panel/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Panel"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Flask secret key"
  type        = string
  sensitive   = true
}

# VPC Configuration
resource "aws_vpc" "panel_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "panel-vpc"
  }
}

resource "aws_internet_gateway" "panel_igw" {
  vpc_id = aws_vpc.panel_vpc.id

  tags = {
    Name = "panel-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.panel_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.panel_igw.id
  }

  tags = {
    Name = "panel-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.panel_vpc.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

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

# NAT Gateway for private subnets
resource "aws_eip" "nat" {
  count = 2
  vpc   = true

  tags = {
    Name = "panel-nat-eip-${count.index + 1}"
  }
}

resource "aws_nat_gateway" "panel_nat" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "panel-nat-${count.index + 1}"
  }
}

resource "aws_route_table" "private" {
  count  = 2
  vpc_id = aws_vpc.panel_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.panel_nat[count.index].id
  }

  tags = {
    Name = "panel-private-rt-${count.index + 1}"
  }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# Security Groups
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

  tags = {
    Name = "panel-alb-sg"
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

  tags = {
    Name = "panel-ecs-sg"
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "panel-rds-"
  vpc_id      = aws_vpc.panel_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "panel-rds-sg"
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "panel-redis-"
  vpc_id      = aws_vpc.panel_vpc.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "panel-redis-sg"
  }
}

# RDS PostgreSQL
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
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.panel.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  skip_final_snapshot    = true
  backup_retention_period = 7
  multi_az               = false

  tags = {
    Name = "panel-database"
  }
}

# ElastiCache Redis
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

# S3 Bucket for uploads
resource "aws_s3_bucket" "panel_uploads" {
  bucket = "panel-uploads-${var.environment}"

  tags = {
    Name = "panel-uploads"
  }
}

resource "aws_s3_bucket_versioning" "panel_uploads" {
  bucket = aws_s3_bucket.panel_uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "panel_uploads" {
  bucket = aws_s3_bucket.panel_uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ECR Repository
resource "aws_ecr_repository" "panel" {
  name                 = "panel"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "panel-ecr"
  }
}

# ECS Cluster
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

# IAM Roles
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

  tags = {
    Name = "panel-ecs-execution-role"
  }
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

  tags = {
    Name = "panel-ecs-task-role"
  }
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
          aws_secretsmanager_secret.panel_secret.arn,
          aws_secretsmanager_secret.db_password.arn
        ]
      }
    ]
  })
}

# Secrets Manager
resource "aws_secretsmanager_secret" "panel_secret" {
  name = "panel/secret-key"
  description = "Panel Flask secret key"

  tags = {
    Name = "panel-secret-key"
  }
}

resource "aws_secretsmanager_secret_version" "panel_secret" {
  secret_id     = aws_secretsmanager_secret.panel_secret.id
  secret_string = var.secret_key
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "panel/db-password"
  description = "Panel database password"

  tags = {
    Name = "panel-db-password"
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

# ECS Task Definition
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
        { name = "FLASK_ENV", value = var.environment },
        { name = "DATABASE_URL", value = "postgresql://${aws_db_instance.panel.username}:${aws_db_instance.panel.password}@${aws_db_instance.panel.endpoint}/${aws_db_instance.panel.db_name}" },
        { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.panel.cache_nodes[0].address}:${aws_elasticache_cluster.panel.cache_nodes[0].port}" },
        { name = "S3_BUCKET", value = aws_s3_bucket.panel_uploads.bucket },
        { name = "AWS_REGION", value = var.aws_region }
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

      healthCheck = {
        command = [
          "CMD-SHELL",
          "curl -f http://localhost:5000/api/health || exit 1"
        ]
        interval = 30
        timeout  = 5
        retries  = 3
      }
    }
  ])

  tags = {
    Name = "panel-task"
  }
}

# Application Load Balancer
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

  tags = {
    Name = "panel-tg"
  }
}

resource "aws_lb_listener" "panel_http" {
  load_balancer_arn = aws_lb.panel.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ACM Certificate (you'll need to request this manually or use DNS validation)
resource "aws_acm_certificate" "panel" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  tags = {
    Name = "panel-certificate"
  }
}

resource "aws_lb_listener" "panel_https" {
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

# ECS Service
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

  depends_on = [aws_lb_listener.panel_https]
}

# CloudFront CDN
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

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "panel" {
  name              = "/ecs/panel"
  retention_in_days = 30

  tags = {
    Name = "panel-logs"
  }
}

# Auto Scaling
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

# Route 53 (optional - if you want to manage DNS with Terraform)
resource "aws_route53_zone" "panel" {
  name = var.domain_name

  tags = {
    Name = "panel-zone"
  }
}

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

# Outputs
output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.panel.dns_name
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.panel.domain_name
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.panel.repository_url
}

output "rds_endpoint" {
  description = "RDS database endpoint"
  value       = aws_db_instance.panel.endpoint
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_cluster.panel.cache_nodes[0].address
}

output "s3_bucket_name" {
  description = "S3 bucket for uploads"
  value       = aws_s3_bucket.panel_uploads.bucket
}