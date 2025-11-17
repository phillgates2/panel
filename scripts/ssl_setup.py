#!/usr/bin/env python3
"""
SSL Certificate Setup Script

This script helps set up SSL certificates for the panel using Let's Encrypt.
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SSLSetup:
    """Handles initial SSL certificate setup"""
    
    def __init__(self):
        self.config_dir = '/etc/panel'
        self.config_file = f'{self.config_dir}/ssl_config.json'
        self.webroot_path = '/var/www/html'
        
    def check_prerequisites(self):
        """Check if required tools are installed"""
        required_tools = ['certbot', 'nginx', 'systemctl']
        missing_tools = []
        
        for tool in required_tools:
            try:
                subprocess.run(['which', tool], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                missing_tools.append(tool)
        
        if missing_tools:
            logger.error(f"Missing required tools: {', '.join(missing_tools)}")
            logger.info("Please install missing tools:")
            logger.info("Ubuntu/Debian: sudo apt install certbot python3-certbot-nginx nginx")
            logger.info("CentOS/RHEL: sudo yum install certbot python3-certbot-nginx nginx")
            return False
        
        return True
    
    def create_webroot(self):
        """Create webroot directory for Let's Encrypt challenge"""
        webroot = Path(self.webroot_path)
        acme_challenge = webroot / '.well-known' / 'acme-challenge'
        
        try:
            acme_challenge.mkdir(parents=True, exist_ok=True)
            # Set proper permissions
            os.chmod(self.webroot_path, 0o755)
            os.chmod(webroot / '.well-known', 0o755)
            os.chmod(acme_challenge, 0o755)
            logger.info(f"Created webroot directory: {self.webroot_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create webroot directory: {e}")
            return False
    
    def configure_nginx_acme(self):
        """Configure nginx to serve ACME challenges"""
        acme_config = f"""
# ACME challenge location for Let's Encrypt
location /.well-known/acme-challenge/ {{
    root {self.webroot_path};
    try_files $uri =404;
}}
"""
        
        nginx_config_path = '/etc/nginx/sites-available/panel'
        
        # Check if nginx config exists
        if not os.path.exists(nginx_config_path):
            logger.warning(f"Nginx config not found at {nginx_config_path}")
            logger.info("Please ensure nginx is configured for the panel first")
            return False
        
        # Read existing config
        try:
            with open(nginx_config_path, 'r') as f:
                config_content = f.read()
            
            # Check if ACME configuration already exists
            if '.well-known/acme-challenge' in config_content:
                logger.info("ACME challenge configuration already exists in nginx")
                return True
            
            # Add ACME configuration to server block
            if 'location / {' in config_content:
                # Insert before the main location block
                config_content = config_content.replace(
                    'location / {',
                    acme_config + '\n    location / {'
                )
                
                with open(nginx_config_path, 'w') as f:
                    f.write(config_content)
                
                # Test nginx configuration
                result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                if result.returncode == 0:
                    # Reload nginx
                    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
                    logger.info("Updated nginx configuration for ACME challenges")
                    return True
                else:
                    logger.error(f"Nginx configuration test failed: {result.stderr}")
                    return False
            else:
                logger.error("Could not find location block in nginx config")
                return False
                
        except Exception as e:
            logger.error(f"Failed to configure nginx: {e}")
            return False
    
    def get_domain_input(self):
        """Get domain information from user"""
        domains = []
        email = ""
        
        print("\\nSSL Certificate Setup")
        print("=" * 50)
        
        # Get email
        while not email:
            email = input("Enter your email address for Let's Encrypt notifications: ").strip()
            if '@' not in email:
                print("Please enter a valid email address")
                email = ""
        
        # Get domains
        print("\\nEnter the domains you want SSL certificates for:")
        print("(Press Enter on an empty line when done)")
        
        while True:
            domain = input(f"Domain {len(domains) + 1}: ").strip()
            if not domain:
                break
            
            # Basic domain validation
            if '.' not in domain or ' ' in domain:
                print("Please enter a valid domain name")
                continue
            
            domains.append(domain)
        
        if not domains:
            logger.error("No domains entered")
            return None, None
        
        return domains, email
    
    def obtain_certificates(self, domains, email, staging=False):
        """Obtain SSL certificates using certbot"""
        logger.info(f"Obtaining SSL certificates for: {', '.join(domains)}")
        
        for domain in domains:
            cmd = [
                'certbot', 'certonly',
                '--webroot',
                '-w', self.webroot_path,
                '-d', domain,
                '--email', email,
                '--agree-tos',
                '--non-interactive'
            ]
            
            if staging:
                cmd.append('--staging')
                logger.info(f"Using staging environment for {domain}")
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"Successfully obtained certificate for {domain}")
                else:
                    logger.error(f"Failed to obtain certificate for {domain}: {result.stderr}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error obtaining certificate for {domain}: {e}")
                return False
        
        return True
    
    def save_config(self, domains, email):
        """Save SSL configuration"""
        config = {
            "domains": domains,
            "email": email,
            "webroot_path": self.webroot_path,
            "nginx_config_path": "/etc/nginx/sites-available/panel",
            "services_to_reload": ["nginx", "panel-gunicorn"],
            "days_before_expiry": 30,
            "test_mode": False,
            "notification": {
                "enabled": False,
                "smtp_server": "localhost",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": "",
                "recipients": [email]
            }
        }
        
        # Create config directory
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Save configuration
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved SSL configuration to {self.config_file}")
    
    def setup_auto_renewal(self):
        """Setup automatic SSL renewal using systemd timer"""
        service_file = '/etc/systemd/system/ssl-renewal.service'
        timer_file = '/etc/systemd/system/ssl-renewal.timer'
        
        # Copy service and timer files
        try:
            import shutil
            
            # Copy from deploy directory
            shutil.copy('deploy/ssl-renewal.service', service_file)
            shutil.copy('deploy/ssl-renewal.timer', timer_file)
            
            # Update service file with correct path
            with open(service_file, 'r') as f:
                content = f.read()
            
            content = content.replace(
                'ExecStart=/usr/bin/python3 /opt/panel/scripts/ssl_renew.py',
                f'ExecStart=/usr/bin/python3 {os.path.abspath("scripts/ssl_renew.py")}'
            )
            
            with open(service_file, 'w') as f:
                f.write(content)
            
            # Enable and start timer
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', 'enable', 'ssl-renewal.timer'], check=True)
            subprocess.run(['systemctl', 'start', 'ssl-renewal.timer'], check=True)
            
            logger.info("SSL auto-renewal timer configured and started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup auto-renewal: {e}")
            return False
    
    def run_setup(self, staging=False):
        """Run the complete SSL setup process"""
        logger.info("Starting SSL certificate setup")
        
        # Check prerequisites
        if not self.check_prerequisites():
            return False
        
        # Create webroot
        if not self.create_webroot():
            return False
        
        # Configure nginx for ACME challenges
        if not self.configure_nginx_acme():
            return False
        
        # Get domain information
        domains, email = self.get_domain_input()
        if not domains:
            return False
        
        # Obtain certificates
        if not self.obtain_certificates(domains, email, staging):
            return False
        
        # Save configuration
        self.save_config(domains, email)
        
        # Setup auto-renewal
        if not self.setup_auto_renewal():
            logger.warning("Auto-renewal setup failed, but certificates were obtained")
        
        logger.info("SSL setup completed successfully!")
        logger.info("\\nNext steps:")
        logger.info("1. Update your nginx configuration to use the SSL certificates")
        logger.info("2. Test your SSL configuration")
        logger.info("3. Configure SSL auto-renewal notifications if needed")
        
        return True

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SSL Certificate Setup')
    parser.add_argument(
        '--staging',
        action='store_true',
        help='Use Let\'s Encrypt staging environment (for testing)'
    )
    
    args = parser.parse_args()
    
    # Check if running as root
    if os.geteuid() != 0:
        logger.error("This script must be run as root")
        sys.exit(1)
    
    try:
        setup = SSLSetup()
        success = setup.run_setup(staging=args.staging)
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Setup failed with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()