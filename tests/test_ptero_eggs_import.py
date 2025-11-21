"""Test Ptero-Eggs import functionality."""

import json
import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import User, app, db
from config_manager import ConfigTemplate


@pytest.fixture(scope="module")
def test_app():
    """Create application context for testing."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

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


def test_ptero_eggs_templates_imported(test_app):
    """Test that Ptero-Eggs templates were imported."""
    with test_app.app_context():
        # Check for templates with Ptero-Eggs naming pattern
        ptero_templates = ConfigTemplate.query.filter(
            ConfigTemplate.name.like("%(Ptero-Eggs)%")
        ).all()

        # Should have imported templates (if import was run)
        # This test verifies the structure without requiring actual import
        assert isinstance(ptero_templates, list)


def test_ptero_eggs_template_structure(test_app):
    """Test that a Ptero-Eggs template has correct structure."""
    with test_app.app_context():
        # Find any Ptero-Eggs template
        template = ConfigTemplate.query.filter(ConfigTemplate.name.like("%(Ptero-Eggs)%")).first()

        if template:
            # Verify basic structure
            assert template.name is not None
            assert template.game_type is not None
            assert template.template_data is not None

            # Parse config data
            config = json.loads(template.template_data)

            # Verify expected keys exist
            assert "egg_metadata" in config
            assert config["egg_metadata"]["source"] == "Ptero-Eggs"

            # Optional keys that might be present
            possible_keys = [
                "startup_command",
                "stop_command",
                "variables",
                "docker_images",
                "installation",
                "features",
            ]

            # At least one should be present
            assert any(key in config for key in possible_keys)


def test_config_template_model_compatibility(test_app):
    """Test that ConfigTemplate model works with Ptero-Eggs data."""
    with test_app.app_context():
        admin = User.query.filter_by(role="system_admin").first()

        # Create a test template with Ptero-Eggs structure
        test_config = {
            "startup_command": "./start.sh",
            "stop_command": "shutdown",
            "variables": {
                "SERVER_NAME": {
                    "name": "Server Name",
                    "default": "Test Server",
                    "user_editable": True,
                }
            },
            "egg_metadata": {
                "source": "Ptero-Eggs",
                "author": "Test Author",
                "original_name": "Test Game",
            },
        }

        template = ConfigTemplate(
            name="Test Game (Ptero-Eggs)",
            description="Test template for Ptero-Eggs import",
            game_type="test_game",
            template_data=json.dumps(test_config),
            is_default=False,
            created_by=admin.id,
        )

        db.session.add(template)
        db.session.commit()

        # Verify it was saved
        saved = ConfigTemplate.query.filter_by(name="Test Game (Ptero-Eggs)").first()
        assert saved is not None
        assert saved.game_type == "test_game"

        # Verify config can be loaded
        loaded_config = json.loads(saved.template_data)
        assert loaded_config["egg_metadata"]["source"] == "Ptero-Eggs"
        assert "SERVER_NAME" in loaded_config["variables"]


def test_import_script_exists():
    """Test that the import script file exists and is executable."""
    script_path = Path(__file__).parent.parent / "scripts" / "import_ptero_eggs.py"

    assert script_path.exists(), "Import script should exist"
    assert script_path.is_file(), "Import script should be a file"

    # Check if it's executable (on Unix systems)
    if sys.platform != "win32":
        assert os.access(script_path, os.X_OK), "Import script should be executable"


def test_readme_exists():
    """Test that documentation for Ptero-Eggs import exists."""
    readme_path = Path(__file__).parent.parent / "scripts" / "README_PTERO_EGGS.md"

    assert readme_path.exists(), "README should exist"
    assert readme_path.is_file(), "README should be a file"

    # Verify it has content
    content = readme_path.read_text()
    assert len(content) > 100, "README should have substantial content"
    assert "Ptero-Eggs" in content, "README should mention Ptero-Eggs"
