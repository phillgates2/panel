"""
Configuration Management System

Manages game server configurations with version control, templates, and deployment.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import config
from app import db

logger = logging.getLogger(__name__)


class ConfigTemplate(db.Model):
    """Configuration templates for different server types."""

    __tablename__ = "config_template"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    game_type = db.Column(db.String(32), nullable=False)  # etlegacy, etc.
    template_data = db.Column(db.Text, nullable=False)  # JSON configuration
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class ConfigVersion(db.Model):
    """Configuration version history for servers."""

    __tablename__ = "config_version"

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey("server.id"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    config_data = db.Column(db.Text, nullable=False)  # JSON configuration
    config_hash = db.Column(db.String(64), nullable=False)  # SHA256 hash
    change_summary = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    deployed_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=False)

    server = db.relationship(
        "Server", backref=db.backref("config_versions", lazy="dynamic")
    )
    creator = db.relationship("User", foreign_keys=[created_by])


class ConfigDeployment(db.Model):
    """Track configuration deployments."""

    __tablename__ = "config_deployment"

    id = db.Column(db.Integer, primary_key=True)
    config_version_id = db.Column(
        db.Integer, db.ForeignKey("config_version.id"), nullable=False
    )
    deployment_status = db.Column(
        db.String(32), nullable=False
    )  # pending, success, failed, rollback
    deployment_log = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    deployed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    config_version = db.relationship(
        "ConfigVersion", backref=db.backref("deployments", lazy="dynamic")
    )
    deployer = db.relationship("User")


class ConfigManager:
    """Manages server configuration operations."""

    def __init__(self, server_id):
        self.server_id = server_id

    def get_current_config(self):
        """Get the currently active configuration."""
        return ConfigVersion.query.filter_by(
            server_id=self.server_id, is_active=True
        ).first()

    def create_version(self, config_data, user_id, change_summary=None):
        """Create a new configuration version."""
        # Serialize and hash the config data
        config_json = json.dumps(config_data, sort_keys=True)
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()

        # Check if this exact configuration already exists
        existing = ConfigVersion.query.filter_by(
            server_id=self.server_id, config_hash=config_hash
        ).first()

        if existing:
            raise ValueError("This configuration already exists")

        # Get next version number
        last_version = (
            ConfigVersion.query.filter_by(server_id=self.server_id)
            .order_by(ConfigVersion.version_number.desc())
            .first()
        )

        next_version = (last_version.version_number + 1) if last_version else 1

        # Create new version
        version = ConfigVersion(
            server_id=self.server_id,
            version_number=next_version,
            config_data=config_json,
            config_hash=config_hash,
            change_summary=change_summary,
            created_by=user_id,
        )

        db.session.add(version)
        db.session.commit()

        return version

    def deploy_version(self, version_id, user_id):
        """Deploy a configuration version."""
        version = ConfigVersion.query.get_or_404(version_id)

        if version.server_id != self.server_id:
            raise ValueError("Version does not belong to this server")

        # Create deployment record
        deployment = ConfigDeployment(
            config_version_id=version_id,
            deployment_status="pending",
            deployed_by=user_id,
        )
        db.session.add(deployment)
        db.session.commit()

        try:
            # Perform the actual deployment
            config_data = json.loads(version.config_data)
            success = self._deploy_config_to_server(config_data)

            if success:
                # Mark as active and deactivate others
                ConfigVersion.query.filter_by(
                    server_id=self.server_id, is_active=True
                ).update({"is_active": False})

                version.is_active = True
                version.deployed_at = datetime.now(timezone.utc)

                deployment.deployment_status = "success"
                deployment.completed_at = datetime.now(timezone.utc)
                deployment.deployment_log = "Configuration deployed successfully"
            else:
                deployment.deployment_status = "failed"
                deployment.completed_at = datetime.now(timezone.utc)
                deployment.deployment_log = "Failed to write configuration files"

        except Exception as e:
            deployment.deployment_status = "failed"
            deployment.completed_at = datetime.now(timezone.utc)
            deployment.deployment_log = f"Deployment error: {str(e)}"

        db.session.commit()
        return deployment

    def rollback_to_version(self, version_id, user_id):
        """Rollback to a previous configuration version."""
        version = ConfigVersion.query.get_or_404(version_id)

        if version.server_id != self.server_id:
            raise ValueError("Version does not belong to this server")

        # Create rollback deployment
        deployment = ConfigDeployment(
            config_version_id=version_id,
            deployment_status="rollback",
            deployed_by=user_id,
        )
        db.session.add(deployment)

        # Deploy the version
        try:
            config_data = json.loads(version.config_data)
            success = self._deploy_config_to_server(config_data)

            if success:
                # Mark as active
                ConfigVersion.query.filter_by(
                    server_id=self.server_id, is_active=True
                ).update({"is_active": False})

                version.is_active = True
                deployment.deployment_status = "success"
                deployment.deployment_log = (
                    f"Rolled back to version {version.version_number}"
                )
            else:
                deployment.deployment_status = "failed"
                deployment.deployment_log = "Rollback failed"

        except Exception as e:
            deployment.deployment_status = "failed"
            deployment.deployment_log = f"Rollback error: {str(e)}"

        deployment.completed_at = datetime.now(timezone.utc)
        db.session.commit()

        return deployment

    def _deploy_config_to_server(self, config_data):
        """Deploy configuration to the actual server files."""
        from app import Server

        server = Server.query.get(self.server_id)
        if not server:
            return False

        try:
            # Create server config directory structure
            etlegacy_dir = config.DOWNLOAD_DIR  # Already OS-aware from config.py
            server_path = Path(f"{etlegacy_dir}/servers/{server.name}")
            server_path.mkdir(parents=True, exist_ok=True)

            # Write main server config
            if "server_cfg" in config_data:
                with open(server_path / "server.cfg", "w") as f:
                    f.write(config_data["server_cfg"])

            # Write campaign config
            if "campaign_cfg" in config_data:
                with open(server_path / "campaign.cfg", "w") as f:
                    f.write(config_data["campaign_cfg"])

            # Write startup script
            if "startup_script" in config_data:
                script_path = server_path / "start_server.sh"
                with open(script_path, "w") as f:
                    f.write(config_data["startup_script"])
                script_path.chmod(0o755)

            # Write mod configuration
            if "mod_config" in config_data:
                with open(server_path / "nitmod.cfg", "w") as f:
                    f.write(config_data["mod_config"])

            return True

        except Exception as e:
            logger.error(f"Config deployment error: {e}")
            return False

    def get_version_history(self, limit=50):
        """Get configuration version history."""
        return (
            ConfigVersion.query.filter_by(server_id=self.server_id)
            .order_by(ConfigVersion.created_at.desc())
            .limit(limit)
            .all()
        )

    def compare_versions(self, version1_id, version2_id):
        """Compare two configuration versions."""
        v1 = ConfigVersion.query.get_or_404(version1_id)
        v2 = ConfigVersion.query.get_or_404(version2_id)

        config1 = json.loads(v1.config_data)
        config2 = json.loads(v2.config_data)

        # Generate diff
        differences = []

        # Check all keys in both configs
        all_keys = set(config1.keys()) | set(config2.keys())

        for key in all_keys:
            if key not in config1:
                differences.append({"type": "added", "key": key, "value": config2[key]})
            elif key not in config2:
                differences.append(
                    {"type": "removed", "key": key, "value": config1[key]}
                )
            elif config1[key] != config2[key]:
                differences.append(
                    {
                        "type": "modified",
                        "key": key,
                        "old_value": config1[key],
                        "new_value": config2[key],
                    }
                )

        return differences

    def validate_config(self, config_data):
        """Validate configuration data."""
        errors = []
        warnings = []

        # Basic validation rules
        required_fields = ["server_cfg"]
        for field in required_fields:
            if field not in config_data:
                errors.append(f"Missing required field: {field}")

        # Validate server.cfg content
        if "server_cfg" in config_data:
            server_cfg = config_data["server_cfg"]

            # Check for required cvars
            required_cvars = ["sv_hostname", "rconpassword", "sv_maxclients"]
            for cvar in required_cvars:
                if cvar not in server_cfg:
                    warnings.append(f"Recommended cvar missing: {cvar}")

        return {"errors": errors, "warnings": warnings}


def create_default_templates():
    """Create default configuration templates."""
    try:
        from flask import current_app

        from app import User

        # Ensure we're in an app context
        if not current_app:
            print("Warning: create_default_templates called without Flask app context")
            return

        # Get the first admin user or create a system user
        admin_user = User.query.filter_by(role="system_admin").first()
        if not admin_user:
            return

        templates = [
            {
                "name": "ET:Legacy Standard Server",
                "description": "Standard ET:Legacy server configuration",
                "game_type": "etlegacy",
                "template_data": {
                    "server_cfg": """// ET:Legacy Server Configuration
