# Production environment variables for Azure
location     = "East US"
environment  = "production"
domain_name  = "yourdomain.com"  # Replace with your actual domain
alert_email  = "admin@yourdomain.com"  # Replace with your alert email

# Generate secure passwords/keys
# You can use: openssl rand -base64 32
db_password  = "your-secure-db-password-here"
secret_key   = "your-super-secret-flask-key-here"