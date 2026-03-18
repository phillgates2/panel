"""
Ptero-Eggs Auto-Update System

Automatically fetches and updates game server templates from the Ptero-Eggs repository.
Tracks versions, manages updates, and provides notification system.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.db import db
from config_manager import ConfigTemplate

logger = logging.getLogger(__name__)


def _resolve_git_executable() -> Optional[str]:
    """Best-effort locate a usable `git` executable.

    Some production systemd units override PATH to only include the venv.
    In that case, subprocess calls to `git` fail even when git is installed
    at /usr/bin/git.
    """

    configured = (os.environ.get("PANEL_GIT_BIN") or "").strip()
    if configured:
        if os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        return None

    found = shutil.which("git")
    if found:
        return found

    for candidate in ("/usr/bin/git", "/usr/local/bin/git", "/bin/git"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def _default_auto_sync_enabled() -> bool:
    val = (os.environ.get("PANEL_AUTO_SYNC_PTERO_EGGS") or "1").strip().lower()
    return val in ("1", "true", "yes", "on")


def _auto_sync_max_age_seconds() -> int:
    raw = (os.environ.get("PANEL_AUTO_SYNC_PTERO_EGGS_MAX_AGE_HOURS") or "24").strip()
    try:
        hours = int(raw)
    except Exception:
        hours = 24
    if hours < 0:
        hours = 0
    return hours * 3600


def _should_auto_sync(updater: "PteroEggsUpdater") -> bool:
    """Decide whether an auto-sync should run (best-effort)."""
    try:
        # If there are no imported eggs at all, always sync.
        existing_count = (
            ConfigTemplate.query.filter(ConfigTemplate.name.ilike("%(Ptero-Eggs)%")).count()
        )
        if existing_count <= 0:
            return True

        # If we can read sync metadata, only re-sync when stale.
        status = updater.get_sync_status() if updater._table_exists("ptero_eggs_update_metadata") else None
        if not status:
            return False

        last_sync_at = status.get("last_sync_at")
        if not last_sync_at:
            return True

        try:
            age = (datetime.now(timezone.utc) - last_sync_at).total_seconds()
        except Exception:
            return True

        return age >= float(_auto_sync_max_age_seconds())
    except Exception:
        # If anything goes wrong, don't aggressively sync.
        return False


def _try_acquire_lock(lock_path: Path) -> Optional[int]:
    """Acquire a best-effort inter-process lock.

    Returns a file descriptor on success, else None.
    """
    try:
        import fcntl  # Unix-only

        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            return None
        return fd
    except Exception:
        return None


def _release_lock(fd: Optional[int]) -> None:
    if fd is None:
        return
    try:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        os.close(fd)
    except Exception:
        pass


def trigger_ptero_eggs_auto_sync(
    flask_app,
    admin_user_id: int,
    *,
    repo_url: Optional[str] = None,
    repo_path: str = "/tmp/game-eggs",
) -> bool:
    """Trigger a background sync if auto-sync is enabled.

    Intended for request handlers (non-blocking). Returns True if a new sync
    thread was started.
    """

    if not _default_auto_sync_enabled():
        return False

    app_obj = flask_app

    # Run a cheap check inside the app context (callers typically invoke this
    # from within a request or startup hook where an app context exists).
    try:
        updater = PteroEggsUpdater(repo_path=repo_path, repo_url=repo_url)
        if not _should_auto_sync(updater):
            return False
    except Exception:
        # If we can't determine, fall back to not syncing.
        return False

    lock_fd = _try_acquire_lock(Path("/tmp/panel-ptero-eggs-sync.lock"))
    if lock_fd is None:
        return False

    def _worker() -> None:
        try:
            with app_obj.app_context():
                updater = PteroEggsUpdater(repo_path=repo_path, repo_url=repo_url)
                stats = updater.sync_templates(int(admin_user_id))
                logger.info(f"Ptero-Eggs auto-sync finished: {stats.get('message')}")
        except Exception as e:
            logger.error(f"Ptero-Eggs auto-sync failed: {e}")
        finally:
            _release_lock(lock_fd)

    t = threading.Thread(target=_worker, name="ptero-eggs-auto-sync", daemon=True)
    t.start()
    return True


class PteroEggsUpdateMetadata(db.Model):
    """Track Ptero-Eggs repository updates and sync status."""

    __tablename__ = "ptero_eggs_update_metadata"

    id = db.Column(db.Integer, primary_key=True)
    repository_url = db.Column(
        db.String(255),
        nullable=False,
        # Default to the official Pterodactyl egg repository.
        default="https://github.com/pterodactyl/game-eggs.git",
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
    template_id = db.Column(
        db.Integer, db.ForeignKey("config_template.id"), nullable=False
    )
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

    def __init__(self, repo_path: str = "/tmp/game-eggs", repo_url: Optional[str] = None):
        self.repo_path = Path(repo_path)
        # Allow overriding the repo URL at runtime.
        # Defaults to the official Pterodactyl `game-eggs` repository.
        self.repo_url = (
            repo_url
            or os.environ.get("PANEL_EGGS_REPO_URL")
            or "https://github.com/pterodactyl/game-eggs.git"
        )
        # When git is unavailable or blocked, we can fall back to downloading
        # a GitHub archive. Track this so commit metadata can degrade cleanly.
        self._archive_source_url: Optional[str] = None

    def _github_archive_urls(self) -> List[str]:
        """Best-effort derive GitHub archive URLs from repo_url."""
        url = (self.repo_url or "").strip()

        # Support https://github.com/<owner>/<repo>(.git)
        m = re.match(r"^https?://github\\.com/([^/]+)/([^/]+?)(?:\\.git)?/?$", url)
        if not m:
            # Support git@github.com:<owner>/<repo>.git
            m = re.match(r"^git@github\\.com:([^/]+)/([^/]+?)(?:\\.git)?$", url)
        if not m:
            return []

        owner, repo = m.group(1), m.group(2)
        branches = ("main", "master")
        return [
            f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
            for branch in branches
        ]

    def _extract_zip_safely(self, zip_path: Path, dest_dir: Path) -> None:
        """Extract a zip into dest_dir, preventing path traversal."""
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    continue
                zf.extract(member, dest_dir)

    def _download_and_extract_archive(self) -> Tuple[bool, str]:
        """Fallback: download GitHub zip archive and extract into repo_path."""
        urls = self._github_archive_urls()
        if not urls:
            return False, "Archive fallback unavailable for this repository URL"

        last_err: Optional[str] = None
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=120) as resp:
                    data = resp.read()

                with tempfile.TemporaryDirectory(prefix="panel-eggs-") as tmp_dir:
                    tmp_path = Path(tmp_dir)
                    zip_file = tmp_path / "repo.zip"
                    zip_file.write_bytes(data)

                    extract_dir = tmp_path / "extract"
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    self._extract_zip_safely(zip_file, extract_dir)

                    # GitHub archives extract into a single top-level folder.
                    extracted_children = [p for p in extract_dir.iterdir() if p.is_dir()]
                    if len(extracted_children) != 1:
                        return False, "Unexpected archive layout"

                    extracted_root = extracted_children[0]

                    # Replace existing repo_path contents.
                    try:
                        if self.repo_path.exists():
                            shutil.rmtree(self.repo_path)
                    except Exception:
                        pass
                    self.repo_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(extracted_root), str(self.repo_path))

                self._archive_source_url = url
                return True, f"Repository downloaded from archive: {url}"
            except Exception as e:
                last_err = str(e)
                continue

        return False, f"Archive download failed: {last_err or 'unknown error'}"

    def _table_exists(self, table_name: str) -> bool:
        """Best-effort check for whether a DB table exists.

        Some deployments may not have run migrations that create the optional
        Ptero-Eggs tracking tables yet. We still want template imports to work.
        """
        try:
            from sqlalchemy import inspect

            return bool(inspect(db.engine).has_table(table_name))
        except Exception:
            return False

    def clone_or_update_repository(self) -> Tuple[bool, str]:
        """Clone the Ptero-Eggs repository or update if it exists.

        Returns:
            Tuple of (success, message)
        """
        try:
            git_bin = _resolve_git_executable()
            if not git_bin:
                path_val = os.environ.get("PATH") or ""
                msg = (
                    "git executable not found. If running under systemd, ensure PATH includes /usr/bin "
                    f"(current PATH={path_val!r}) or set PANEL_GIT_BIN=/usr/bin/git."
                )
                logger.error(msg)
                # Fall back to archive mode if possible.
                archive_ok, archive_msg = self._download_and_extract_archive()
                if archive_ok:
                    return True, archive_msg
                return False, msg

            if self.repo_path.exists():
                logger.info(f"Updating existing repository at {self.repo_path}")
                # Ensure the existing clone points at the configured origin.
                try:
                    subprocess.run(
                        [git_bin, "-C", str(self.repo_path), "remote", "set-url", "origin", self.repo_url],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                except Exception:
                    pass
                # Update existing repository. Avoid hard-coding branch names
                # since upstream repos may use main or master.
                pull_cmds = [
                    [git_bin, "-C", str(self.repo_path), "pull", "--ff-only"],
                    [git_bin, "-C", str(self.repo_path), "pull", "origin", "main", "--ff-only"],
                    [git_bin, "-C", str(self.repo_path), "pull", "origin", "master", "--ff-only"],
                ]

                last_err = None
                for cmd in pull_cmds:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if result.returncode == 0:
                        return True, "Repository updated successfully"
                    last_err = (result.stderr or result.stdout or "").strip()

                # Fallback: if updating fails (corrupt clone, blocked network,
                # missing git), try refreshing from a GitHub archive.
                archive_ok, archive_msg = self._download_and_extract_archive()
                if archive_ok:
                    return True, archive_msg

                return False, f"Git pull failed: {last_err or 'unknown error'}"
            else:
                logger.info(f"Cloning repository to {self.repo_path}")
                # Clone repository
                clone_cmds = [
                    [git_bin, "clone", "--depth", "1", self.repo_url, str(self.repo_path)],
                    [git_bin, "clone", self.repo_url, str(self.repo_path)],
                ]

                last_err = None
                for cmd in clone_cmds:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    if result.returncode == 0:
                        return True, "Repository cloned successfully"
                    last_err = (result.stderr or result.stdout or "").strip()

                # Fallback: if git is unavailable or blocked, try GitHub archive.
                archive_ok, archive_msg = self._download_and_extract_archive()
                if archive_ok:
                    return True, archive_msg

                return False, f"Git clone failed: {last_err or 'unknown error'}"

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
            # If we used the archive fallback, there is no git metadata.
            if self._archive_source_url:
                return {
                    "commit_hash": "archive",
                    "commit_message": f"Downloaded from {self._archive_source_url}",
                }

            git_bin = _resolve_git_executable()
            if not git_bin:
                return None

            # Get commit hash
            result = subprocess.run(
                [git_bin, "-C", str(self.repo_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            commit_hash = result.stdout.strip()

            # Get commit message
            result = subprocess.run(
                [git_bin, "-C", str(self.repo_path), "log", "-1", "--pretty=%B"],
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
        self,
        egg_path: Path,
        admin_user_id: int,
        commit_hash: str,
        track_versions: bool = True,
    ) -> Tuple[str, Optional[int]]:
        """Import or update a single template from an egg file.

        Args:
            egg_path: Path to the egg JSON file
            admin_user_id: User ID of the admin performing the import
            commit_hash: Current commit hash for version tracking

        Returns:
            Tuple of (status, template_id) where status is 'added', 'updated', 'unchanged', or 'error'
        """
        from scripts.import_ptero_eggs import (clean_game_type,
                                               extract_config_from_egg)

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

                # Update template
                existing.template_data = template_data_json
                existing.description = (
                    f"{description}\n\nSource: Ptero-Eggs\nAuthor: {author}"
                )
                existing.updated_at = datetime.now(timezone.utc)

                if track_versions:
                    try:
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
                        db.session.add(new_version)
                    except Exception:
                        # If version tracking tables aren't present, proceed without history.
                        pass

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

                if track_versions:
                    try:
                        # Create initial version entry
                        initial_version = PteroEggsTemplateVersion(
                            template_id=template.id,
                            version_number=1,
                            commit_hash=commit_hash,
                            template_data_snapshot=template_data_json,
                            is_current=True,
                        )
                        db.session.add(initial_version)
                    except Exception:
                        pass

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
            has_versions = self._table_exists("ptero_eggs_template_version")
            has_metadata = self._table_exists("ptero_eggs_update_metadata")

            # Clone or update repository
            success, message = self.clone_or_update_repository()
            if not success:
                stats["message"] = message
                return stats

            # Get commit info
            commit_info = self.get_current_commit_info()
            if not commit_info:
                # Non-fatal: templates can still be imported without git metadata.
                commit_info = {
                    "commit_hash": "unknown",
                    "commit_message": "unknown (no git metadata)",
                }

            # Find all egg files
            egg_files = self.find_egg_files()
            if not egg_files:
                stats["message"] = "No egg files found in repository"
                return stats

            stats["total_processed"] = len(egg_files)

            # Process each egg file
            for egg_file in egg_files:
                status, template_id = self.import_or_update_template(
                    egg_file,
                    admin_user_id,
                    commit_info["commit_hash"],
                    track_versions=has_versions,
                )

                if status == "added":
                    stats["added"] += 1
                elif status == "updated":
                    stats["updated"] += 1
                elif status == "unchanged":
                    stats["unchanged"] += 1
                elif status == "error":
                    stats["errors"] += 1

            # Commit template changes first so missing optional tables can't
            # prevent core imports from working.
            db.session.commit()

            # Update metadata (optional)
            if has_metadata:
                try:
                    metadata = PteroEggsUpdateMetadata.query.first()
                    if not metadata:
                        metadata = PteroEggsUpdateMetadata()
                        db.session.add(metadata)

                    metadata.last_sync_at = datetime.now(timezone.utc)
                    metadata.repository_url = self.repo_url
                    metadata.last_commit_hash = commit_info["commit_hash"]
                    metadata.last_commit_message = commit_info["commit_message"]
                    metadata.last_sync_status = "success"
                    metadata.last_error_message = None
                    metadata.total_templates_imported = (
                        stats["added"] + stats["updated"] + stats["unchanged"]
                    )
                    metadata.templates_added = stats["added"]
                    metadata.templates_updated = stats["updated"]

                    db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

            stats["success"] = True
            stats["message"] = (
                f"Sync completed: {stats['added']} added, {stats['updated']} updated, {stats['unchanged']} unchanged, {stats['errors']} errors"
            )

            logger.info(f"Ptero-Eggs sync completed: {stats['message']}")

        except Exception as e:
            db.session.rollback()
            stats["message"] = f"Sync failed: {str(e)}"
            logger.error(f"Ptero-Eggs sync failed: {e}")

            # Update metadata with error (optional)
            try:
                if self._table_exists("ptero_eggs_update_metadata"):
                    metadata = PteroEggsUpdateMetadata.query.first()
                    if metadata:
                        metadata.last_sync_status = "failed"
                        metadata.last_error_message = str(e)
                        db.session.commit()
            except Exception:
                pass

        return stats

    def get_sync_status(self) -> Optional[Dict[str, any]]:
        """Get the current sync status and metadata.

        Returns:
            Dictionary with sync status information, or None if never synced
        """
        if not self._table_exists("ptero_eggs_update_metadata"):
            return None

        try:
            metadata = PteroEggsUpdateMetadata.query.first()
        except Exception:
            return None

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

            redis_conn = Redis.from_url(
                app.config.get("REDIS_URL", "redis://localhost:6379/0")
            )
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


def _cli_find_admin_user(admin_user_id: Optional[int], admin_email: Optional[str]):
    """Resolve the admin user to attribute imports to (CLI helper)."""
    from app import User

    if admin_user_id is not None:
        admin = User.query.get(int(admin_user_id))
        if admin:
            return admin
        raise ValueError(f"No user found with id={admin_user_id}")

    if admin_email:
        admin = User.query.filter_by(email=admin_email).first()
        if admin:
            return admin
        raise ValueError(f"No user found with email={admin_email}")

    admin = User.query.filter_by(role="system_admin").order_by(User.id.asc()).first()
    if not admin:
        raise ValueError("No system_admin user found")
    return admin


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint.

    Examples:
        python ptero_eggs_updater.py sync
        python ptero_eggs_updater.py sync --admin-email admin@example.com
        PANEL_EGGS_REPO_URL=https://github.com/pterodactyl/game-eggs.git python ptero_eggs_updater.py sync
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="ptero_eggs_updater.py",
        description="Sync Ptero-Eggs templates into Panel",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sync_p = sub.add_parser("sync", help="Clone/pull game-eggs and import all egg templates")
    sync_p.add_argument(
        "--repo-url",
        default=None,
        help="Repository URL (default: PANEL_EGGS_REPO_URL or official game-eggs)",
    )
    sync_p.add_argument(
        "--repo-path",
        default=None,
        help="Local clone path (default: /tmp/game-eggs)",
    )
    sync_p.add_argument("--admin-user-id", type=int, default=None, help="Attribute import to this user id")
    sync_p.add_argument("--admin-email", default=None, help="Attribute import to this admin email")
    sync_p.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output (default)",
    )

    status_p = sub.add_parser("status", help="Show last sync metadata (if enabled)")
    status_p.add_argument("--repo-url", default=None)
    status_p.add_argument("--repo-path", default=None)
    status_p.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    from app import app

    with app.app_context():
        try:
            repo_path = args.repo_path if getattr(args, "repo_path", None) else "/tmp/game-eggs"
            repo_url = getattr(args, "repo_url", None)
            updater = PteroEggsUpdater(repo_path=repo_path, repo_url=repo_url)

            if args.command == "status":
                status = updater.get_sync_status() or {}
                print(json.dumps(status, default=str))
                return 0

            if args.command == "sync":
                admin = _cli_find_admin_user(args.admin_user_id, args.admin_email)
                stats = updater.sync_templates(admin.id)
                print(json.dumps(stats, default=str))
                return 0 if stats.get("success") else 1

            raise ValueError(f"Unknown command: {args.command}")

        except Exception as e:
            # Print JSON so automation can capture the reason.
            err = {"success": False, "message": str(e)}
            print(json.dumps(err, default=str))
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
