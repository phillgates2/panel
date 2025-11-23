# Panel Azure Infrastructure
# Terraform configuration for production deployment

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "panel-terraform-state"
    storage_account_name = "panelterraformstate"
    container_name       = "tfstate"
    key                  = "panel.terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }

  skip_provider_registration = true
}

# Data sources
data "azurerm_client_config" "current" {}

# Variables
variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
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

variable "alert_email" {
  description = "Email for alerts"
  type        = string
}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Resource Group
resource "azurerm_resource_group" "panel" {
  name     = "panel-rg-${random_string.suffix.result}"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "Panel"
    ManagedBy   = "Terraform"
  }
}

# Virtual Network
resource "azurerm_virtual_network" "panel" {
  name                = "panel-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.panel.location
  resource_group_name = azurerm_resource_group.panel.name

  tags = {
    Environment = var.environment
  }
}

# Subnet for Container Apps
resource "azurerm_subnet" "app" {
  name                 = "app-subnet"
  resource_group_name  = azurerm_resource_group.panel.name
  virtual_network_name = azurerm_virtual_network.panel.name
  address_prefixes     = ["10.0.1.0/24"]

  delegation {
    name = "Microsoft.App.environments"
    service_delegation {
      name = "Microsoft.App/environments"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# Azure Container Registry
resource "azurerm_container_registry" "panel" {
  name                = "panelacr${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.panel.name
  location            = azurerm_resource_group.panel.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = {
    Environment = var.environment
  }
}

# Azure Database for PostgreSQL
resource "azurerm_postgresql_flexible_server" "panel" {
  name                   = "panel-db-${random_string.suffix.result}"
  resource_group_name    = azurerm_resource_group.panel.name
  location               = azurerm_resource_group.panel.location
  version                = "15"
  administrator_login    = "paneladmin"
  administrator_password = var.db_password
  storage_mb             = 32768
  sku_name               = "GP_Standard_D2s_v3"
  backup_retention_days  = 7

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_postgresql_flexible_server_database" "panel" {
  name      = "panel"
  server_id = azurerm_postgresql_flexible_server.panel.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.panel.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Azure Cache for Redis
resource "azurerm_redis_cache" "panel" {
  name                = "panel-redis-${random_string.suffix.result}"
  location            = azurerm_resource_group.panel.location
  resource_group_name = azurerm_resource_group.panel.name
  capacity            = 1
  family              = "C"
  sku_name            = "Basic"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  tags = {
    Environment = var.environment
  }
}

# Azure Blob Storage
resource "azurerm_storage_account" "panel" {
  name                     = "panelstorage${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.panel.name
  location                 = azurerm_resource_group.panel.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  min_tls_version          = "TLS1_2"

  blob_properties {
    versioning_enabled = true
  }

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_storage_container" "uploads" {
  name                  = "uploads"
  storage_account_name  = azurerm_storage_account.panel.name
  container_access_type = "private"
}

# Azure Key Vault
resource "azurerm_key_vault" "panel" {
  name                        = "panel-kv-${random_string.suffix.result}"
  location                    = azurerm_resource_group.panel.location
  resource_group_name         = azurerm_resource_group.panel.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false

  sku_name = "standard"

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Recover",
      "Backup",
      "Restore"
    ]
  }

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = var.db_password
  key_vault_id = azurerm_key_vault.panel.id
}

resource "azurerm_key_vault_secret" "secret_key" {
  name         = "secret-key"
  value        = var.secret_key
  key_vault_id = azurerm_key_vault.panel.id
}

# Azure OpenAI Service
resource "azurerm_cognitive_account" "panel_ai" {
  name                = "panel-openai-${random_string.suffix.result}"
  location            = azurerm_resource_group.panel.location
  resource_group_name = azurerm_resource_group.panel.name
  kind                = "OpenAI"
  sku_name            = "S0"

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_cognitive_deployment" "gpt4" {
  name                 = "gpt-4"
  cognitive_account_id = azurerm_cognitive_account.panel_ai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4"
    version = "0613"
  }

  scale {
    type = "Standard"
  }
}

resource "azurerm_cognitive_deployment" "gpt35_turbo" {
  name                 = "gpt-35-turbo"
  cognitive_account_id = azurerm_cognitive_account.panel_ai.id
  model {
    format  = "OpenAI"
    name    = "gpt-35-turbo"
    version = "0613"
  }

  scale {
    type = "Standard"
  }
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "panel" {
  name                = "panel-log-analytics-${random_string.suffix.result}"
  location            = azurerm_resource_group.panel.location
  resource_group_name = azurerm_resource_group.panel.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = var.environment
  }
}

# Container App Environment
resource "azurerm_container_app_environment" "panel" {
  name                       = "panel-env-${random_string.suffix.result}"
  location                   = azurerm_resource_group.panel.location
  resource_group_name        = azurerm_resource_group.panel.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.panel.id
}

# Container App
resource "azurerm_container_app" "panel" {
  name                         = "panel-app"
  container_app_environment_id = azurerm_container_app_environment.panel.id
  resource_group_name          = azurerm_resource_group.panel.name
  revision_mode                = "Single"

  template {
    container {
      name   = "panel"
      image  = "${azurerm_container_registry.panel.login_server}/panel:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "FLASK_ENV"
        value = var.environment
      }

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "REDIS_URL"
        secret_name = "redis-url"
      }

      env {
        name        = "SECRET_KEY"
        secret_name = "secret-key"
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT"
        value = azurerm_storage_account.panel.name
      }

      env {
        name        = "AZURE_STORAGE_KEY"
        secret_name = "storage-key"
      }

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = azurerm_cognitive_account.panel_ai.endpoint
      }

      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "openai-key"
      }

      env {
        name  = "AZURE_OPENAI_DEPLOYMENT_GPT4"
        value = azurerm_cognitive_deployment.gpt4.name
      }

      env {
        name  = "AZURE_OPENAI_DEPLOYMENT_GPT35"
        value = azurerm_cognitive_deployment.gpt35_turbo.name
      }
    }

    min_replicas = 1
    max_replicas = 10

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = 10
    }
  }

  ingress {
    external_enabled = true
    target_port      = 5000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  secret {
    name  = "database-url"
    value = "postgresql://${azurerm_postgresql_flexible_server.panel.administrator_login}:${var.db_password}@${azurerm_postgresql_flexible_server.panel.fqdn}:5432/${azurerm_postgresql_flexible_server_database.panel.name}"
  }

  secret {
    name  = "redis-url"
    value = "rediss://:${azurerm_redis_cache.panel.primary_access_key}@${azurerm_redis_cache.panel.hostname}:${azurerm_redis_cache.panel.ssl_port}"
  }

  secret {
    name  = "secret-key"
    value = var.secret_key
  }

  secret {
    name  = "storage-key"
    value = azurerm_storage_account.panel.primary_access_key
  }

  secret {
    name  = "openai-key"
    value = azurerm_cognitive_account.panel_ai.primary_access_key
  }

  tags = {
    Environment = var.environment
  }
}

