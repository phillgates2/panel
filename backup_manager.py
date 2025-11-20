import os
import shutil
import subprocess
import tarfile
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automated backups for the panel system."""

    def __init__(self, backup_dir="backups", db_url=None):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.db_url = db_url

        # Create subdirectories
        self.db_backups = self.backup_dir / "database"
        self.config_backups = self.backup_dir / "config"
        self.server_backups = self.backup_dir / "servers"

        for dir_path in [self.db_backups, self.config_backups, self.server_backups]:
            dir_path.mkdir(exist_ok=True)

    def create_database_backup(self, name=None):
        """Create a database backup."""
        if not name:
            name = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_file = self.db_backups / f"{name}.sql"

        try:
            # Use pg_dump for PostgreSQL
            if self.db_url and 'postgresql' in self.db_url:
                # Extract connection details from SQLAlchemy URL
                # This is a simplified version - in production you'd parse the URL properly
                cmd = [
                    'pg_dump',
                    '--no-owner',
                    '--no-privileges',
                    '--clean',
                    '--if-exists',
                    '-f', str(backup_file)
                ]

                # Add connection string if available
                if self.db_url:
                    # This would need proper URL parsing in production
                    pass

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"Database backup created: {backup_file}")
                    return str(backup_file)
                else:
                    logger.error(f"Database backup failed: {result.stderr}")
                    return None

            else:
                # For SQLite or other databases, copy the file
                db_path = self._get_db_path()
                if db_path and db_path.exists():
                    shutil.copy2(db_path, backup_file)
                    logger.info(f"Database backup created: {backup_file}")
                    return str(backup_file)

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return None

    def create_config_backup(self, config_files=None, name=None):
        """Create a backup of configuration files."""
        if not name:
            name = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_file = self.config_backups / f"{name}.tar.gz"

        if not config_files:
            # Default config files to backup
            config_files = [
                'config.py',
                'config_dev.py',
                'docker-compose.dev.yml',
                'Dockerfile.dev',
                'requirements.txt',
                'pytest.ini'
            ]

        try:
            with tarfile.open(backup_file, 'w:gz') as tar:
                for config_file in config_files:
                    if os.path.exists(config_file):
                        tar.add(config_file, arcname=os.path.basename(config_file))

            # Also backup environment variables (redacted)
            env_backup = self._create_env_backup()
            if env_backup:
                env_file = self.config_backups / f"{name}_env.json"
                with open(env_file, 'w') as f:
                    json.dump(env_backup, f, indent=2)

            logger.info(f"Config backup created: {backup_file}")
            return str(backup_file)

        except Exception as e:
            logger.error(f"Config backup failed: {e}")
            return None

    def create_server_backup(self, server_id, server_data, name=None):
        """Create a backup of server configuration and data."""
        if not name:
            name = f"server_{server_id}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_file = self.server_backups / f"{name}.json"

        try:
            # Create server backup data
            backup_data = {
                'server_id': server_id,
                'backup_time': datetime.now().isoformat(),
                'server_config': server_data,
                'metadata': {
                    'version': '1.0',
                    'type': 'server_config'
                }
            }

            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)

            logger.info(f"Server backup created: {backup_file}")
            return str(backup_file)

        except Exception as e:
            logger.error(f"Server backup failed: {e}")
            return None

    def list_backups(self, backup_type=None):
        """List available backups."""
        backups = {}

        if backup_type in [None, 'database']:
            backups['database'] = self._list_files(self.db_backups)

        if backup_type in [None, 'config']:
            backups['config'] = self._list_files(self.config_backups)

        if backup_type in [None, 'server']:
            backups['server'] = self._list_files(self.server_backups)

        return backups

    def restore_database(self, backup_file):
        """Restore database from backup."""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        try:
            if backup_path.suffix == '.sql':
                # PostgreSQL restore
                cmd = ['psql', '-f', str(backup_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"Database restored from: {backup_file}")
                    return True
                else:
                    logger.error(f"Database restore failed: {result.stderr}")
                    return False

            else:
                # SQLite restore
                db_path = self._get_db_path()
                if db_path:
                    shutil.copy2(backup_path, db_path)
                    logger.info(f"Database restored from: {backup_file}")
                    return True

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False

    def restore_config(self, backup_file):
        """Restore configuration files from backup."""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        try:
            # Create restore directory
            restore_dir = self.backup_dir / "restore_temp"
            restore_dir.mkdir(exist_ok=True)

            # Extract backup
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(restore_dir)

            # Restore files (with confirmation prompt in UI)
            restored_files = []
            for item in restore_dir.iterdir():
                if item.is_file():
                    target_path = Path(item.name)
                    if target_path.exists():
                        # Create backup of current file
                        backup_current = target_path.with_suffix(f"{target_path.suffix}.backup")
                        shutil.copy2(target_path, backup_current)

                    shutil.copy2(item, target_path)
                    restored_files.append(str(target_path))

            # Cleanup
            shutil.rmtree(restore_dir)

            logger.info(f"Config restored from: {backup_file}")
            return restored_files

        except Exception as e:
            logger.error(f"Config restore failed: {e}")
            return False

    def cleanup_old_backups(self, days_to_keep=30):
        """Clean up backups older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_files = []

        for backup_dir in [self.db_backups, self.config_backups, self.server_backups]:
            for file_path in backup_dir.glob('*'):
                if file_path.is_file():
                    # Check file modification time
                    if file_path.stat().st_mtime < cutoff_date.timestamp():
                        file_path.unlink()
                        deleted_files.append(str(file_path))

        logger.info(f"Cleaned up {len(deleted_files)} old backup files")
        return deleted_files

    def get_backup_stats(self):
        """Get backup statistics."""
        stats = {
            'total_size': 0,
            'file_count': 0,
            'oldest_backup': None,
            'newest_backup': None,
            'by_type': {}
        }

        for backup_type, backup_dir in [
            ('database', self.db_backups),
            ('config', self.config_backups),
            ('server', self.server_backups)
        ]:
            type_stats = {
                'count': 0,
                'size': 0,
                'oldest': None,
                'newest': None
            }

            for file_path in backup_dir.glob('*'):
                if file_path.is_file():
                    stat = file_path.stat()
                    type_stats['count'] += 1
                    type_stats['size'] += stat.st_size

                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    if type_stats['oldest'] is None or mtime < type_stats['oldest']:
                        type_stats['oldest'] = mtime
                    if type_stats['newest'] is None or mtime > type_stats['newest']:
                        type_stats['newest'] = mtime

            stats['by_type'][backup_type] = type_stats
            stats['total_size'] += type_stats['size']
            stats['file_count'] += type_stats['count']

            if type_stats['oldest'] and (stats['oldest_backup'] is None or type_stats['oldest'] < stats['oldest_backup']):
                stats['oldest_backup'] = type_stats['oldest']
            if type_stats['newest'] and (stats['newest_backup'] is None or type_stats['newest'] > stats['newest_backup']):
                stats['newest_backup'] = type_stats['newest']

        return stats

    def _get_db_path(self):
        """Get database file path (for SQLite)."""
        # This would need to be configured based on your setup
        # For now, return None - implement based on your database config
        return None

    def _create_env_backup(self):
        """Create a redacted backup of environment variables."""
        env_backup = {}
        sensitive_keys = ['password', 'secret', 'key', 'token']

        for key, value in os.environ.items():
            # Redact sensitive information
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                env_backup[key] = "***REDACTED***"
            else:
                env_backup[key] = value

        return env_backup

    def _list_files(self, directory):
        """List files in a directory with metadata."""
        files = []
        for file_path in directory.glob('*'):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        return files