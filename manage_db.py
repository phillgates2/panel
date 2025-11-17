#!/usr/bin/env python3
"""Database migration management script.

Usage:
    python manage_db.py init        # Initialize migrations (first time only)
    python manage_db.py migrate -m "description"  # Create a new migration
    python manage_db.py upgrade     # Apply all pending migrations
    python manage_db.py downgrade   # Rollback one migration
    python manage_db.py current     # Show current revision
    python manage_db.py history     # Show migration history
"""

import sys
import subprocess
from pathlib import Path

def run_alembic(args):
    """Run alembic command with proper environment."""
    cmd = ['alembic'] + args
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'init':
        # Check if migrations/versions exists
        versions_dir = Path('migrations/versions')
        if not versions_dir.exists():
            versions_dir.mkdir(parents=True, exist_ok=True)
            print("✓ Created migrations/versions directory")
        else:
            print("✓ Migrations directory already exists")
        
        # Create initial migration
        print("\nCreating initial migration...")
        return run_alembic(['revision', '--autogenerate', '-m', 'Initial migration'])
    
    elif command == 'migrate':
        # Create new migration
        if '-m' in sys.argv:
            idx = sys.argv.index('-m')
            message = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else 'Auto migration'
        else:
            message = 'Auto migration'
        return run_alembic(['revision', '--autogenerate', '-m', message])
    
    elif command == 'upgrade':
        target = sys.argv[2] if len(sys.argv) > 2 else 'head'
        return run_alembic(['upgrade', target])
    
    elif command == 'downgrade':
        target = sys.argv[2] if len(sys.argv) > 2 else '-1'
        return run_alembic(['downgrade', target])
    
    elif command == 'current':
        return run_alembic(['current'])
    
    elif command == 'history':
        return run_alembic(['history'])
    
    elif command == 'stamp':
        target = sys.argv[2] if len(sys.argv) > 2 else 'head'
        return run_alembic(['stamp', target])
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return 1

if __name__ == '__main__':
    sys.exit(main())
