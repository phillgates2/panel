# Azure Production Deployment Guide

This guide provides step-by-step instructions for deploying the Panel application to Microsoft Azure using best practices for scalability, security, and cost optimization.

## Architecture Overview

```
Internet
    ?
Azure Front Door (CDN/Global Load Balancer)
    ?
Application Gateway (WAF + Load Balancer)
    ?
Azure Container Apps (Application)
    ?
Azure Database for PostgreSQL (Database)
    ?
Azure Cache for Redis (Cache)
    ?
Azure Blob Storage (File Storage)
    ?
Azure Monitor (Monitoring)
```

## Prerequisites

### Azure Account Setup
1. **Azure Account**: Create an Azure account with appropriate subscriptions
2. **Azure CLI**: Install and configure Azure CLI
3. **Terraform**: Install Terraform for infrastructure as code
4. **Docker**: Install Docker for container builds

### Domain and SSL
1. **Azure DNS**: Register domain or transfer existing domain
2. **Azure Key Vault**: Store SSL certificates and secrets
3. **Custom Domain**: Configure custom domain for Azure services

### Application Preparation
1. **Environment Variables**: Configure production environment variables
2. **Secrets**: Store sensitive data in Azure Key Vault
3. **Build Application**: Create production Docker image

## Infrastructure Setup

### 1. Resource Group and Networking

```hcl
# resource_group.tf
resource "azurerm_resource_group" "panel" {
  name     = "panel-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "Panel"
  }
}

# network.tf
resource "azurerm_virtual_network" "panel" {
  name                = "panel-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.panel.location
  resource_group_name = azurerm_resource_group.panel.name
}

resource "azurerm_subnet" "app" {
  name                 = "app-subnet"
  resource_group_name  = azurerm_resource_group.panel.location
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
```

### 2. Azure Database for PostgreSQL

```hcl
# database.tf
resource "azurerm_postgresql_flexible_server" "panel" {
  name                   = "panel-db"
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
```

### 3. Azure Cache for Redis

```hcl
# redis.tf
resource "azurerm_redis_cache" "panel" {
  name                = "panel-redis"
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
```

### 4. Azure Container Apps

```hcl
# container_app.tf
resource "azurerm_container_app_environment" "panel" {
  name                       = "panel-env"
  location                   = azurerm_resource_group.panel.location
  resource_group_name        = azurerm_resource_group.panel.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.panel.id
}

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

  tags = {
    Environment = var.environment
  }
}
```

### 5. Azure Front Door

```hcl
# frontdoor.tf
resource "azurerm_cdn_frontdoor_profile" "panel" {
  name                = "panel-cdn"
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
```

### 6. Azure Blob Storage

```hcl
# storage.tf
resource "azurerm_storage_account" "panel" {
  name                     = "panelstorage${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.panel.name
  location                 = azurerm_resource_group.panel.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_storage_container" "uploads" {
  name                  = "uploads"
  storage_account_name  = azurerm_storage_account.panel.name
  container_access_type = "private"
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}
```

### 7. Azure Key Vault

```hcl
# keyvault.tf
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
```

## Application Deployment

### 1. Build Docker Image

```dockerfile
# Dockerfile.azure
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

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

EXPOSE 5000

CMD ["python", "app.py"]
```

### 2. Build and Push to ACR

```bash
# Build image
docker build -f Dockerfile.azure -t panel:latest .

# Login to ACR
az acr login --name panelacr

# Tag and push
docker tag panel:latest panelacr.azurecr.io/panel:latest
docker push panelacr.azurecr.io/panel:latest
```

## Monitoring and Logging

### Azure Monitor Setup

```hcl
# monitoring.tf
resource "azurerm_log_analytics_workspace" "panel" {
  name                = "panel-log-analytics"
  location            = azurerm_resource_group.panel.location
  resource_group_name = azurerm_resource_group.panel.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = var.environment
  }
}

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
```

## AI Integration with Azure OpenAI

### Azure OpenAI Service Setup

```hcl
# ai.tf
resource "azurerm_cognitive_account" "panel_ai" {
  name                = "panel-openai"
  location            = azurerm_resource_group.panel.location
  resource_group_name = azurerm_resource_group.panel.name
  kind                = "OpenAI"

  sku_name = "S0"

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
```

### AI Integration Code

