# Panel GCP Infrastructure
# Terraform configuration for production deployment

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }

  backend "gcs" {
    bucket = "panel-terraform-state"
    prefix = "panel/terraform.tfstate"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
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

variable "billing_account" {
  description = "GCP Billing Account ID"
  type        = string
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "dns.googleapis.com"
  ])

  service = each.key

  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "panel_vpc" {
  name                    = "panel-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.required_apis]
}

resource "google_compute_subnetwork" "panel_subnet" {
  name          = "panel-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.panel_vpc.id

  private_ip_google_access = true
}

# Cloud SQL PostgreSQL
resource "google_sql_database_instance" "panel" {
  name             = "panel-db-instance"
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

    disk_autoresize = true
    disk_size       = 10
    disk_type       = "PD_SSD"
  }

  deletion_protection = false

  depends_on = [google_project_service.required_apis]
}

resource "google_sql_database" "panel" {
  name     = "panel"
  instance = google_sql_database_instance.panel.name
}

resource "google_sql_user" "panel" {
  name     = "panel"
  instance = google_sql_database_instance.panel.name
  password = var.db_password
}

# Memorystore Redis
resource "google_redis_instance" "panel" {
  name           = "panel-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  authorized_network = google_compute_network.panel_vpc.id

  depends_on = [google_project_service.required_apis]
}

# Cloud Storage
resource "google_storage_bucket" "panel_uploads" {
  name          = "${var.project_id}-panel-uploads"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Secret Manager
resource "google_secret_manager_secret" "db_url" {
  secret_id = "panel-db-url"

  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "db_url" {
  secret = google_secret_manager_secret.db_url.id

  secret_data = "postgresql://${google_sql_user.panel.name}:${var.db_password}@${google_sql_database_instance.panel.private_ip_address}:5432/${google_sql_database.panel.name}"
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "panel-redis-url"

  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret = google_secret_manager_secret.redis_url.id

  secret_data = "redis://${google_redis_instance.panel.host}:${google_redis_instance.panel.port}"
}

resource "google_secret_manager_secret" "secret_key" {
  secret_id = "panel-secret-key"

  replication {
    automatic = true
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "secret_key" {
  secret = google_secret_manager_secret.secret_key.id

  secret_data = var.secret_key
}

# Service Account
resource "google_service_account" "panel" {
  account_id   = "panel-service-account"
  display_name = "Panel Service Account"
}

resource "google_project_iam_member" "panel_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.panel.email}"
}

resource "google_project_iam_member" "panel_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.panel.email}"
}

# Container Registry
resource "google_container_registry" "panel" {
  location = "US"

  depends_on = [google_project_service.required_apis]
}

# Cloud Run
resource "google_cloud_run_service" "panel" {
  name     = "panel-app"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/panel:latest"

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

        env {
          name  = "GCS_BUCKET"
          value = google_storage_bucket.panel_uploads.name
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
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
        "autoscaling.knative.dev/minScale"  = "1"
        "run.googleapis.com/cpu-throttling" = "false"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.required_apis]
}

# Cloud Load Balancer
resource "google_compute_global_address" "panel" {
  name = "panel-ip"
}

resource "google_compute_region_network_endpoint_group" "panel" {
  name                  = "panel-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = google_cloud_run_service.panel.name
  }
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

# SSL Certificate
resource "google_compute_managed_ssl_certificate" "panel" {
  name = "panel-cert"

  managed {
    domains = [var.domain_name]
  }
}

resource "google_compute_target_https_proxy" "panel" {
  name             = "panel-https-proxy"
  url_map          = google_compute_url_map.panel.id
  ssl_certificates = [google_compute_managed_ssl_certificate.panel.id]
}

resource "google_compute_global_forwarding_rule" "panel_https" {
  name       = "panel-https-forwarding-rule"
  target     = google_compute_target_https_proxy.panel.id
  port_range = "443"
  ip_address = google_compute_global_address.panel.address
}

# Vertex AI
resource "google_vertex_ai_endpoint" "panel_ai" {
  name         = "panel-ai-endpoint"
  display_name = "Panel AI Endpoint"
  location     = var.region

  depends_on = [google_project_service.required_apis]
}

# Cloud DNS (optional)
resource "google_dns_managed_zone" "panel" {
  name        = "panel-zone"
  dns_name    = "${var.domain_name}."
  description = "Panel DNS zone"

  depends_on = [google_project_service.required_apis]
}

resource "google_dns_record_set" "panel" {
  name = google_dns_managed_zone.panel.dns_name
  type = "A"
  ttl  = 300

  managed_zone = google_dns_managed_zone.panel.name

  rrdatas = [google_compute_global_address.panel.address]
}

# Monitoring
resource "google_monitoring_dashboard" "panel" {
  dashboard_json = jsonencode({
    displayName = "Panel Application Dashboard"
    gridLayout = {
      widgets = [
        {
          title = "Cloud Run Request Count"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\""
                }
              }
            }]
          }
        },
        {
          title = "Cloud Run Latency"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"run.googleapis.com/request_latencies\" resource.type=\"cloud_run_revision\""
                }
              }
            }]
          }
        }
      ]
    }
  })

  depends_on = [google_project_service.required_apis]
}

# Budget
resource "google_billing_budget" "panel" {
  billing_account = var.billing_account
  display_name    = "Panel Monthly Budget"

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
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  depends_on = [google_project_service.required_apis]
}

# Outputs
output "cloud_run_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_service.panel.status[0].url
}

output "load_balancer_ip" {
  description = "Load balancer IP address"
  value       = google_compute_global_address.panel.address
}

output "database_connection" {
  description = "Database connection string"
  value       = "postgresql://${google_sql_user.panel.name}:[PASSWORD]@${google_sql_database_instance.panel.private_ip_address}:5432/${google_sql_database.panel.name}"
  sensitive   = true
}

output "redis_connection" {
  description = "Redis connection string"
  value       = "redis://${google_redis_instance.panel.host}:${google_redis_instance.panel.port}"
}

output "storage_bucket" {
  description = "Cloud Storage bucket name"
  value       = google_storage_bucket.panel_uploads.name
}

output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.panel.email
}