set sv_hostname "ET:Legacy Server"
set rconpassword "changeme"
set sv_maxclients 32
set g_gametype 6
set sv_pure 1
set sv_floodProtect 1
set sv_dl_maxRate 42000
set sv_allowDownload 1
set sv_wwwDownload 1
set sv_wwwBaseURL ""
set sv_wwwDlDisconnected 0
set g_heavyWeaponRestriction 100
set g_autoFireteams 1
set g_complaintlimit 6
set g_ipcomplaintlimit 3
set g_filtercams 0
set g_maxlives 0
set g_alliedmaxlives 0
set g_axismaxlives 0
set g_friendlyFire 1
set g_warmup 60
set vote_limit 5
set g_voting 0
set nextmap ""

exec "campaign.cfg"
""",
                    "campaign_cfg": """// Campaign Configuration
set g_gametype 6
clearscriptlist
scriptlist maps/goldrush.script
scriptlist maps/oasis.script
scriptlist maps/battery.script
scriptlist maps/radar.script
scriptlist maps/railgun.script
scriptlist maps/fueldump.script
""",
                    "startup_script": f"""#!/bin/bash
cd {config.DOWNLOAD_DIR}
./etlded +set dedicated 2 +set net_port 27960 +exec server.cfg
""",  # Use OS-aware path
                    "mod_config": """// n!tmod Configuration