# Azure Front Door (CDN)
resource "azurerm_cdn_frontdoor_profile" "panel" {
  name                = "panel-cdn-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.panel.name
  sku_name            = "Standard_AzureFrontDoor"

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_cdn_frontdoor_endpoint" "panel" {
  name                     = "panel-endpoint"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.panel.id
}

resource "azurerm_cdn_frontdoor_origin_group" "panel" {
  name                     = "panel-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.panel.id

  load_balancing {}
}

resource "azurerm_cdn_frontdoor_origin" "panel" {
  name                           = "panel-origin"
  cdn_frontdoor_origin_group_id  = azurerm_cdn_frontdoor_origin_group.panel.id
  host_name                      = azurerm_container_app.panel.ingress[0].fqdn
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = azurerm_container_app.panel.ingress[0].fqdn
}

resource "azurerm_cdn_frontdoor_route" "panel" {
  name                          = "panel-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.panel.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.panel.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.panel.id]

  supported_protocols    = ["Http", "Https"]
  patterns_to_match      = ["/*"]
  forwarding_protocol    = "HttpsOnly"
  link_to_default_domain = true
}

# Azure Monitor Alerts
resource "azurerm_monitor_metric_alert" "cpu_usage" {
  name                = "panel-cpu-alert"
  resource_group_name = azurerm_resource_group.panel.name
  scopes              = [azurerm_container_app.panel.id]
  description         = "Alert when CPU usage is high"

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "UsageCpu"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.panel.id
  }
}

resource "azurerm_monitor_action_group" "panel" {
  name                = "panel-action-group"
  resource_group_name = azurerm_resource_group.panel.name
  short_name          = "panelalert"

  email_receiver {
    name          = "admin"
    email_address = var.alert_email
  }
}

# Cost Management
resource "azurerm_consumption_budget_resource_group" "panel" {
  name              = "panel-budget"
  resource_group_id = azurerm_resource_group.panel.id

  amount     = 100
  time_grain = "Monthly"

  time_period {
    start_date = "2024-01-01T00:00:00Z"
  }

  notification {
    enabled   = true
    threshold = 80.0
    operator  = "EqualTo"

    contact_emails = [var.alert_email]
  }
}

# Outputs
output "container_app_url" {
  description = "Container App URL"
  value       = "https://${azurerm_container_app.panel.ingress[0].fqdn}"
}

output "frontdoor_endpoint" {
  description = "Front Door endpoint hostname"
  value       = azurerm_cdn_frontdoor_endpoint.panel.host_name
}

output "acr_login_server" {
  description = "ACR login server"
  value       = azurerm_container_registry.panel.login_server
}

output "database_server" {
  description = "PostgreSQL server FQDN"
  value       = azurerm_postgresql_flexible_server.panel.fqdn
}

output "redis_hostname" {
  description = "Redis hostname"
  value       = azurerm_redis_cache.panel.hostname
}

output "storage_account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.panel.name
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.panel.name
}

output "openai_endpoint" {
  description = "OpenAI endpoint"
  value       = azurerm_cognitive_account.panel_ai.endpoint
}