# GCP Production Deployment Guide

This guide provides step-by-step instructions for deploying the Panel application to Google Cloud Platform using best practices for scalability, security, and cost optimization.

## Architecture Overview

```
Internet
    ?
Cloud Load Balancer (Global)
    ?
Cloud Run (Application)
    ?
Cloud SQL PostgreSQL (Database)
    ?
Memorystore Redis (Cache)
    ?
Cloud Storage (File Storage)
    ?
Cloud Monitoring (Observability)
```

## Prerequisites

### GCP Account Setup
1. **Google Cloud Account**: Create a GCP account with billing enabled
2. **Google Cloud SDK**: Install and configure `gcloud` CLI
3. **Terraform**: Install Terraform for infrastructure as code
4. **Docker**: Install Docker for container builds

### Domain and SSL
1. **Cloud DNS**: Register domain or transfer existing domain
2. **SSL Certificates**: Managed SSL certificates via Google Cloud
3. **Custom Domain**: Configure custom domain for Cloud Run

### Application Preparation
1. **Environment Variables**: Configure production environment variables
2. **Secrets**: Store sensitive data in Google Cloud Secret Manager
3. **Build Application**: Create production Docker image

## Infrastructure Setup

### 1. VPC and Networking

```hcl
# vpc.tf
resource "google_compute_network" "panel_vpc" {
  name                    = "panel-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "panel_subnet" {
  name          = "panel-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.panel_vpc.id
}
```

### 2. Cloud SQL PostgreSQL

```hcl
# database.tf
resource "google_sql_database_instance" "panel" {
  name             = "panel-db"
  region           = var.region
  database_version = "POSTGRES_15"

  settings {
    tier = "db-f1-micro"

    backup_configuration {
      enabled    = true
      start_time = "02:00"
    }

    ip_configuration {
      ipv4_enabled = false
      private_network = google_compute_network.panel_vpc.id
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "panel" {
  name     = "panel"
  instance = google_sql_database_instance.panel.name
}
```

### 3. Memorystore Redis

```hcl
# redis.tf
resource "google_redis_instance" "panel" {
  name           = "panel-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  authorized_network = google_compute_network.panel_vpc.id
}
```

### 4. Cloud Run

```hcl
# cloud_run.tf
resource "google_cloud_run_service" "panel" {
  name     = "panel-app"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/panel-repo/panel:latest"

        env {
          name  = "FLASK_ENV"
          value = var.environment
        }

        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.db_url.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "REDIS_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.redis_url.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "SECRET_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.secret_key.secret_id
              key  = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }

      service_account_name = google_service_account.panel.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "10"
        "autoscaling.knative.dev/minScale" = "1"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
```

### 5. Cloud Load Balancer

```hcl
# load_balancer.tf
resource "google_compute_global_address" "panel" {
  name = "panel-ip"
}

resource "google_compute_backend_service" "panel" {
  name        = "panel-backend"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30

  backend {
    group = google_compute_region_network_endpoint_group.panel.id
  }
}

resource "google_compute_url_map" "panel" {
  name            = "panel-url-map"
  default_service = google_compute_backend_service.panel.id
}

resource "google_compute_target_http_proxy" "panel" {
  name    = "panel-http-proxy"
  url_map = google_compute_url_map.panel.id
}

resource "google_compute_global_forwarding_rule" "panel" {
  name       = "panel-forwarding-rule"
  target     = google_compute_target_http_proxy.panel.id
  port_range = "80"
  ip_address = google_compute_global_address.panel.address
}
```

### 6. Cloud Storage

```hcl
# storage.tf
resource "google_storage_bucket" "panel_uploads" {
  name          = "${var.project_id}-panel-uploads"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}
```

### 7. Secret Manager

```hcl
# secrets.tf
resource "google_secret_manager_secret" "db_url" {
  secret_id = "panel-db-url"

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "db_url" {
  secret      = google_secret_manager_secret.db_url.id
  secret_data = "postgresql://${google_sql_user.panel.name}:${var.db_password}@${google_sql_database_instance.panel.private_ip_address}:5432/${google_sql_database.panel.name}"
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "panel-redis-url"

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = "redis://${google_redis_instance.panel.host}:${google_redis_instance.panel.port}"
}

resource "google_secret_manager_secret" "secret_key" {
  secret_id = "panel-secret-key"

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "secret_key" {
  secret      = google_secret_manager_secret.secret_key.id
  secret_data = var.secret_key
}
```

## Application Deployment

### 1. Build Docker Image

```dockerfile
# Dockerfile.gcp
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Copy requirements and install
COPY --chown=app:app requirements/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application
COPY --chown=app:app . .

# Create necessary directories
RUN mkdir -p instance logs static/uploads

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

EXPOSE 5000

# Start application
CMD ["python", "app.py"]
```

### 2. Build and Push to GCR

```bash
# Build image
docker build -f Dockerfile.gcp -t panel:latest .

# Tag for GCR
docker tag panel:latest gcr.io/YOUR_PROJECT/panel:latest

# Push image
docker push gcr.io/YOUR_PROJECT/panel:latest
```

## AI Integration with Vertex AI

### Vertex AI Setup

