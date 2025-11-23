"""
Backup & Disaster Recovery Automation
Automated backup creation, management, and disaster recovery procedures
"""

import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import logging
import gzip
import tarfile
from dataclasses import dataclass, field
import threading
import schedule
from flask import Flask


@dataclass
class BackupConfig:
    """Configuration for backup operations"""
    enabled: bool = True
    schedule: str = "daily"  # daily, weekly, monthly
    retention_days: int = 30
    compression: str = "gzip"  # gzip, bz2, none
    encryption: bool = False
    storage_path: str = "backups"
    max_concurrent_backups: int = 2
    timeout_minutes: int = 60
    verify_backups: bool = True
    notification_enabled: bool = True


@dataclass
class BackupJob:
    """Represents a backup job"""
    id: str
    name: str
    type: str  # database, filesystem, application
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    size_bytes: int = 0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class BackupManager:
    """Manages backup and recovery operations"""

    def __init__(self, app: Flask, config: BackupConfig = None):
        self.app = app
        self.config = config or BackupConfig()
        self.backup_jobs: Dict[str, BackupJob] = {}
        self.logger = logging.getLogger(__name__)
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False

        # Create backup directory
        self.backup_dir = Path(self.config.storage_path)
        self.backup_dir.mkdir(exist_ok=True)

        # Initialize backup types
        self.backup_types = {
            'database': DatabaseBackup(self.app),
            'filesystem': FilesystemBackup(self.app),
            'application': ApplicationBackup(self.app),
            'configuration': ConfigurationBackup(self.app)
        }

    def start_scheduler(self):
        """Start the backup scheduler"""
        if self._running:
            return

        self._running = True
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        self.logger.info("Backup scheduler started")

    def stop_scheduler(self):
        """Stop the backup scheduler"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        self.logger.info("Backup scheduler stopped")

    def _run_scheduler(self):
        """Run the backup scheduler"""
        # Schedule based on configuration
        if self.config.schedule == "daily":
            schedule.every().day.at("02:00").do(self.run_scheduled_backup)
        elif self.config.schedule == "weekly":
            schedule.every().monday.at("02:00").do(self.run_scheduled_backup)
        elif self.config.schedule == "monthly":
            schedule.every(30).days.at("02:00").do(self.run_scheduled_backup)

        # Cleanup old backups daily
        schedule.every().day.at("03:00").do(self.cleanup_old_backups)

        while self._running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def run_scheduled_backup(self):
        """Run scheduled backup for all types"""
        self.logger.info("Starting scheduled backup")

        backup_types = ['database', 'filesystem', 'configuration']
        results = []

        for backup_type in backup_types:
            try:
                result = self.create_backup(backup_type, f"scheduled_{backup_type}")
                results.append(result)
            except Exception as e:
                self.logger.error(f"Scheduled backup failed for {backup_type}: {e}")
                results.append({
                    'type': backup_type,
                    'status': 'failed',
                    'error': str(e)
                })

        # Send notification if enabled
        if self.config.notification_enabled:
            self._send_backup_notification(results)

        self.logger.info("Scheduled backup completed")

    def create_backup(self, backup_type: str, name: str = None) -> Dict[str, Any]:
        """Create a backup of specified type"""
        if backup_type not in self.backup_types:
            raise ValueError(f"Unknown backup type: {backup_type}")

        job_id = f"{backup_type}_{int(time.time())}"
        if name:
            job_id = f"{name}_{job_id}"

        job = BackupJob(
            id=job_id,
            name=name or f"{backup_type}_backup",
            type=backup_type,
            status="running"
        )

        self.backup_jobs[job_id] = job

        try:
            backup_handler = self.backup_types[backup_type]
            result_path = backup_handler.create_backup(job_id)

            # Compress if configured
            if self.config.compression != "none":
                result_path = self._compress_backup(result_path, job_id)

            # Encrypt if configured
            if self.config.encryption:
                result_path = self._encrypt_backup(result_path, job_id)

            # Get file size
            job.size_bytes = result_path.stat().st_size
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.metadata = {
                'file_path': str(result_path),
                'compressed': self.config.compression != "none",
                'encrypted': self.config.encryption
            }

            self.logger.info(f"Backup completed: {job_id} ({job.size_bytes} bytes)")

            return {
                'job_id': job_id,
                'type': backup_type,
                'status': 'completed',
                'file_path': str(result_path),
                'size': job.size_bytes
            }

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            self.logger.error(f"Backup failed: {job_id} - {e}")

            raise

    def restore_backup(self, backup_type: str, backup_file: str) -> Dict[str, Any]:
        """Restore from a backup"""
        if backup_type not in self.backup_types:
            raise ValueError(f"Unknown backup type: {backup_type}")

        # Decrypt if needed
        if self.config.encryption and backup_file.endswith('.enc'):
            backup_file = self._decrypt_backup(backup_file)

        # Decompress if needed
        if self.config.compression != "none" and backup_file.endswith(f'.{self.config.compression}'):
            backup_file = self._decompress_backup(backup_file)

        backup_handler = self.backup_types[backup_type]
        result = backup_handler.restore_backup(backup_file)

        self.logger.info(f"Restore completed: {backup_type} from {backup_file}")

        return result

    def list_backups(self, backup_type: str = None) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []

        for job in self.backup_jobs.values():
            if backup_type and job.type != backup_type:
                continue

            backup_info = {
                'id': job.id,
                'name': job.name,
                'type': job.type,
                'status': job.status,
                'created_at': job.created_at.isoformat(),
                'size_bytes': job.size_bytes,
                'file_path': job.metadata.get('file_path')
            }

            if job.completed_at:
                backup_info['completed_at'] = job.completed_at.isoformat()

            if job.error_message:
                backup_info['error'] = job.error_message

            backups.append(backup_info)

        return sorted(backups, key=lambda x: x['created_at'], reverse=True)

    def cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.retention_days)

        removed_count = 0
        for job in list(self.backup_jobs.values()):
            if job.created_at < cutoff_date and job.status == "completed":
                # Remove backup file
                file_path = job.metadata.get('file_path')
                if file_path and Path(file_path).exists():
                    Path(file_path).unlink()
                    removed_count += 1

                # Remove from jobs
                del self.backup_jobs[job.id]

        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} old backups")

    def get_backup_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a backup job"""
        job = self.backup_jobs.get(job_id)
        if not job:
            return None

        return {
            'id': job.id,
            'name': job.name,
            'type': job.type,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'size_bytes': job.size_bytes,
            'error_message': job.error_message,
            'metadata': job.metadata
        }

    def _compress_backup(self, file_path: Path, job_id: str) -> Path:
        """Compress a backup file"""
        compressed_path = file_path.with_suffix(f"{file_path.suffix}.{self.config.compression}")

        if self.config.compression == "gzip":
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        elif self.config.compression == "bz2":
            import bz2
            with open(file_path, 'rb') as f_in:
                with bz2.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

        # Remove original file
        file_path.unlink()

        return compressed_path

    def _decompress_backup(self, file_path: str) -> str:
        """Decompress a backup file"""
        path = Path(file_path)
        decompressed_path = path.with_suffix('')

        if self.config.compression == "gzip":
            with gzip.open(path, 'rb') as f_in:
                with open(decompressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        elif self.config.compression == "bz2":
            import bz2
            with bz2.open(path, 'rb') as f_in:
                with open(decompressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

        return str(decompressed_path)

    def _encrypt_backup(self, file_path: Path, job_id: str) -> Path:
        """Encrypt a backup file"""
        from src.panel.config_manager import SecretManager

        encrypted_path = file_path.with_suffix(f"{file_path.suffix}.enc")
        secret_manager = SecretManager()

        # Read file content
        with open(file_path, 'rb') as f:
            data = f.read()

        # Encrypt data
        encrypted_data = secret_manager.encrypt_secret(data.decode('latin-1'))

        # Write encrypted data
        with open(encrypted_path, 'w') as f:
            f.write(encrypted_data)

        # Remove original file
        file_path.unlink()

        return encrypted_path

    def _decrypt_backup(self, file_path: str) -> str:
        """Decrypt a backup file"""
        from src.panel.config_manager import SecretManager

        path = Path(file_path)
        decrypted_path = path.with_suffix('')

        secret_manager = SecretManager()

        # Read encrypted data
        with open(path, 'r') as f:
            encrypted_data = f.read()

        # Decrypt data
        decrypted_data = secret_manager.decrypt_secret(encrypted_data)

        # Write decrypted data
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted_data.encode('latin-1'))

        return str(decrypted_path)

    def _send_backup_notification(self, results: List[Dict[str, Any]]):
        """Send backup completion notification"""
        # This would integrate with your notification system
        # For now, just log the results
        success_count = sum(1 for r in results if r.get('status') == 'completed')
        total_count = len(results)

        self.logger.info(f"Backup notification: {success_count}/{total_count} backups completed")

        # TODO: Integrate with email, Slack, etc.
        # from src.panel.notifications import send_notification
        # send_notification("Backup Status", f"{success_count}/{total_count} backups completed")


class DatabaseBackup:
    """Handles database backups"""

    def __init__(self, app: Flask):
        self.app = app
        self.db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')

    def create_backup(self, job_id: str) -> Path:
        """Create database backup"""
        backup_manager = get_backup_manager()
        backup_dir = backup_manager.backup_dir
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"db_backup_{timestamp}.sql"

        if self.db_url.startswith('postgresql://'):
            self._backup_postgresql(str(backup_file))
        elif self.db_url.startswith('mysql://'):
            self._backup_mysql(str(backup_file))
        elif self.db_url.startswith('sqlite:///'):
            self._backup_sqlite(str(backup_file))
        else:
            raise ValueError(f"Unsupported database type: {self.db_url}")

        return backup_file

    def restore_backup(self, backup_file: str) -> Dict[str, Any]:
        """Restore database from backup"""
        if self.db_url.startswith('postgresql://'):
            self._restore_postgresql(backup_file)
        elif self.db_url.startswith('mysql://'):
            self._restore_mysql(backup_file)
        elif self.db_url.startswith('sqlite:///'):
            self._restore_sqlite(backup_file)
        else:
            raise ValueError(f"Unsupported database type: {self.db_url}")

        return {'status': 'restored', 'database': self.db_url}

    def _backup_postgresql(self, output_file: str):
        """Backup PostgreSQL database"""
        # Parse connection details
        from urllib.parse import urlparse
        parsed = urlparse(self.db_url)
        db_name = parsed.path.lstrip('/')
        host = parsed.hostname
        port = parsed.port or 5432
        user = parsed.username
        password = parsed.password

        env = os.environ.copy()
        env['PGPASSWORD'] = password or ''

        cmd = [
            'pg_dump',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', db_name,
            '-f', output_file,
            '--no-password',
            '--format=custom'  # Custom format for better compression
        ]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"PostgreSQL backup failed: {result.stderr}")

    def _restore_postgresql(self, backup_file: str):
        """Restore PostgreSQL database"""
        from urllib.parse import urlparse
        parsed = urlparse(self.db_url)
        db_name = parsed.path.lstrip('/')
        host = parsed.hostname
        port = parsed.port or 5432
        user = parsed.username
        password = parsed.password

        env = os.environ.copy()
        env['PGPASSWORD'] = password or ''

        cmd = [
            'pg_restore',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', db_name,
            '--clean',
            '--if-exists',
            backup_file
        ]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"PostgreSQL restore failed: {result.stderr}")

    def _backup_mysql(self, output_file: str):
        """Backup MySQL database"""
        from urllib.parse import urlparse
        parsed = urlparse(self.db_url)
        db_name = parsed.path.lstrip('/')
        host = parsed.hostname
        port = parsed.port or 3306
        user = parsed.username
        password = parsed.password

        cmd = [
            'mysqldump',
            '-h', host,
            '-P', str(port),
            '-u', user,
            f'-p{password}',
            db_name
        ]

        with open(output_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise Exception(f"MySQL backup failed: {result.stderr}")

    def _restore_mysql(self, backup_file: str):
        """Restore MySQL database"""
        from urllib.parse import urlparse
        parsed = urlparse(self.db_url)
        db_name = parsed.path.lstrip('/')
        host = parsed.hostname
        port = parsed.port or 3306
        user = parsed.username
        password = parsed.password

        cmd = [
            'mysql',
            '-h', host,
            '-P', str(port),
            '-u', user,
            f'-p{password}',
            db_name
        ]

        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                raise Exception(f"MySQL restore failed: {result.stderr}")

    def _backup_sqlite(self, output_file: str):
        """Backup SQLite database"""
        db_path = self.db_url.replace('sqlite:///', '')
        shutil.copy2(db_path, output_file)

    def _restore_sqlite(self, backup_file: str):
        """Restore SQLite database"""
        db_path = self.db_url.replace('sqlite:///', '')
        shutil.copy2(backup_file, db_path)


class FilesystemBackup:
    """Handles filesystem backups"""

    def __init__(self, app: Flask):
        self.app = app
        self.backup_paths = [
            'static/uploads',
            'instance',
            'logs',
            'config'
        ]

    def create_backup(self, job_id: str) -> Path:
        """Create filesystem backup"""
        backup_manager = get_backup_manager()
        backup_dir = backup_manager.backup_dir
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"fs_backup_{timestamp}.tar.gz"

        # Create temporary directory for backup
        temp_dir = backup_dir / f"temp_{job_id}"
        temp_dir.mkdir()

        try:
            # Copy files to backup
            for path in self.backup_paths:
                src_path = Path(path)
                if src_path.exists():
                    dst_path = temp_dir / src_path.name
                    if src_path.is_file():
                        shutil.copy2(src_path, dst_path)
                    else:
                        shutil.copytree(src_path, dst_path, dirs_exist_ok=True)

            # Create compressed archive
            with tarfile.open(backup_file, "w:gz") as tar:
                for item in temp_dir.rglob('*'):
                    if item.is_file():
                        tar.add(item, arcname=item.relative_to(temp_dir))

            return backup_file

        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def restore_backup(self, backup_file: str) -> Dict[str, Any]:
        """Restore filesystem from backup"""
        backup_path = Path(backup_file)

        # Create temporary directory for extraction
        temp_dir = backup_path.parent / f"restore_temp_{int(time.time())}"
        temp_dir.mkdir()

        try:
            # Extract archive
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)

            # Restore files
            restored_paths = []
            for item in temp_dir.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(temp_dir)
                    target_path = Path(relative_path)

                    # Create parent directories
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(item, target_path)
                    restored_paths.append(str(target_path))

            return {
                'status': 'restored',
                'files_restored': len(restored_paths),
                'paths': restored_paths[:10]  # Limit output
            }

        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)


