#!/usr/bin/env python3
"""
App Structure Fix Script
Automatically fixes critical structural issues in the app/ folder
"""

import os
import sys
from pathlib import Path


def create_init_files():
    """Create missing __init__.py files in app/modules."""
    print("Creating missing __init__.py files...")
    
    app_dir = Path("app")
    if not app_dir.exists():
        print(f"Error: {app_dir} directory not found!")
        return False
    
    modules_dir = app_dir / "modules"
    if not modules_dir.exists():
        print(f"Creating {modules_dir}...")
        modules_dir.mkdir(parents=True, exist_ok=True)
    
    created_files = []
    
    # Create __init__.py in modules directory
    modules_init = modules_dir / "__init__.py"
    if not modules_init.exists():
        modules_init.write_text('"""App modules package."""\n')
        created_files.append(str(modules_init))
        print(f"? Created: {modules_init}")
    
    # Find all subdirectories and create __init__.py
    for dirpath, dirnames, filenames in os.walk(modules_dir):
        dir_path = Path(dirpath)
        init_file = dir_path / "__init__.py"
        
        if not init_file.exists():
            # Create appropriate __init__.py content based on directory name
            module_name = dir_path.name
            content = f'"""{module_name.replace("_", " ").title()} module."""\n'
            
            init_file.write_text(content)
            created_files.append(str(init_file))
            print(f"? Created: {init_file}")
    
    if created_files:
        print(f"\n? Created {len(created_files)} __init__.py files")
        return True
    else:
        print("\n? All __init__.py files already exist")
        return True


def move_demo_code():
    """Move demo code to examples/ directory."""
    print("\nMoving demo code...")
    
    demo_file = Path("app/advanced_features.py")
    
    if not demo_file.exists():
        print(f"? Demo file not found (already moved?): {demo_file}")
        return True
    
    examples_dir = Path("examples")
    examples_dir.mkdir(exist_ok=True)
    
    target = examples_dir / "demo_features.py"
    
    # Add warning comment to moved file
    content = demo_file.read_text()
    warning = '''"""
WARNING: This is demo/showcase code moved from app/advanced_features.py
This code demonstrates features but has import errors and should not be used in production.
Many of the imported modules don't exist at the specified paths.
"""

'''
    
    target.write_text(warning + content)
    
    # Remove original file
    demo_file.unlink()
    
    print(f"? Moved: {demo_file} ? {target}")
    print(f"? Demo code moved to examples/")
    
    return True


def create_proper_init_py():
    """Create a proper app/__init__.py without app instance."""
    print("\nFixing app/__init__.py...")
    
    init_file = Path("app/__init__.py")
    
    if not init_file.exists():
        print(f"Error: {init_file} not found!")
        return False
    
    # Backup original
    backup = init_file.with_suffix(".py.bak")
    init_file.rename(backup)
    print(f"? Backed up: {init_file} ? {backup}")
    
    # Create new __init__.py without global app instance
    new_content = '''"""
App Package

This package contains the core application components.
Use create_app() factory function to create Flask app instances.
"""

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

# Initialize extensions (but don't bind to app yet)
db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name="default"):
    """Application factory function.
    
    Creates and configures a Flask application instance.
    
    Args:
        config_name: Configuration name or object
        
    Returns:
        Configured Flask application
    """
    import os
    from pathlib import Path
    
    # Determine template and static directories
    root_dir = Path(__file__).parent.parent
    template_dir = root_dir / "templates"
    static_dir = root_dir / "static"
    
    # Create Flask app
    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )
    
    # Load configuration
    from config import config
    if isinstance(config_name, str):
        app.config.from_object(config)
    else:
        # Assume it's a config object
        for key, value in vars(config_name).items():
            if not key.startswith("_"):
                app.config[key.upper()] = value
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = "main.login"
    login_manager.login_message = "Please log in to access this page."
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID."""
        from src.panel.models import User
        return db.session.get(User, int(user_id))
    
    # Register blueprints
    register_blueprints(app)
    
    # Register context processors
    register_context_processors(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def register_blueprints(app):
    """Register application blueprints."""
    try:
        from src.panel.main_bp import main_bp
        app.register_blueprint(main_bp)
    except ImportError:
        pass
    
    try:
        from src.panel.api_bp import api_bp
        app.register_blueprint(api_bp, url_prefix="/api")
    except ImportError:
        pass
    
    try:
        from src.panel.admin_bp import admin_bp
        app.register_blueprint(admin_bp)
    except ImportError:
        pass
    
    try:
        from src.panel.chat_bp import chat_bp
        app.register_blueprint(chat_bp)
    except ImportError:
        pass
    
    try:
        from src.panel.payment_bp import payment_bp
        app.register_blueprint(payment_bp)
    except ImportError:
        pass


def register_context_processors(app):
    """Register template context processors."""
    try:
        from app.context_processors import inject_user
        app.context_processor(inject_user)
    except ImportError:
        pass


def register_error_handlers(app):
    """Register error handlers."""
    try:
        from app.error_handlers import page_not_found, internal_error
        app.errorhandler(404)(page_not_found)
        app.errorhandler(500)(internal_error)
    except ImportError:
        pass


# Expose key components at package level
__all__ = [
    "create_app",
    "db",
    "login_manager",
]
'''
    
    init_file.write_text(new_content)
    print(f"? Created new: {init_file}")
    print(f"? Fixed app/__init__.py (backup saved)")
    
    return True


