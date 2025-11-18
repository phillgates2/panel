#!/usr/bin/env python3
"""
SSL Certificate Auto-Renewal Script

This script handles automatic SSL certificate renewal using certbot and includes
zero-downtime deployment for web services.
"""

import json
import logging
import os
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Try to import OS-aware paths
try:
    from os_paths import os_paths

    DEFAULT_LOG_FILE = os.path.join(os_paths.log_dir, "ssl_renewal.log")
    DEFAULT_CONFIG_FILE = os.path.join(os_paths.config_dir, "ssl_config.json")
    DEFAULT_WEBROOT = "/var/www/html"  # This is typically standard across systems
    DEFAULT_NGINX_CONFIG = os_paths.nginx_config_dir
except ImportError:
    # Fallback to Linux defaults if os_paths not available
    DEFAULT_LOG_FILE = "/var/log/ssl_renewal.log"
    DEFAULT_CONFIG_FILE = "/etc/panel/ssl_config.json"
    DEFAULT_WEBROOT = "/var/www/html"
    DEFAULT_NGINX_CONFIG = "/etc/nginx/sites-available"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(DEFAULT_LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class SSLRenewalManager:
    """Manages SSL certificate renewal and deployment"""

    def __init__(self, config_file=None):
        self.config_file = config_file if config_file else DEFAULT_CONFIG_FILE
        self.config = self.load_config()

    def load_config(self):
        """Load SSL renewal configuration"""
        default_config = {
            "domains": [],
            "email": "admin@example.com",
            "webroot_path": DEFAULT_WEBROOT,
            "nginx_config_path": os.path.join(DEFAULT_NGINX_CONFIG, "panel"),
            "services_to_reload": ["nginx", "panel-gunicorn"],
            "days_before_expiry": 30,
            "test_mode": False,
            "notification": {
                "enabled": False,
                "smtp_server": "localhost",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": "",
                "recipients": [],
            },
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}, using defaults")
                return default_config
        else:
            # Create default config file
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default config at {self.config_file}")
            return default_config

    def check_certificate_expiry(self, domain):
        """Check when a certificate expires"""
        try:
            cmd = [
                "openssl",
                "x509",
                "-noout",
                "-dates",
                "-in",
                f"/etc/letsencrypt/live/{domain}/cert.pem",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.warning(
                    f"Could not check certificate for {domain}: {result.stderr}"
                )
                return None

            # Parse the expiry date
            for line in result.stdout.split("\n"):
                if line.startswith("notAfter="):
                    expiry_str = line.replace("notAfter=", "")
                    expiry_date = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                    return expiry_date

            return None
        except Exception as e:
            logger.error(f"Error checking certificate expiry for {domain}: {e}")
            return None

    def needs_renewal(self, domain):
        """Check if certificate needs renewal"""
        expiry_date = self.check_certificate_expiry(domain)
        if not expiry_date:
            return True  # Assume needs renewal if we can't check

        days_until_expiry = (expiry_date - datetime.now()).days
        return days_until_expiry <= self.config["days_before_expiry"]

    def run_certbot(self, domain):
        """Run certbot to renew certificate"""
        logger.info(f"Attempting to renew certificate for {domain}")

        cmd = [
            "certbot",
            "certonly",
            "--webroot",
            "-w",
            self.config["webroot_path"],
            "-d",
            domain,
            "--email",
            self.config["email"],
            "--agree-tos",
            "--non-interactive",
        ]

        if self.config["test_mode"]:
            cmd.append("--staging")
            logger.info("Running in test mode (staging environment)")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Successfully renewed certificate for {domain}")
                return True
            else:
                logger.error(
                    f"Failed to renew certificate for {domain}: {result.stderr}"
                )
                return False

        except Exception as e:
            logger.error(f"Error running certbot for {domain}: {e}")
            return False

    def reload_services(self):
        """Reload web services after certificate renewal"""
        logger.info("Reloading services after certificate renewal")

        for service in self.config["services_to_reload"]:
            try:
                cmd = ["systemctl", "reload", service]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"Successfully reloaded {service}")
                else:
                    logger.error(f"Failed to reload {service}: {result.stderr}")

            except Exception as e:
                logger.error(f"Error reloading {service}: {e}")

    def send_notification(self, subject, message):
        """Send email notification"""
        if not self.config["notification"]["enabled"]:
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = self.config["notification"]["smtp_user"]
            msg["Subject"] = subject

            msg.attach(MIMEText(message, "plain"))

            server = smtplib.SMTP(
                self.config["notification"]["smtp_server"],
                self.config["notification"]["smtp_port"],
            )
            server.starttls()
            server.login(
                self.config["notification"]["smtp_user"],
                self.config["notification"]["smtp_password"],
            )

            for recipient in self.config["notification"]["recipients"]:
                msg["To"] = recipient
                server.sendmail(
                    self.config["notification"]["smtp_user"], recipient, msg.as_string()
                )

            server.quit()
            logger.info("Notification email sent successfully")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def run_renewal_check(self):
        """Main renewal check and execution"""
        logger.info("Starting SSL certificate renewal check")

        if not self.config["domains"]:
            logger.warning("No domains configured for SSL renewal")
            return False

        renewed_domains = []
        failed_domains = []

        for domain in self.config["domains"]:
            logger.info(f"Checking certificate for {domain}")

            if self.needs_renewal(domain):
                logger.info(f"Certificate for {domain} needs renewal")

                if self.run_certbot(domain):
                    renewed_domains.append(domain)
                else:
                    failed_domains.append(domain)
            else:
                logger.info(f"Certificate for {domain} is still valid")

        # Reload services if any certificates were renewed
        if renewed_domains:
            self.reload_services()

            # Send success notification
            subject = f"SSL certificates renewed for {len(renewed_domains)} domains"
            message = f"""
SSL Certificate Renewal Report

Successfully renewed certificates for:
{chr(10).join(f'- {domain}' for domain in renewed_domains)}

Renewal completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Services reloaded: {', '.join(self.config['services_to_reload'])}
"""
            self.send_notification(subject, message)

        # Send failure notification if any failed
        if failed_domains:
            subject = (
                f"SSL certificate renewal failed for {len(failed_domains)} domains"
            )
            message = f"""
SSL Certificate Renewal Failure Report

Failed to renew certificates for:
{chr(10).join(f'- {domain}' for domain in failed_domains)}

Please check the logs for more details.
Failure occurred at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            self.send_notification(subject, message)

        logger.info(
            f"SSL renewal check completed. Renewed: {len(renewed_domains)}, Failed: {len(failed_domains)}"
        )
        return len(failed_domains) == 0


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="SSL Certificate Auto-Renewal")
    parser.add_argument(
        "--config",
        default="/etc/panel/ssl_config.json",
        help="Path to SSL configuration file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check what would be renewed without actually doing it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force renewal even if certificate is not expiring soon",
    )

    args = parser.parse_args()

    try:
        manager = SSLRenewalManager(args.config)

        if args.dry_run:
            logger.info("Running in dry-run mode")
            for domain in manager.config["domains"]:
                expiry = manager.check_certificate_expiry(domain)
                if expiry:
                    days_left = (expiry - datetime.now()).days
                    status = (
                        "NEEDS RENEWAL"
                        if days_left <= manager.config["days_before_expiry"]
                        else "OK"
                    )
                    logger.info(f"{domain}: expires in {days_left} days ({status})")
                else:
                    logger.info(f"{domain}: certificate not found or error checking")
        else:
            success = manager.run_renewal_check()
            sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"SSL renewal failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