class ApplicationBackup:
    """Handles application state backups"""

    def __init__(self, app: Flask):
        self.app = app

    def create_backup(self, job_id: str) -> Path:
        """Create application state backup"""
        backup_manager = get_backup_manager()
        backup_dir = backup_manager.backup_dir
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"app_backup_{timestamp}.json"

        # Collect application state
        app_state = {
            'timestamp': timestamp,
            'version': '1.0.0',  # Would come from version file
            'environment': os.getenv('FLASK_ENV', 'development'),
            'config': {
                k: v for k, v in self.app.config.items()
                if not k.startswith('_') and 'SECRET' not in k and 'PASSWORD' not in k
            },
            'routes': [str(rule) for rule in self.app.url_map.iter_rules()],
            'active_users': 0,  # Would need to query database
            'system_info': {
                'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
                'platform': os.sys.platform
            }
        }

        # Save to file
        with open(backup_file, 'w') as f:
            json.dump(app_state, f, indent=2, default=str)

        return backup_file

    def restore_backup(self, backup_file: str) -> Dict[str, Any]:
        """Restore application state"""
        with open(backup_file, 'r') as f:
            app_state = json.load(f)

        # This would typically restore application configuration
        # For now, just validate the backup
        return {
            'status': 'validated',
            'version': app_state.get('version'),
            'environment': app_state.get('environment'),
            'routes_count': len(app_state.get('routes', []))
        }