def add_missing_error_handlers():
    """Add missing error handlers to error_handlers.py."""
    print("\nEnhancing error handlers...")
    
    error_file = Path("app/error_handlers.py")
    
    if not error_file.exists():
        print(f"Error: {error_file} not found!")
        return False
    
    # Backup original
    backup = error_file.with_suffix(".py.bak")
    content = error_file.read_text()
    error_file.rename(backup)
    print(f"? Backed up: {error_file} ? {backup}")
    
    # Add new error handlers
    enhanced_content = '''import logging
from typing import Tuple

from flask import render_template, jsonify, request

logger = logging.getLogger(__name__)


def wants_json_response():
    """Check if client wants JSON response."""
    return (
        request.accept_mimetypes.best == "application/json"
        or request.path.startswith("/api/")
    )


def bad_request(e) -> Tuple:
    """Handle 400 Bad Request errors."""
    logger.warning(f"400 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Bad Request",
            "message": str(e),
            "status": 400
        }), 400
    
    return render_template("400.html", error=e), 400


def unauthorized(e) -> Tuple:
    """Handle 401 Unauthorized errors."""
    logger.warning(f"401 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication required",
            "status": 401
        }), 401
    
    return render_template("401.html", error=e), 401


def forbidden(e) -> Tuple:
    """Handle 403 Forbidden errors."""
    logger.warning(f"403 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Forbidden",
            "message": "You don't have permission to access this resource",
            "status": 403
        }), 403
    
    return render_template("403.html", error=e), 403


def page_not_found(e) -> Tuple:
    """Handle 404 Not Found errors."""
    logger.warning(f"404 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found",
            "status": 404
        }), 404
    
    return render_template("404.html", error=e), 404


def method_not_allowed(e) -> Tuple:
    """Handle 405 Method Not Allowed errors."""
    logger.warning(f"405 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Method Not Allowed",
            "message": str(e),
            "status": 405
        }), 405
    
    return render_template("405.html", error=e), 405


def too_many_requests(e) -> Tuple:
    """Handle 429 Too Many Requests errors."""
    logger.warning(f"429 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please try again later.",
            "status": 429
        }), 429
    
    return render_template("429.html", error=e), 429


def internal_error(e) -> Tuple:
    """Handle 500 Internal Server Error."""
    logger.error(f"500 error: {e}", exc_info=True)
    
    if wants_json_response():
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status": 500
        }), 500
    
    return render_template("500.html", error=e), 500


def service_unavailable(e) -> Tuple:
    """Handle 503 Service Unavailable errors."""
    logger.error(f"503 error: {e}")
    
    if wants_json_response():
        return jsonify({
            "error": "Service Unavailable",
            "message": "The service is temporarily unavailable",
            "status": 503
        }), 503
    
    return render_template("503.html", error=e), 503


# Export all error handlers
__all__ = [
    "bad_request",
    "unauthorized",
    "forbidden",
    "page_not_found",
    "method_not_allowed",
    "too_many_requests",
    "internal_error",
    "service_unavailable",
]
'''
    
    error_file.write_text(enhanced_content)
    print(f"? Enhanced: {error_file}")
    print(f"? Added error handlers for 400, 401, 403, 405, 429, 503")
    
    return True


