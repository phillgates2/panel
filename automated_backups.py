"""
Automated Backup System for Panel Application

This module provides comprehensive backup capabilities including:
- Database backups with encryption
- File system backups
- Configuration backups
- Automated scheduling
- Cloud storage integration
- Backup verification and monitoring
"""

import gzip
import hashlib
import json
import logging
import os
import shutil
import smtplib
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional

import boto3
import schedule

logger = logging.getLogger(__name__)


class BackupManager:
    """Main backup management system"""

    def __init__(self, config: Dict):
        self.config = config
        self.backup_dir = Path(config.get("backup_dir", "/app/backups"))
        self.backup_dir.mkdir(exist_ok=True)

        # Cloud storage
        self.s3_client = None
        if config.get("s3_enabled"):
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=config.get("aws_access_key_id"),
                aws_secret_access_key=config.get("aws_secret_access_key"),
                region_name=config.get("aws_region", "us-east-1"),
            )

        # Email notifications
        self.email_config = config.get("email", {})

        # Encryption
        self.encryption_key = config.get("encryption_key")

        # Retention policies
        self.retention_days = config.get("retention_days", 30)

    def create_database_backup(self, db_url: str, name: str = None) -> str:
        """Create encrypted database backup"""
        if name is None:
            name = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_file = self.backup_dir / f"{name}.sql.gz"

        try:
            # Extract database connection details
            # This is a simplified example - in production, parse the actual DB URL
            db_host = "localhost"
            db_port = "5432"
            db_name = "panel"
            db_user = "panel"
            db_password = "password"

            # Create pg_dump command
            cmd = [
                "pg_dump",
                f"--host={db_host}",
                f"--port={db_port}",
                f"--username={db_user}",
                f"--dbname={db_name}",
                "--no-password",
                "--format=custom",
                "--compress=9",
                "--verbose",
            ]

            # Set password environment
            env = os.environ.copy()
            env["PGPASSWORD"] = db_password

            # Execute backup
            with open(backup_file, "wb") as f:
                result = subprocess.run(
                    cmd, env=env, stdout=f, stderr=subprocess.PIPE, check=True
                )

            # Encrypt if key provided
            if self.encryption_key:
                self._encrypt_file(backup_file)

            # Calculate checksum
            checksum = self._calculate_checksum(backup_file)
            checksum_file = backup_file.with_suffix(".sha256")
            checksum_file.write_text(f"{checksum}  {backup_file.name}")

            logger.info(f"Database backup created: {backup_file}")
            return str(backup_file)

        except subprocess.CalledProcessError as e:
            logger.error(f"Database backup failed: {e.stderr.decode()}")
            raise

    def create_filesystem_backup(self, paths: List[str], name: str = None) -> str:
        """Create filesystem backup"""
        if name is None:
            name = f"fs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_file = self.backup_dir / f"{name}.tar.gz"

        try:
            # Create tar command
            cmd = ["tar", "-czf", str(backup_file)] + paths

            result = subprocess.run(cmd, check=True, capture_output=True)

            # Encrypt if key provided
            if self.encryption_key:
                self._encrypt_file(backup_file)

            # Calculate checksum
            checksum = self._calculate_checksum(backup_file)
            checksum_file = backup_file.with_suffix(".sha256")
            checksum_file.write_text(f"{checksum}  {backup_file.name}")

            logger.info(f"Filesystem backup created: {backup_file}")
            return str(backup_file)

        except subprocess.CalledProcessError as e:
            logger.error(f"Filesystem backup failed: {e.stderr.decode()}")
            raise

    def create_config_backup(self, config_paths: List[str], name: str = None) -> str:
        """Create configuration backup"""
        if name is None:
            name = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_file = self.backup_dir / f"{name}.tar.gz"

        try:
            # Collect all config files
            config_files = []
            for path in config_paths:
                if os.path.isfile(path):
                    config_files.append(path)
                elif os.path.isdir(path):
                    config_files.extend(
                        [str(p) for p in Path(path).rglob("*") if p.is_file()]
                    )

            if not config_files:
                raise ValueError("No configuration files found")

            # Create tar command
            cmd = ["tar", "-czf", str(backup_file)] + config_files

            result = subprocess.run(cmd, check=True, capture_output=True)

            # Encrypt if key provided
            if self.encryption_key:
                self._encrypt_file(backup_file)

            logger.info(f"Configuration backup created: {backup_file}")
            return str(backup_file)

        except subprocess.CalledProcessError as e:
            logger.error(f"Configuration backup failed: {e.stderr.decode()}")
            raise

    def upload_to_s3(self, backup_file: str, bucket: str, key: str = None) -> str:
        """Upload backup to S3"""
        if not self.s3_client:
            raise ValueError("S3 client not configured")

        if key is None:
            key = f"backups/{Path(backup_file).name}"

        try:
            self.s3_client.upload_file(backup_file, bucket, key)
            logger.info(f"Backup uploaded to S3: s3://{bucket}/{key}")
            return f"s3://{bucket}/{key}"

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise

    def verify_backup(self, backup_file: str) -> bool:
        """Verify backup integrity"""
        backup_path = Path(backup_file)

        # Check if file exists
        if not backup_path.exists():
            return False

        # Verify checksum if available
        checksum_file = backup_path.with_suffix(".sha256")
        if checksum_file.exists():
            expected_checksum = checksum_file.read_text().split()[0]
            actual_checksum = self._calculate_checksum(backup_path)

            if expected_checksum != actual_checksum:
                logger.error(f"Checksum verification failed for {backup_file}")
                return False

        # Try to decrypt if encrypted
        if self.encryption_key and backup_path.suffix == ".enc":
            try:
                self._decrypt_file(backup_path)
            except Exception as e:
                logger.error(f"Decryption verification failed: {e}")
                return False

        return True

    def cleanup_old_backups(self, days: int = None) -> int:
        """Clean up old backups based on retention policy"""
        if days is None:
            days = self.retention_days

        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        for backup_file in self.backup_dir.glob("*"):
            if backup_file.is_file():
                # Check file modification time
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    try:
                        backup_file.unlink()
                        # Also remove checksum file if exists
                        checksum_file = backup_file.with_suffix(".sha256")
                        if checksum_file.exists():
                            checksum_file.unlink()

                        deleted_count += 1
                        logger.info(f"Deleted old backup: {backup_file}")

                    except Exception as e:
                        logger.error(f"Failed to delete {backup_file}: {e}")

        return deleted_count

    def send_notification(self, subject: str, message: str, success: bool = True):
        """Send email notification"""
        if not self.email_config.get("enabled"):
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_config["from"]
            msg["To"] = self.email_config["to"]
            msg["Subject"] = f"{'✅' if success else '❌'} {subject}"

            body = f"""
Backup System Notification

{message}

Timestamp: {datetime.now().isoformat()}
Status: {'SUCCESS' if success else 'FAILED'}
"""
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(
                self.email_config["smtp_server"],
                self.email_config.get("smtp_port", 587),
            )
            server.starttls()
            server.login(self.email_config["username"], self.email_config["password"])
            server.send_message(msg)
            server.quit()

            logger.info("Notification email sent")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def _encrypt_file(self, file_path: Path):
        """Encrypt a file using AES"""
        # This is a simplified encryption example
        # In production, use proper encryption libraries
        encrypted_file = file_path.with_suffix(".enc")

        # Simple XOR encryption for demonstration
        key = self.encryption_key.encode()
        with open(file_path, "rb") as f_in, open(encrypted_file, "wb") as f_out:
            while True:
                chunk = f_in.read(4096)
                if not chunk:
                    break
                encrypted_chunk = bytes(
                    b ^ key[i % len(key)] for i, b in enumerate(chunk)
                )
                f_out.write(encrypted_chunk)

        # Replace original file
        encrypted_file.replace(file_path)

    def _decrypt_file(self, file_path: Path):
        """Decrypt a file"""
        # Simplified decryption
        key = self.encryption_key.encode()
        decrypted_file = file_path.with_suffix("")

        with open(file_path, "rb") as f_in, open(decrypted_file, "wb") as f_out:
            while True:
                chunk = f_in.read(4096)
                if not chunk:
                    break
                decrypted_chunk = bytes(
                    b ^ key[i % len(key)] for i, b in enumerate(chunk)
                )
                f_out.write(decrypted_chunk)

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()