class ConfigurationBackup:
    """Handles configuration backups"""

    def __init__(self, app: Flask):
        self.app = app

    def create_backup(self, job_id: str) -> Path:
        """Create configuration backup"""
        from src.panel.config_manager import get_config_manager

        backup_manager = get_backup_manager()
        backup_dir = backup_manager.backup_dir
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"config_backup_{timestamp}.tar.gz"

        # Create temporary directory
        temp_dir = backup_dir / f"config_temp_{job_id}"
        temp_dir.mkdir()

        try:
            # Backup configuration files
            config_files = [
                'config/config.*.json',
                '.env',
                '.secrets',
                '.config_key',
                'pyproject.toml',
                'requirements.txt',
                'requirements/requirements*.txt'
            ]

            for pattern in config_files:
                for file_path in Path('.').glob(pattern):
                    if file_path.exists():
                        shutil.copy2(file_path, temp_dir / file_path.name)

            # Create compressed archive
            with tarfile.open(backup_file, "w:gz") as tar:
                for item in temp_dir.rglob('*'):
                    if item.is_file():
                        tar.add(item, arcname=item.relative_to(temp_dir))

            return backup_file

        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

    def restore_backup(self, backup_file: str) -> Dict[str, Any]:
        """Restore configuration from backup"""
        backup_path = Path(backup_file)
        temp_dir = backup_path.parent / f"config_restore_temp_{int(time.time())}"
        temp_dir.mkdir()

        try:
            # Extract archive
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)

            # Restore configuration files
            restored_files = []
            for item in temp_dir.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(temp_dir)
                    target_path = Path(relative_path)

                    # Create parent directories
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Backup existing file
                    if target_path.exists():
                        backup_file = target_path.with_suffix(f"{target_path.suffix}.backup")
                        shutil.copy2(target_path, backup_file)

                    # Copy new file
                    shutil.copy2(item, target_path)
                    restored_files.append(str(target_path))

            return {
                'status': 'restored',
                'files_restored': len(restored_files),
                'files': restored_files
            }

        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)


