"""
Ptero-Eggs Auto-Update System

Automatically fetches and updates game server templates from the Ptero-Eggs repository.
Tracks versions, manages updates, and provides notification system.
"""

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app import app, db
from config_manager import ConfigTemplate

logger = logging.getLogger(__name__)


class PteroEggsUpdateMetadata(db.Model):
    """Track Ptero-Eggs repository updates and sync status."""

    __tablename__ = "ptero_eggs_update_metadata"

    id = db.Column(db.Integer, primary_key=True)
    repository_url = db.Column(
        db.String(255), nullable=False, default="https://github.com/Ptero-Eggs/game-eggs.git"
    )
    last_sync_at = db.Column(db.DateTime, nullable=True)
    last_commit_hash = db.Column(db.String(64), nullable=True)
    last_commit_message = db.Column(db.Text, nullable=True)
    last_sync_status = db.Column(
        db.String(32), nullable=False, default="never"
    )  # never, success, failed
    last_error_message = db.Column(db.Text, nullable=True)
    total_templates_imported = db.Column(db.Integer, default=0)
    templates_updated = db.Column(db.Integer, default=0)
    templates_added = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PteroEggsTemplateVersion(db.Model):
    """Track version history of Ptero-Eggs templates."""

    __tablename__ = "ptero_eggs_template_version"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("config_template.id"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    commit_hash = db.Column(db.String(64), nullable=True)
    template_data_snapshot = db.Column(db.Text, nullable=False)  # JSON snapshot
    changes_summary = db.Column(db.Text, nullable=True)
    imported_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_current = db.Column(db.Boolean, default=True)

    template = db.relationship(
        "ConfigTemplate", backref=db.backref("ptero_versions", lazy="dynamic")
    )


class PteroEggsUpdater:
    """Manages updates from the Ptero-Eggs repository."""

    def __init__(self, repo_path: str = "/tmp/game-eggs"):
        self.repo_path = Path(repo_path)
        self.repo_url = "https://github.com/Ptero-Eggs/game-eggs.git"

    def clone_or_update_repository(self) -> Tuple[bool, str]:
        """Clone the Ptero-Eggs repository or update if it exists.

        Returns:
            Tuple of (success, message)
        """
        try:
            if self.repo_path.exists():
                logger.info(f"Updating existing repository at {self.repo_path}")
                # Update existing repository
                result = subprocess.run(
                    ["git", "-C", str(self.repo_path), "pull", "origin", "main"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    return False, f"Git pull failed: {result.stderr}"

                return True, "Repository updated successfully"
            else:
                logger.info(f"Cloning repository to {self.repo_path}")
                # Clone repository
                result = subprocess.run(
                    ["git", "clone", self.repo_url, str(self.repo_path)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode != 0:
                    return False, f"Git clone failed: {result.stderr}"

                return True, "Repository cloned successfully"

        except subprocess.TimeoutExpired:
            return False, "Git operation timed out"
        except Exception as e:
            logger.error(f"Error cloning/updating repository: {e}")
            return False, str(e)

    def get_current_commit_info(self) -> Optional[Dict[str, str]]:
        """Get current commit hash and message from the repository.

        Returns:
            Dictionary with commit_hash and commit_message, or None on error
        """
        try:
            # Get commit hash
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            commit_hash = result.stdout.strip()

            # Get commit message
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "log", "-1", "--pretty=%B"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            commit_message = result.stdout.strip()

            return {"commit_hash": commit_hash, "commit_message": commit_message}

        except Exception as e:
            logger.error(f"Error getting commit info: {e}")
            return None

    def find_egg_files(self) -> List[Path]:
        """Find all egg JSON files in the repository.

        Returns:
            List of Path objects for egg files
        """
        if not self.repo_path.exists():
            return []

        return list(self.repo_path.rglob("egg-*.json"))

    def import_or_update_template(
        self, egg_path: Path, admin_user_id: int, commit_hash: str
    ) -> Tuple[str, Optional[int]]:
        """Import or update a single template from an egg file.

        Args:
            egg_path: Path to the egg JSON file
            admin_user_id: User ID of the admin performing the import
            commit_hash: Current commit hash for version tracking

        Returns:
            Tuple of (status, template_id) where status is 'added', 'updated', 'unchanged', or 'error'
        """
        from scripts.import_ptero_eggs import clean_game_type, extract_config_from_egg

        try:
            with open(egg_path, "r", encoding="utf-8") as f:
                egg_data = json.load(f)

            # Extract metadata
            name = egg_data.get("name", egg_path.stem)
            description = egg_data.get("description", "")
            author = egg_data.get("author", "Ptero-Eggs Community")
            game_type = clean_game_type(name)

            # Extract config
            config_dict = extract_config_from_egg(egg_data)

            # Add metadata
            config_dict["egg_metadata"] = {
                "source": "Ptero-Eggs",
                "author": author,
                "original_name": name,
                "exported_at": egg_data.get("exported_at", "unknown"),
                "file_path": str(egg_path.relative_to(self.repo_path)),
            }

            template_name = f"{name} (Ptero-Eggs)"
            template_data_json = json.dumps(config_dict, indent=2)

            # Check if template exists
            existing = ConfigTemplate.query.filter_by(name=template_name).first()

            if existing:
                # Check if data has changed
                if existing.template_data == template_data_json:
                    return "unchanged", existing.id

                # Mark old version as not current
                for old_version in existing.ptero_versions:
                    old_version.is_current = False

                # Create new version entry
                version_count = existing.ptero_versions.count()
                new_version = PteroEggsTemplateVersion(
                    template_id=existing.id,
                    version_number=version_count + 1,
                    commit_hash=commit_hash,
                    template_data_snapshot=template_data_json,
                    is_current=True,
                )

                # Update template
                existing.template_data = template_data_json
                existing.description = f"{description}\n\nSource: Ptero-Eggs\nAuthor: {author}"
                existing.updated_at = datetime.now(timezone.utc)

                db.session.add(new_version)

                return "updated", existing.id
            else:
                # Create new template
                template = ConfigTemplate(
                    name=template_name,
                    description=f"{description}\n\nSource: Ptero-Eggs\nAuthor: {author}",
                    game_type=game_type,
                    template_data=template_data_json,
                    is_default=False,
                    created_by=admin_user_id,
                )

                db.session.add(template)
                db.session.flush()  # Get template ID

                # Create initial version entry
                initial_version = PteroEggsTemplateVersion(
                    template_id=template.id,
                    version_number=1,
                    commit_hash=commit_hash,
                    template_data_snapshot=template_data_json,
                    is_current=True,
                )

                db.session.add(initial_version)

                return "added", template.id

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON in {egg_path}: {e}")
            return "error", None
        except Exception as e:
            logger.error(f"Error importing {egg_path}: {e}")
            return "error", None

    def sync_templates(self, admin_user_id: int) -> Dict[str, any]:
        """Sync all templates from the Ptero-Eggs repository.

        Args:
            admin_user_id: User ID of the admin performing the sync

        Returns:
            Dictionary with sync statistics
        """
        stats = {
            "success": False,
            "added": 0,
            "updated": 0,
            "unchanged": 0,
            "errors": 0,
            "total_processed": 0,
            "message": "",
        }

        try:
            # Clone or update repository
            success, message = self.clone_or_update_repository()
            if not success:
                stats["message"] = message
                return stats

            # Get commit info
            commit_info = self.get_current_commit_info()
            if not commit_info:
                stats["message"] = "Failed to get repository commit information"
                return stats

            # Find all egg files
            egg_files = self.find_egg_files()
            if not egg_files:
                stats["message"] = "No egg files found in repository"
                return stats

            stats["total_processed"] = len(egg_files)

            # Process each egg file
            for egg_file in egg_files:
                status, template_id = self.import_or_update_template(
                    egg_file, admin_user_id, commit_info["commit_hash"]
                )

                if status == "added":
                    stats["added"] += 1
                elif status == "updated":
                    stats["updated"] += 1
                elif status == "unchanged":
                    stats["unchanged"] += 1
                elif status == "error":
                    stats["errors"] += 1

            # Update metadata
            metadata = PteroEggsUpdateMetadata.query.first()
            if not metadata:
                metadata = PteroEggsUpdateMetadata()
                db.session.add(metadata)

            metadata.last_sync_at = datetime.now(timezone.utc)
            metadata.last_commit_hash = commit_info["commit_hash"]
            metadata.last_commit_message = commit_info["commit_message"]
            metadata.last_sync_status = "success"
            metadata.last_error_message = None
            metadata.total_templates_imported = (
                stats["added"] + stats["updated"] + stats["unchanged"]
            )
            metadata.templates_added = stats["added"]
            metadata.templates_updated = stats["updated"]

            # Commit all changes
            db.session.commit()

            stats["success"] = True
            stats[
                "message"
            ] = f"Sync completed: {stats['added']} added, {stats['updated']} updated, {stats['unchanged']} unchanged, {stats['errors']} errors"

            logger.info(f"Ptero-Eggs sync completed: {stats['message']}")

        except Exception as e:
            db.session.rollback()
            stats["message"] = f"Sync failed: {str(e)}"
            logger.error(f"Ptero-Eggs sync failed: {e}")

            # Update metadata with error
            try:
                metadata = PteroEggsUpdateMetadata.query.first()
                if metadata:
                    metadata.last_sync_status = "failed"
                    metadata.last_error_message = str(e)
                    db.session.commit()
            except:
                pass

        return stats

    def get_sync_status(self) -> Optional[Dict[str, any]]:
        """Get the current sync status and metadata.

        Returns:
            Dictionary with sync status information, or None if never synced
        """
        metadata = PteroEggsUpdateMetadata.query.first()
        if not metadata:
            return None

        return {
            "last_sync_at": metadata.last_sync_at,
            "last_commit_hash": metadata.last_commit_hash,
            "last_commit_message": metadata.last_commit_message,
            "last_sync_status": metadata.last_sync_status,
            "last_error_message": metadata.last_error_message,
            "total_templates_imported": metadata.total_templates_imported,
            "templates_added": metadata.templates_added,
            "templates_updated": metadata.templates_updated,
        }


def schedule_auto_update():
    """Schedule automatic Ptero-Eggs updates using RQ.

    This function can be called to set up recurring updates.
    """
    from app import app

    with app.app_context():
        try:
            from redis import Redis
            from rq_scheduler import Scheduler

            redis_conn = Redis.from_url(app.config.get("REDIS_URL", "redis://localhost:6379/0"))
            scheduler = Scheduler(connection=redis_conn)

            # Schedule daily updates at 3 AM
            scheduler.cron(
                "0 3 * * *",  # cron format: minute hour day month day_of_week
                func=auto_update_task,
                queue_name="default",
            )

            logger.info("Scheduled automatic Ptero-Eggs updates")

        except ImportError:
            logger.warning("rq-scheduler not available, auto-updates not scheduled")
        except Exception as e:
            logger.error(f"Failed to schedule auto-updates: {e}")


def auto_update_task():
    """Background task for automatic Ptero-Eggs updates."""
    from app import User, app

    with app.app_context():
        # Get an admin user to attribute the update to
        admin = User.query.filter_by(role="system_admin").first()
        if not admin:
            logger.error("No admin user found for auto-update")
            return

        updater = PteroEggsUpdater()
        stats = updater.sync_templates(admin.id)

        if stats["success"]:
            logger.info(f"Auto-update completed: {stats['message']}")
        else:
            logger.error(f"Auto-update failed: {stats['message']}")

        return stats