set nitmod_version "2.3.1"
set g_shrubbot "shrubbot.cfg"
set g_shrubbot_logs 1
""",
                },
            },
            {
                "name": "ET:Legacy Competition Server",
                "description": "Competition-ready server with strict settings",
                "game_type": "etlegacy",
                "template_data": {
                    "server_cfg": """// ET:Legacy Competition Server
set sv_hostname "ET:Legacy Competition Server"
set rconpassword "changeme"
set sv_maxclients 12
set g_gametype 6
set sv_pure 1
set sv_floodProtect 1
set g_heavyWeaponRestriction 1
set g_autoFireteams 0
set g_complaintlimit 0
set g_friendlyFire 0
set g_warmup 0
set vote_limit 0
set g_voting 0
set g_maxlives 1
set g_alliedmaxlives 1
set g_axismaxlives 1

exec "campaign.cfg"
""",
                    "campaign_cfg": """// Competition Maps
set g_gametype 6
clearscriptlist
scriptlist maps/supply.script
scriptlist maps/adlernest.script
scriptlist maps/sw_grush_te.script
scriptlist maps/braundorf_b4.script
scriptlist maps/frostbite.script
scriptlist maps/erdenberg_t2.script
""",
                },
            },
        ]

        for template_data in templates:
            existing = ConfigTemplate.query.filter_by(
                name=template_data["name"]
            ).first()
            if not existing:
                template = ConfigTemplate(
                    name=template_data["name"],
                    description=template_data["description"],
                    game_type=template_data["game_type"],
                    template_data=json.dumps(template_data["template_data"]),
                    created_by=admin_user.id,
                )
                db.session.add(template)

        db.session.commit()
        logger.info("Default configuration templates created")
    except Exception as e:
        logger.warning(f"Failed to create default templates: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