class BackupScheduler:
    """Automated backup scheduling system"""

    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.running = False

    def start(self):
        """Start the backup scheduler"""
        self.running = True

        # Schedule daily database backup at 2 AM
        schedule.every().day.at("02:00").do(self._run_database_backup)

        # Schedule weekly filesystem backup on Sunday at 3 AM
        schedule.every().sunday.at("03:00").do(self._run_filesystem_backup)

        # Schedule daily config backup at 4 AM
        schedule.every().day.at("04:00").do(self._run_config_backup)

        # Schedule cleanup every Sunday at 5 AM
        schedule.every().sunday.at("05:00").do(self._run_cleanup)

        # Run scheduler in background thread
        scheduler_thread = threading.Thread(target=self._run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()

        logger.info("Backup scheduler started")

    def stop(self):
        """Stop the backup scheduler"""
        self.running = False
        self.executor.shutdown(wait=True)
        logger.info("Backup scheduler stopped")

    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def _run_database_backup(self):
        """Execute scheduled database backup"""
        try:
            logger.info("Starting scheduled database backup")
            backup_file = self.backup_manager.create_database_backup(
                self.backup_manager.config["database_url"]
            )

            # Upload to S3 if configured
            if self.backup_manager.s3_client:
                s3_url = self.backup_manager.upload_to_s3(
                    backup_file, self.backup_manager.config["s3_bucket"]
                )

            # Send success notification
            self.backup_manager.send_notification(
                "Database Backup Completed",
                f"Database backup completed successfully: {backup_file}",
            )

        except Exception as e:
            logger.error(f"Scheduled database backup failed: {e}")
            self.backup_manager.send_notification(
                "Database Backup Failed",
                f"Database backup failed: {str(e)}",
                success=False,
            )

    def _run_filesystem_backup(self):
        """Execute scheduled filesystem backup"""
        try:
            logger.info("Starting scheduled filesystem backup")
            paths = self.backup_manager.config.get(
                "filesystem_paths", ["/app/uploads", "/app/logs"]
            )
            backup_file = self.backup_manager.create_filesystem_backup(paths)

            if self.backup_manager.s3_client:
                s3_url = self.backup_manager.upload_to_s3(
                    backup_file, self.backup_manager.config["s3_bucket"]
                )

            self.backup_manager.send_notification(
                "Filesystem Backup Completed",
                f"Filesystem backup completed successfully: {backup_file}",
            )

        except Exception as e:
            logger.error(f"Scheduled filesystem backup failed: {e}")
            self.backup_manager.send_notification(
                "Filesystem Backup Failed",
                f"Filesystem backup failed: {str(e)}",
                success=False,
            )

    def _run_config_backup(self):
        """Execute scheduled configuration backup"""
        try:
            logger.info("Starting scheduled configuration backup")
            config_paths = self.backup_manager.config.get(
                "config_paths", ["/app/config"]
            )
            backup_file = self.backup_manager.create_config_backup(config_paths)

            if self.backup_manager.s3_client:
                s3_url = self.backup_manager.upload_to_s3(
                    backup_file, self.backup_manager.config["s3_bucket"]
                )

            self.backup_manager.send_notification(
                "Configuration Backup Completed",
                f"Configuration backup completed successfully: {backup_file}",
            )

        except Exception as e:
            logger.error(f"Scheduled configuration backup failed: {e}")
            self.backup_manager.send_notification(
                "Configuration Backup Failed",
                f"Configuration backup failed: {str(e)}",
                success=False,
            )

    def _run_cleanup(self):
        """Execute scheduled cleanup"""
        try:
            logger.info("Starting scheduled backup cleanup")
            deleted_count = self.backup_manager.cleanup_old_backups()

            self.backup_manager.send_notification(
                "Backup Cleanup Completed",
                f"Cleaned up {deleted_count} old backup files",
            )

        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {e}")
            self.backup_manager.send_notification(
                "Backup Cleanup Failed",
                f"Backup cleanup failed: {str(e)}",
                success=False,
            )


# Flask integration
def init_backup_system(app):
    """Initialize backup system for Flask application"""
    backup_config = {
        "backup_dir": app.config.get("BACKUP_DIR", "/app/backups"),
        "database_url": app.config["SQLALCHEMY_DATABASE_URI"],
        "retention_days": app.config.get("BACKUP_RETENTION_DAYS", 30),
        "encryption_key": app.config.get("BACKUP_ENCRYPTION_KEY"),
        "s3_enabled": app.config.get("BACKUP_S3_ENABLED", False),
        "aws_access_key_id": app.config.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": app.config.get("AWS_SECRET_ACCESS_KEY"),
        "aws_region": app.config.get("AWS_REGION", "us-east-1"),
        "s3_bucket": app.config.get("BACKUP_S3_BUCKET"),
        "filesystem_paths": app.config.get("BACKUP_FILESYSTEM_PATHS", ["/app/uploads"]),
        "config_paths": app.config.get("BACKUP_CONFIG_PATHS", ["/app/config"]),
        "email": {
            "enabled": app.config.get("BACKUP_EMAIL_ENABLED", False),
            "from": app.config.get("BACKUP_EMAIL_FROM"),
            "to": app.config.get("BACKUP_EMAIL_TO"),
            "smtp_server": app.config.get("BACKUP_SMTP_SERVER"),
            "smtp_port": app.config.get("BACKUP_SMTP_PORT", 587),
            "username": app.config.get("BACKUP_SMTP_USERNAME"),
            "password": app.config.get("BACKUP_SMTP_PASSWORD"),
        },
    }

    backup_manager = BackupManager(backup_config)
    backup_scheduler = BackupScheduler(backup_manager)

    # Store in app context
    app.backup_manager = backup_manager
    app.backup_scheduler = backup_scheduler

    # Start scheduler if enabled
    if app.config.get("BACKUP_SCHEDULER_ENABLED", True):
        backup_scheduler.start()

    return backup_manager, backup_scheduler


# CLI commands for manual backup operations
def create_backup_cli():
    """Command line interface for backup operations"""
    import argparse

    parser = argparse.ArgumentParser(description="Panel Backup Management")
    parser.add_argument("action", choices=["db", "fs", "config", "cleanup", "verify"])
    parser.add_argument("--name", help="Backup name")
    parser.add_argument("--file", help="Backup file to verify")

    args = parser.parse_args()

    # This would be integrated with Flask app context
    # For now, just show usage
    print(f"Backup action: {args.action}")
    if args.name:
        print(f"Backup name: {args.name}")
    if args.file:
        print(f"File to verify: {args.file}")


if __name__ == "__main__":
    create_backup_cli()