def create_summary_report():
    """Create a summary report of changes."""
    print("\n" + "="*60)
    print(" App Structure Fix Summary")
    print("="*60)
    
    report = Path("docs/APP_FIX_SUMMARY.md")
    
    content = f"""# App Structure Fix Summary

## Date: {os.popen('date').read().strip()}

## Changes Made

### 1. Created Missing __init__.py Files
- Added `__init__.py` to `app/modules/` and all subdirectories
- Python can now recognize modules as packages
- Imports will work correctly

### 2. Moved Demo Code
- Moved `app/advanced_features.py` ? `examples/demo_features.py`
- Added warning comment to demo file
- Production code is now cleaner

### 3. Fixed app/__init__.py
- Removed global app instance creation
- Converted to proper factory pattern
- Added blueprint registration helpers
- Backup saved as `app/__init__.py.bak`

### 4. Enhanced Error Handlers
- Added handlers for 400, 401, 403, 405, 429, 503
- Support for both HTML and JSON responses
- Better logging for all errors
- Backup saved as `app/error_handlers.py.bak`

## Next Steps

### Immediate
1. **Test the application**:
   ```bash
   python app.py
   ```

2. **Run tests**:
   ```bash
   pytest tests/
   ```

3. **Check imports**:
   ```bash
   python -c "from app import create_app; app = create_app(); print('? Success')"
   ```

### Short Term
1. Review and merge changes from app/factory.py if needed
2. Update all code that uses `from app import app` to use factory
3. Create error templates (400.html, 401.html, etc.)
4. Add comprehensive tests for error handlers

### Medium Term
1. Refactor extensions.py into smaller modules
2. Standardize all import paths
3. Add type hints to all functions
4. Create module documentation

## Rollback Instructions

If something breaks:

```bash
# Restore app/__init__.py
mv app/__init__.py app/__init__.py.new
mv app/__init__.py.bak app/__init__.py

# Restore error_handlers.py
mv app/error_handlers.py app/error_handlers.py.new
mv app/error_handlers.py.bak app/error_handlers.py

# Move demo code back
mv examples/demo_features.py app/advanced_features.py
```

## Files Modified

- `app/__init__.py` - Rewritten (backup: `.bak`)
- `app/error_handlers.py` - Enhanced (backup: `.bak`)
- `app/advanced_features.py` - Moved to examples/
- `app/modules/**/__init__.py` - Created (new files)

## Verification

Run these commands to verify fixes:

```bash
# Check Python can import modules
python -c "from app.modules import security; print('? Modules importable')"

# Check app factory works
python -c "from app import create_app; app = create_app(); print('? App factory works')"

# Check no circular imports
python -c "import app; print('? No circular imports')"
```

## Support

If you encounter issues:
1. Check the backup files (*.bak)
2. Review this summary
3. Consult `docs/APP_FOLDER_ANALYSIS.md`
4. Run the rollback instructions above
"""
    
    report.parent.mkdir(exist_ok=True)
    report.write_text(content)
    print(f"\n? Created summary report: {report}")
    
    return True


def main():
    """Main execution function."""
    print("="*60)
    print(" App Structure Fixer")
    print("="*60)
    print()
    print("This script will:")
    print("1. Create missing __init__.py files")
    print("2. Move demo code to examples/")
    print("3. Fix app/__init__.py")
    print("4. Enhance error handlers")
    print()
    
    response = input("Continue? [y/N]: ")
    if response.lower() != 'y':
        print("Aborted.")
        return 1
    
    print()
    
    try:
        # Run fixes
        if not create_init_files():
            return 1
        
        if not move_demo_code():
            return 1
        
        if not create_proper_init_py():
            return 1
        
        if not add_missing_error_handlers():
            return 1
        
        if not create_summary_report():
            return 1
        
        print()
        print("="*60)
        print(" ? All fixes completed successfully!")
        print("="*60)
        print()
        print("Next steps:")
        print("1. Review the changes")
        print("2. Test the application: python app.py")
        print("3. Run tests: pytest tests/")
        print("4. Read docs/APP_FIX_SUMMARY.md")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n? Error: {e}")
        print("Please review the error and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