# Global backup manager instance
backup_manager = None

def init_backup_system(app: Flask):
    """Initialize backup and recovery system"""
    global backup_manager

    # Get backup configuration from app config
    backup_config = BackupConfig(
        enabled=app.config.get('BACKUP_ENABLED', True),
        schedule=app.config.get('BACKUP_SCHEDULE', 'daily'),
        retention_days=app.config.get('BACKUP_RETENTION_DAYS', 30),
        compression=app.config.get('BACKUP_COMPRESSION', 'gzip'),
        encryption=app.config.get('BACKUP_ENCRYPTION', False),
        storage_path=app.config.get('BACKUP_STORAGE_PATH', 'backups'),
        verify_backups=app.config.get('BACKUP_VERIFY', True),
        notification_enabled=app.config.get('BACKUP_NOTIFICATIONS', True)
    )

    backup_manager = BackupManager(app, backup_config)

    # Start scheduler if enabled
    if backup_config.enabled:
        backup_manager.start_scheduler()

    app.logger.info("Backup and recovery system initialized")

    return backup_manager


def get_backup_manager() -> BackupManager:
    """Get the global backup manager instance"""
    return backup_manager


# Utility functions
def create_backup(backup_type: str, name: str = None) -> Dict[str, Any]:
    """Create a backup (convenience function)"""
    manager = get_backup_manager()
    return manager.create_backup(backup_type, name)


def restore_backup(backup_type: str, backup_file: str) -> Dict[str, Any]:
    """Restore from backup (convenience function)"""
    manager = get_backup_manager()
    return manager.restore_backup(backup_type, backup_file)


def list_backups(backup_type: str = None) -> List[Dict[str, Any]]:
    """List available backups (convenience function)"""
    manager = get_backup_manager()
    return manager.list_backups(backup_type)


def get_backup_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get backup job status (convenience function)"""
    manager = get_backup_manager()
    return manager.get_backup_status(job_id)