```python
# src/panel/ai_integration.py
import os
import openai
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class AzureOpenAIClient:
    """Azure OpenAI client for AI-powered features"""

    def __init__(self):
        self.client = openai.AzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version="2023-12-01-preview",
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
        )
        self.deployment_gpt4 = os.getenv('AZURE_OPENAI_DEPLOYMENT_GPT4', 'gpt-4')
        self.deployment_gpt35 = os.getenv('AZURE_OPENAI_DEPLOYMENT_GPT35', 'gpt-35-turbo')

    async def moderate_content(self, content: str) -> Dict[str, any]:
        """Moderate forum posts and comments for inappropriate content"""
        try:
            response = await self.client.moderations.create(
                input=content
            )

            result = response.results[0]
            return {
                'flagged': result.flagged,
                'categories': result.categories.dict(),
                'category_scores': result.category_scores.dict()
            }
        except Exception as e:
            logger.error(f"Content moderation failed: {e}")
            return {'flagged': False, 'error': str(e)}

    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Generate AI-powered responses for user queries"""
        system_prompt = """You are a helpful assistant for a gaming community platform.
        Provide accurate, helpful responses about gaming, server management, and community guidelines.
        Keep responses concise and friendly."""

        try:
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            if context:
                messages.append({"role": "user", "content": f"Context: {context}"})

            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return "I'm sorry, I'm having trouble generating a response right now."

    async def analyze_sentiment(self, text: str) -> Dict[str, any]:
        """Analyze sentiment of user feedback and forum posts"""
        try:
            prompt = f"""Analyze the sentiment of this text and provide:
1. Overall sentiment (positive, negative, neutral)
2. Confidence score (0-1)
3. Key emotions detected
4. Brief explanation

Text: {text}"""

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )

            return {
                'analysis': response.choices[0].message.content.strip(),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {'error': str(e)}

    async def suggest_tags(self, content: str) -> List[str]:
        """Suggest relevant tags for forum posts"""
        try:
            prompt = f"""Based on this forum post content, suggest 3-5 relevant tags.
            Return only the tags as a comma-separated list.

Content: {content}"""

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.5
            )

            tags_str = response.choices[0].message.content.strip()
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            return tags[:5]  # Limit to 5 tags
        except Exception as e:
            logger.error(f"Tag suggestion failed: {e}")
            return []

    async def detect_language(self, text: str) -> str:
        """Detect the language of user input"""
        try:
            prompt = f"""Detect the primary language of this text.
            Return only the language name (e.g., English, Spanish, French).

Text: {text}"""

            response = await self.client.chat.completions.create(
                model=self.deployment_gpt35,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.1
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "unknown"

# Global AI client instance
ai_client = None

def init_ai_client():
    """Initialize the AI client"""
    global ai_client
    if os.getenv('AZURE_OPENAI_API_KEY'):
        ai_client = AzureOpenAIClient()
    else:
        logger.warning("Azure OpenAI not configured")

def get_ai_client() -> Optional[AzureOpenAIClient]:
    """Get the AI client instance"""
    return ai_client
```

### AI Integration in Application

```python
# Integrate AI features into the application
from src.panel.ai_integration import init_ai_client, get_ai_client

# Initialize AI client
init_ai_client()

# Example usage in forum post creation
@app.route('/api/forum/posts', methods=['POST'])
@login_required
def create_forum_post():
    data = request.get_json()
    content = data.get('content', '')

    # AI-powered content moderation
    ai_client = get_ai_client()
    if ai_client:
        moderation = await ai_client.moderate_content(content)
        if moderation.get('flagged'):
            return jsonify({'error': 'Content flagged by moderation'}), 400

        # Suggest tags
        suggested_tags = await ai_client.suggest_tags(content)
        data['suggested_tags'] = suggested_tags

    # Create post...
    return jsonify({'success': True, 'post': post_data})
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
az acr build --registry panelacr --image panel:latest --file Dockerfile.azure .
```

### 3. DNS Configuration

```bash
# Add custom domain to Front Door
az network front-door frontend-endpoint create \
  --resource-group panel-rg \
  --front-door-name panel-cdn \
  --name custom-domain \
  --host-name yourdomain.com
```

## Cost Optimization

### Azure Cost Management

```hcl
# budgets.tf
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
```

### Scaling Configuration

```hcl
# Scale to zero when not in use
resource "azurerm_container_app" "panel" {
  # ... existing config ...

  template {
    # ... existing config ...
    min_replicas = 0  # Scale to zero
    max_replicas = 10
  }
}
```

## Security Configuration

### Azure Security Center

```hcl
# security.tf
resource "azurerm_security_center_subscription_pricing" "panel" {
  tier = "Standard"
}

resource "azurerm_security_center_setting" "panel" {
  setting_name = "MCAS"
  enabled      = true
}
```

### Network Security

```hcl
# NSG for additional security
resource "azurerm_network_security_group" "panel" {
  name                = "panel-nsg"
  location            = azurerm_resource_group.panel.location
  resource_group_name = azurerm_resource_group.panel.name

  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
```

This Azure deployment provides a production-ready, scalable, and secure infrastructure for the Panel application with integrated AI capabilities using Azure OpenAI Service.