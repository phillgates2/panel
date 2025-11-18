"""
Flask-Migrate initialization for database migrations
Run: flask db init (one time setup)
     flask db migrate -m "description" (create migration)
     flask db upgrade (apply migration)
"""

from flask_migrate import Migrate

# Import the app and db from your main application
from app import app, db

# Initialize Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    print("Flask-Migrate initialized")
    print("Available commands:")
    print("  flask db init         - Initialize migrations directory")
    print("  flask db migrate -m 'message' - Create new migration")
    print("  flask db upgrade      - Apply migrations")
    print("  flask db downgrade    - Rollback migration")
    print("  flask db history      - Show migration history")
    print("  flask db current      - Show current migration")
