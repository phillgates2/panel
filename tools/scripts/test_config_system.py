#!/usr/bin/env python3
"""
Simple test script for configuration management functionality
"""

import sys


def run_config_system_checks():
    print("🧪 Testing Configuration Management System...")
    # Minimal health checks (kept lightweight for local scripts)
    try:
        # Mock the app module to avoid database connection issues when running standalone
        import types

        _orig_app = sys.modules.get("app")
        _orig_app_db = sys.modules.get("app.db")
        mock_app = types.ModuleType("app")
        mock_db = types.ModuleType("db")
        mock_db.Model = object
        mock_db.Column = lambda *args, **kwargs: None
        mock_db.Integer = str
        mock_db.String = str
        mock_db.Text = str
        mock_db.DateTime = str
        mock_db.Boolean = str
        mock_db.ForeignKey = str
        mock_db.relationship = lambda *args, **kwargs: None
        mock_db.backref = lambda *args, **kwargs: None
        mock_db.session = types.ModuleType("session")
        mock_db.session.add = lambda x: None
        mock_db.session.commit = lambda: None
        mock_db.session.query = lambda x: None
        mock_app.db = mock_db

        sys.modules["app"] = mock_app
        sys.modules["app.db"] = mock_db

        from config_manager import ConfigManager  # noqa: F401

        print("  ✅ ConfigManager import ok")

    finally:
        # restore originals
        if _orig_app is not None:
            sys.modules["app"] = _orig_app
        else:
            sys.modules.pop("app", None)
        if _orig_app_db is not None:
            sys.modules["app.db"] = _orig_app_db
        else:
            sys.modules.pop("app.db", None)


if __name__ == "__main__":
    run_config_system_checks()