```hcl
# ai.tf
resource "google_project_service" "vertex_ai" {
  service = "aiplatform.googleapis.com"
}

resource "google_vertex_ai_endpoint" "panel_ai" {
  name         = "panel-ai-endpoint"
  display_name = "Panel AI Endpoint"
  location     = var.region

  depends_on = [google_project_service.vertex_ai]
}
```

### AI Integration Code

```python
# src/panel/gcp_ai_integration.py
import os
import vertexai
from vertexai.generative_models import GenerativeModel
import logging

logger = logging.getLogger(__name__)

class GCPAIAgent:
    """GCP AI agent for enhanced AI capabilities"""

    def __init__(self):
        vertexai.init(project=os.getenv('GOOGLE_CLOUD_PROJECT'), location=os.getenv('GOOGLE_CLOUD_REGION'))
        self.model = GenerativeModel("gemini-1.5-pro")

    async def analyze_image(self, image_url: str) -> Dict[str, Any]:
        """Analyze images for content moderation and insights"""
        try:
            # Download and analyze image
            response = await self.model.generate_content([
                "Analyze this image for:",
                "1. Content appropriateness",
                "2. Main subjects/objects",
                "3. Text content (if any)",
                "4. Overall sentiment/mood",
                f"Image URL: {image_url}"
            ])

            return {
                'analysis': response.text,
                'moderated': self._check_image_moderation(response.text),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return {'error': str(e)}

    async def generate_content(self, prompt: str, content_type: str = "post") -> str:
        """Generate AI content for various purposes"""
        try:
            system_prompts = {
                "post": "Generate an engaging forum post about gaming.",
                "summary": "Create a concise summary of the following content.",
                "response": "Generate a helpful response to a user query.",
                "tutorial": "Create a step-by-step tutorial or guide."
            }

            full_prompt = f"{system_prompts.get(content_type, '')}\n\nPrompt: {prompt}"

            response = await self.model.generate_content([full_prompt])

            return response.text.strip()
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return "Content generation is currently unavailable."

    async def predict_user_behavior(self, user_history: List[Dict]) -> Dict[str, Any]:
        """Predict user behavior patterns"""
        try:
            history_text = "\n".join([f"{h['action']}: {h.get('details', '')}" for h in user_history[-10:]])

            prompt = f"""Based on this user activity history, predict:
1. User's interests/hobbies
2. Likely next actions
3. Engagement level (high/medium/low)
4. Suggested content/features

History:
{history_text}"""

            response = await self.model.generate_content([prompt])

            return {
                'predictions': response.text,
                'confidence': 0.8,  # Could be calculated based on model confidence
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Behavior prediction failed: {e}")
            return {'error': str(e)}

    async def classify_content_advanced(self, content: str, categories: List[str]) -> Dict[str, Any]:
        """Advanced content classification with explanations"""
        try:
            categories_str = ", ".join(categories)

            prompt = f"""Classify this content into the most relevant category from: {categories_str}

Content: {content}

Provide:
1. Primary category
2. Secondary category (if applicable)
3. Confidence level (0-1)
4. Detailed reasoning
5. Suggested tags"""

            response = await self.model.generate_content([prompt])

            return {
                'classification': response.text,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Advanced classification failed: {e}")
            return {'error': str(e)}

    def _check_image_moderation(self, analysis: str) -> bool:
        """Check if image analysis indicates inappropriate content"""
        inappropriate_keywords = [
            'inappropriate', 'explicit', 'violent', 'harmful',
            'offensive', 'nsfw', 'adult', 'nudity'
        ]

        analysis_lower = analysis.lower()
        return not any(keyword in analysis_lower for keyword in inappropriate_keywords)

# Global GCP AI agent
gcp_ai_agent = None

def init_gcp_ai():
    """Initialize GCP AI agent"""
    global gcp_ai_agent
    if os.getenv('GOOGLE_CLOUD_PROJECT'):
        try:
            gcp_ai_agent = GCPAIAgent()
            logger.info("GCP AI agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GCP AI: {e}")
    else:
        logger.warning("GCP AI not configured")

def get_gcp_ai_agent() -> Optional[GCPAIAgent]:
    """Get the GCP AI agent instance"""
    return gcp_ai_agent
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
gcloud builds submit --tag gcr.io/YOUR_PROJECT/panel:latest .
```

### 3. DNS Configuration

```bash
# Point your domain to the load balancer IP
gcloud dns record-sets create YOUR_DOMAIN \
  --rrdatas=LOAD_BALANCER_IP \
  --type=A \
  --zone=YOUR_DNS_ZONE
```

## Monitoring and Logging

### Cloud Monitoring Setup

```hcl
# monitoring.tf
resource "google_monitoring_dashboard" "panel" {
  dashboard_json = jsonencode({
    displayName = "Panel Application Dashboard"
    gridLayout = {
      widgets = [
        {
          title = "Request Count"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\""
                }
              }
            }]
          }
        }
      ]
    }
  })
}
```

## Cost Optimization

### GCP Cost Management

```hcl
# budgets.tf
resource "google_billing_budget" "panel" {
  billing_account = var.billing_account
  display_name    = "Panel Budget"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "100"
    }
  }

  threshold_rules {
    threshold_percent = 0.8
  }
}
```

This GCP deployment provides a production-ready, scalable, and secure infrastructure for the Panel application with integrated AI capabilities using Google Cloud Vertex AI.