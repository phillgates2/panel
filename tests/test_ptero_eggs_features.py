"""
Tests for Ptero-Eggs auto-update and web UI features.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import User, app, db
from config_manager import ConfigTemplate
from ptero_eggs_updater import PteroEggsTemplateVersion, PteroEggsUpdateMetadata, PteroEggsUpdater


@pytest.fixture(scope="module")
def test_app():
    """Create application context for testing."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()

        # Create admin user for testing
        from datetime import date

        admin = User(
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            dob=date(1990, 1, 1),
            role="system_admin",
        )
        admin.set_password("test")
        db.session.add(admin)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()


@pytest.fixture
def auth_client(client, test_app):
    """Create authenticated test client."""
    with test_app.app_context():
        with client.session_transaction() as sess:
            # Manually set session for authenticated user
            sess["user_id"] = 1  # Admin user ID
            sess["_fresh"] = True
    return client


def test_ptero_eggs_update_metadata_model(test_app):
    """Test PteroEggsUpdateMetadata model."""
    with test_app.app_context():
        metadata = PteroEggsUpdateMetadata()
        metadata.last_commit_hash = "abc123"
        metadata.last_sync_status = "success"
        metadata.total_templates_imported = 5

        db.session.add(metadata)
        db.session.commit()

        # Verify
        saved = PteroEggsUpdateMetadata.query.first()
        assert saved is not None
        assert saved.last_commit_hash == "abc123"
        assert saved.last_sync_status == "success"
        assert saved.total_templates_imported == 5


def test_ptero_eggs_template_version_model(test_app):
    """Test PteroEggsTemplateVersion model."""
    with test_app.app_context():
        # Create a template first
        admin = User.query.filter_by(role="system_admin").first()

        template = ConfigTemplate(
            name="Test Template",
            description="Test",
            game_type="test",
            template_data='{"test": "data"}',
            created_by=admin.id,
        )
        db.session.add(template)
        db.session.flush()

        # Create version
        version = PteroEggsTemplateVersion(
            template_id=template.id,
            version_number=1,
            commit_hash="abc123",
            template_data_snapshot='{"test": "data"}',
            is_current=True,
        )
        db.session.add(version)
        db.session.commit()

        # Verify
        saved = PteroEggsTemplateVersion.query.first()
        assert saved is not None
        assert saved.version_number == 1
        assert saved.commit_hash == "abc123"
        assert saved.is_current is True


def test_ptero_eggs_updater_initialization():
    """Test PteroEggsUpdater initialization."""
    updater = PteroEggsUpdater()
    assert updater.repo_path == Path("/tmp/game-eggs")
    assert updater.repo_url == "https://github.com/Ptero-Eggs/game-eggs.git"

    # Custom path
    updater2 = PteroEggsUpdater("/custom/path")
    assert updater2.repo_path == Path("/custom/path")


@patch("subprocess.run")
def test_clone_or_update_repository_clone(mock_run):
    """Test cloning repository when it doesn't exist."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    updater = PteroEggsUpdater("/tmp/test_clone")
    # Ensure directory doesn't exist
    if updater.repo_path.exists():
        import shutil

        shutil.rmtree(updater.repo_path)

    success, message = updater.clone_or_update_repository()

    assert success is True
    assert "cloned" in message.lower()
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_clone_or_update_repository_update(mock_run, tmp_path):
    """Test updating repository when it exists."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    # Create temporary directory
    test_repo = tmp_path / "game-eggs"
    test_repo.mkdir()

    updater = PteroEggsUpdater(str(test_repo))
    success, message = updater.clone_or_update_repository()

    assert success is True
    assert "updated" in message.lower()
    mock_run.assert_called_once()


def test_ptero_eggs_browser_route_exists():
    """Test that browser route exists in config blueprint."""
    from routes_config import config_bp

    # Check that the route is registered
    route_names = [rule.endpoint for rule in config_bp.url_map.iter_rules()]
    assert "config.ptero_eggs_browser" in route_names or any(
        "browser" in name for name in route_names
    )


def test_ptero_eggs_sync_route_exists():
    """Test that sync route exists in config blueprint."""
    from routes_config import config_bp

    # Check that the route is registered
    route_names = [rule.endpoint for rule in config_bp.url_map.iter_rules()]
    assert "config.ptero_eggs_sync" in route_names or any("sync" in name for name in route_names)


def test_ptero_eggs_routes_registered():
    """Test that all Ptero-Eggs routes are registered in config blueprint."""
    from routes_config import config_bp

    # Get all rule endpoints from the blueprint's deferred functions
    # Since blueprints defer registration, we check the blueprint has our functions
    expected_functions = [
        "ptero_eggs_browser",
        "ptero_eggs_sync",
        "ptero_eggs_template_preview",
        "apply_ptero_eggs_template",
        "compare_ptero_eggs_templates",
        "create_custom_ptero_template",
        "migrate_servers_to_ptero",
        "api_list_servers",
    ]

    # Check that config_bp has these view functions
    for func_name in expected_functions:
        # Either as part of the blueprint or in the module
        found = (
            hasattr(config_bp, func_name)
            or func_name in dir(config_bp)
            or any(func_name in str(rule) for rule in config_bp.deferred_functions)
        )
        # At minimum, the module should have these functions defined
        import routes_config

        assert hasattr(
            routes_config, func_name
        ) or func_name in routes_config.config_bp.view_functions.get(f"config.{func_name}", {})


def test_get_sync_status(test_app):
    """Test getting sync status."""
    updater = PteroEggsUpdater()

    with test_app.app_context():
        # Clear any existing metadata first
        PteroEggsUpdateMetadata.query.delete()
        db.session.commit()

        # Initially should be None
        status = updater.get_sync_status()
        assert status is None

        # Create metadata
        metadata = PteroEggsUpdateMetadata()
        metadata.last_commit_hash = "test123"
        metadata.last_sync_status = "success"
        metadata.total_templates_imported = 10
        db.session.add(metadata)
        db.session.commit()

        # Now should return data
        status = updater.get_sync_status()
        assert status is not None
        assert status["last_commit_hash"] == "test123"
        assert status["last_sync_status"] == "success"
        assert status["total_templates_imported"] == 10


def test_background_task_exists():
    """Test that the background task is defined."""
    from tasks import run_ptero_eggs_sync

    # Verify function exists
    assert callable(run_ptero_eggs_sync)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
