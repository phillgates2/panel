# Production environment variables for GCP
project_id     = "your-gcp-project-id"  # Replace with your GCP project ID
region         = "us-central1"
environment    = "production"
domain_name    = "yourdomain.com"  # Replace with your actual domain
billing_account = "your-billing-account-id"  # Replace with your billing account ID

# Generate secure passwords/keys
# You can use: openssl rand -base64 32
db_password    = "your-secure-db-password-here"
secret_key     = "your-super-secret-flask-key-here"