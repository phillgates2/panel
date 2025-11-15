#!/usr/bin/env python3
"""
Database Backup & Recovery Manager

Provides comprehensive backup and recovery capabilities for the panel database
including automated backups, encryption, compression, and cloud storage integration.
"""

import os
import sys
import json
import gzip
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
import boto3
from botocore.exceptions import ClientError

# Add app path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class BackupManager:
    """Manages database backups with encryption and cloud storage."""
    
    def __init__(self, config_file='/etc/panel/backup_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self):
        """Load backup configuration."""
        default_config = {
            "database": {
                "host": "localhost",
                "user": "paneluser",
                "password": "panelpass", 
                "name": "paneldb",
                "port": 3306
            },
            "backup": {
                "directory": "/var/backups/panel",
                "retention_days": 30,
                "compress": True,
                "encrypt": True,
                "encryption_key_file": "/etc/panel/backup.key"
            },
            "cloud": {
                "enabled": False,
                "provider": "s3",
                "bucket": "panel-backups",
                "region": "us-east-1",
                "access_key_id": "",
                "secret_access_key": "",
                "retention_days": 90
            },
            "schedule": {
                "full_backup_hour": 2,
                "incremental_interval_hours": 4,
                "enabled": True
            },
            "notifications": {
                "discord_webhook": "",
                "email_enabled": False,
                "smtp_server": "localhost",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": "",
                "recipients": []
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                return self._deep_merge(default_config, config)
            except Exception as e:
                print(f"Warning: Failed to load config, using defaults: {e}")
                
        # Create default config
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
            
        return default_config
    
    def _deep_merge(self, base, update):
        """Deep merge two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def generate_encryption_key(self):
        """Generate a new encryption key."""
        key = Fernet.generate_key()
        key_file = self.config['backup']['encryption_key_file']
        
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
        
        # Secure permissions
        os.chmod(key_file, 0o600)
        print(f"Encryption key generated and saved to {key_file}")
        return key
    
    def get_encryption_key(self):
        """Get the encryption key."""
        key_file = self.config['backup']['encryption_key_file']
        
        if not os.path.exists(key_file):
            return self.generate_encryption_key()
            
        with open(key_file, 'rb') as f:
            return f.read()
    
    def create_backup(self, backup_type='full'):
        """Create a database backup."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = Path(self.config['backup']['directory'])
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate backup filename
        backup_name = f"panel_backup_{backup_type}_{timestamp}.sql"
        backup_path = backup_dir / backup_name
        
        print(f"Creating {backup_type} backup: {backup_name}")
        
        try:
            # Create MariaDB dump
            self._create_mariadb_dump(backup_path, backup_type)
            
            # Compress if enabled
            if self.config['backup']['compress']:
                backup_path = self._compress_backup(backup_path)
            
            # Encrypt if enabled
            if self.config['backup']['encrypt']:
                backup_path = self._encrypt_backup(backup_path)
            
            # Upload to cloud if enabled
            if self.config['cloud']['enabled']:
                self._upload_to_cloud(backup_path)
            
            # Update backup registry
            self._update_backup_registry(backup_path, backup_type)
            
            print(f"Backup completed successfully: {backup_path}")
            
            # Send notification
            self._send_notification('success', f"Backup {backup_name} completed successfully")
            
            return backup_path
            
        except Exception as e:
            error_msg = f"Backup failed: {str(e)}"
            print(error_msg)
            self._send_notification('error', error_msg)
            raise
    
    def _create_mariadb_dump(self, backup_path, backup_type):
        """Create MariaDB database dump."""
        db_config = self.config['database']
        
        cmd = [
            'mysqldump',
            f'--host={db_config["host"]}',
            f'--port={db_config["port"]}',
            f'--user={db_config["user"]}',
            f'--password={db_config["password"]}',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--add-drop-table',
            '--disable-keys',
            '--extended-insert'
        ]
        
        # Add incremental backup options
        if backup_type == 'incremental':
            cmd.extend(['--flush-logs', '--master-data=2'])
            
        cmd.append(db_config['name'])
        
        # Execute mysqldump (works with MariaDB)
        with open(backup_path, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
        if result.returncode != 0:
            raise Exception(f"mysqldump failed: {result.stderr}")
    
    def _compress_backup(self, backup_path):
        """Compress backup file using gzip."""
        compressed_path = Path(str(backup_path) + '.gz')
        
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed file
        backup_path.unlink()
        
        return compressed_path
    
    def _encrypt_backup(self, backup_path):
        """Encrypt backup file."""
        encrypted_path = Path(str(backup_path) + '.enc')
        
        # Get encryption key
        key = self.get_encryption_key()
        fernet = Fernet(key)
        
        # Encrypt file
        with open(backup_path, 'rb') as f_in:
            data = f_in.read()
            encrypted_data = fernet.encrypt(data)
            
        with open(encrypted_path, 'wb') as f_out:
            f_out.write(encrypted_data)
        
        # Remove unencrypted file
        backup_path.unlink()
        
        return encrypted_path
    
    def _upload_to_cloud(self, backup_path):
        """Upload backup to cloud storage."""
        cloud_config = self.config['cloud']
        
        if cloud_config['provider'] == 's3':
            self._upload_to_s3(backup_path)
        else:
            raise Exception(f"Unsupported cloud provider: {cloud_config['provider']}")
    
    def _upload_to_s3(self, backup_path):
        """Upload backup to Amazon S3."""
        cloud_config = self.config['cloud']
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name=cloud_config['region'],
            aws_access_key_id=cloud_config['access_key_id'],
            aws_secret_access_key=cloud_config['secret_access_key']
        )
        
        # Upload file
        s3_key = f"panel_backups/{backup_path.name}"
        
        try:
            s3_client.upload_file(str(backup_path), cloud_config['bucket'], s3_key)
            print(f"Backup uploaded to S3: s3://{cloud_config['bucket']}/{s3_key}")
        except ClientError as e:
            raise Exception(f"S3 upload failed: {e}")
    
    def _update_backup_registry(self, backup_path, backup_type):
        """Update backup registry with new backup info."""
        registry_file = Path(self.config['backup']['directory']) / 'backup_registry.json'
        
        # Load existing registry
        registry = []
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                registry = json.load(f)
        
        # Add new backup
        backup_info = {
            'filename': backup_path.name,
            'path': str(backup_path),
            'type': backup_type,
            'timestamp': datetime.now().isoformat(),
            'size': backup_path.stat().st_size,
            'compressed': self.config['backup']['compress'],
            'encrypted': self.config['backup']['encrypt'],
            'cloud_uploaded': self.config['cloud']['enabled']
        }
        
        registry.append(backup_info)
        
        # Save registry
        with open(registry_file, 'w') as f:
            json.dump(registry, f, indent=2)
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy."""
        backup_dir = Path(self.config['backup']['directory'])
        retention_days = self.config['backup']['retention_days']
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        removed_count = 0
        
        for backup_file in backup_dir.glob('panel_backup_*'):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                print(f"Removing old backup: {backup_file}")
                backup_file.unlink()
                removed_count += 1
        
        print(f"Cleanup completed. Removed {removed_count} old backups.")
        
        # Cleanup cloud backups
        if self.config['cloud']['enabled']:
            self._cleanup_cloud_backups()
    
    def _cleanup_cloud_backups(self):
        """Remove old backups from cloud storage."""
        # Implementation for cloud cleanup
        pass
    
    def restore_backup(self, backup_file, target_database=None):
        """Restore database from backup."""
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            raise Exception(f"Backup file not found: {backup_file}")
        
        print(f"Restoring backup: {backup_path}")
        
        # Determine file type and process accordingly
        processed_file = backup_path
        
        # Decrypt if needed
        if backup_path.suffix == '.enc':
            processed_file = self._decrypt_backup(backup_path)
        
        # Decompress if needed
        if processed_file.suffix == '.gz':
            processed_file = self._decompress_backup(processed_file)
        
        # Restore database
        db_config = self.config['database']
        target_db = target_database or db_config['name']
        
        cmd = [
            'mysql',
            f'--host={db_config["host"]}',
            f'--port={db_config["port"]}',
            f'--user={db_config["user"]}',
            f'--password={db_config["password"]}',
            target_db
        ]
        
        with open(processed_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Database restore failed: {result.stderr}")
        
        print(f"Database restored successfully to {target_db}")
        
        # Cleanup temporary files
        if processed_file != backup_path:
            processed_file.unlink()
    
    def _decrypt_backup(self, encrypted_file):
        """Decrypt backup file."""
        decrypted_file = Path(str(encrypted_file).replace('.enc', ''))
        
        key = self.get_encryption_key()
        fernet = Fernet(key)
        
        with open(encrypted_file, 'rb') as f_in:
            encrypted_data = f_in.read()
            decrypted_data = fernet.decrypt(encrypted_data)
        
        with open(decrypted_file, 'wb') as f_out:
            f_out.write(decrypted_data)
        
        return decrypted_file
    
    def _decompress_backup(self, compressed_file):
        """Decompress backup file."""
        decompressed_file = Path(str(compressed_file).replace('.gz', ''))
        
        with gzip.open(compressed_file, 'rb') as f_in:
            with open(decompressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return decompressed_file
    
    def list_backups(self):
        """List available backups."""
        registry_file = Path(self.config['backup']['directory']) / 'backup_registry.json'
        
        if not registry_file.exists():
            return []
        
        with open(registry_file, 'r') as f:
            return json.load(f)
    
    def _send_notification(self, status, message):
        """Send backup notification."""
        # Discord webhook notification
        if self.config['notifications']['discord_webhook']:
            self._send_discord_notification(status, message)
        
        # Email notification
        if self.config['notifications']['email_enabled']:
            self._send_email_notification(status, message)
    
    def _send_discord_notification(self, status, message):
        """Send Discord notification."""
        import requests
        
        color = 0x00ff00 if status == 'success' else 0xff0000
        
        payload = {
            "embeds": [{
                "title": "Panel Database Backup",
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
        
        try:
            requests.post(self.config['notifications']['discord_webhook'], json=payload)
        except Exception as e:
            print(f"Discord notification failed: {e}")
    
    def _send_email_notification(self, status, message):
        """Send email notification."""
        # Email implementation
        pass

def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Panel Database Backup Manager')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'cleanup', 'generate-key'],
                       help='Action to perform')
    parser.add_argument('--type', choices=['full', 'incremental'], default='full',
                       help='Backup type (default: full)')
    parser.add_argument('--file', help='Backup file path (for restore)')
    parser.add_argument('--database', help='Target database name (for restore)')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Initialize backup manager
    config_file = args.config if args.config else '/etc/panel/backup_config.json'
    manager = BackupManager(config_file)
    
    try:
        if args.action == 'backup':
            manager.create_backup(args.type)
        elif args.action == 'restore':
            if not args.file:
                print("Error: --file required for restore")
                sys.exit(1)
            manager.restore_backup(args.file, args.database)
        elif args.action == 'list':
            backups = manager.list_backups()
            if backups:
                print("Available backups:")
                for backup in backups:
                    print(f"  {backup['filename']} ({backup['type']}) - {backup['timestamp']}")
            else:
                print("No backups found")
        elif args.action == 'cleanup':
            manager.cleanup_old_backups()
        elif args.action == 'generate-key':
            manager.generate_encryption_key()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()