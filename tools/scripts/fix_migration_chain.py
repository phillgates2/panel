#!/usr/bin/env python3
"""
Fix Migration Chain Script
Repairs broken Alembic migration chains by setting proper down_revision values
"""

import os
import re
from pathlib import Path
from datetime import datetime


def get_migration_files(migrations_dir: Path):
    """Get all migration files sorted by creation date."""
    versions_dir = migrations_dir / "versions"
    if not versions_dir.exists():
        print(f"Error: {versions_dir} does not exist")
        return []
    
    migration_files = []
    for file_path in versions_dir.glob("*.py"):
        if file_path.name == "__init__.py":
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract revision ID
        revision_match = re.search(r'revision\s*=\s*["\']([^"\']+)["\']', content)
        down_revision_match = re.search(r'down_revision\s*=\s*([^#\n]+)', content)
        create_date_match = re.search(r'Create Date:\s*(.+)', content)
        
        if revision_match:
            revision_id = revision_match.group(1)
            down_revision = down_revision_match.group(1).strip() if down_revision_match else "None"
            create_date = create_date_match.group(1).strip() if create_date_match else "Unknown"
            
            migration_files.append({
                'path': file_path,
                'revision': revision_id,
                'down_revision': down_revision,
                'create_date': create_date,
                'filename': file_path.name
            })
    
    # Sort by filename (which often includes timestamp)
    migration_files.sort(key=lambda x: x['filename'])
    
    return migration_files


def detect_issues(migrations):
    """Detect issues in migration chain."""
    issues = []
    
    # Find migrations with None as down_revision (except the first one)
    none_revisions = [m for m in migrations if m['down_revision'] == 'None']
    if len(none_revisions) > 1:
        issues.append({
            'type': 'multiple_roots',
            'message': f"Found {len(none_revisions)} migrations with down_revision=None. Only the first migration should have None.",
            'migrations': none_revisions
        })
    
    # Check for missing down_revisions
    revision_ids = {m['revision'] for m in migrations}
    for migration in migrations:
        down_rev = migration['down_revision'].strip('"\'')
        if down_rev != 'None' and down_rev not in revision_ids:
            issues.append({
                'type': 'missing_down_revision',
                'message': f"Migration {migration['revision']} references non-existent down_revision: {down_rev}",
                'migration': migration
            })
    
    return issues


def fix_migration_chain(migrations, dry_run=True):
    """Fix the migration chain by setting proper down_revision values."""
    if not migrations:
        print("No migrations found!")
        return
    
    print(f"\n{'='*60}")
    print(f"{'DRY RUN MODE' if dry_run else 'FIXING MIGRATIONS'}")
    print(f"{'='*60}\n")
    
    # First migration should have down_revision = None
    first_migration = migrations[0]
    print(f"? First migration: {first_migration['filename']}")
    print(f"  Revision: {first_migration['revision']}")
    print(f"  Down revision: {first_migration['down_revision']}")
    
    # Fix subsequent migrations
    for i in range(1, len(migrations)):
        current = migrations[i]
        previous = migrations[i - 1]
        
        current_down_rev = current['down_revision'].strip('"\'')
        expected_down_rev = previous['revision']
        
        if current_down_rev != expected_down_rev:
            print(f"\n? Issue found in: {current['filename']}")
            print(f"  Current down_revision: {current_down_rev}")
            print(f"  Expected down_revision: {expected_down_rev}")
            
            if not dry_run:
                # Read file content
                with open(current['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace down_revision
                pattern = r'(down_revision\s*=\s*)([^#\n]+)'
                replacement = f'\\1"{expected_down_rev}"'
                new_content = re.sub(pattern, replacement, content)
                
                # Write back
                with open(current['path'], 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"  ? Fixed! Set down_revision to '{expected_down_rev}'")
            else:
                print(f"  ? Would set down_revision to '{expected_down_rev}'")
        else:
            print(f"\n? OK: {current['filename']}")
            print(f"  Down revision: {current_down_rev}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix Alembic migration chain")
    parser.add_argument(
        '--migrations-dir',
        default='migrations',
        help='Path to migrations directory (default: migrations)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Actually fix the migrations (default is dry-run)'
    )
    
    args = parser.parse_args()
    
    migrations_dir = Path(args.migrations_dir)
    
    if not migrations_dir.exists():
        print(f"Error: Migrations directory not found: {migrations_dir}")
        return 1
    
    print("Analyzing migration chain...")
    migrations = get_migration_files(migrations_dir)
    
    if not migrations:
        print("No migration files found!")
        return 1
    
    print(f"Found {len(migrations)} migration files\n")
    
    # Detect issues
    issues = detect_issues(migrations)
    
    if issues:
        print("Issues detected:")
        for issue in issues:
            print(f"\n? {issue['type']}: {issue['message']}")
            if 'migrations' in issue:
                for m in issue['migrations']:
                    print(f"   - {m['filename']} (revision: {m['revision']})")
            elif 'migration' in issue:
                m = issue['migration']
                print(f"   - {m['filename']} (revision: {m['revision']})")
        print()
    
    # Fix chain
    fix_migration_chain(migrations, dry_run=not args.fix)
    
    print(f"\n{'='*60}")
    if not args.fix:
        print("DRY RUN COMPLETE - No changes made")
        print("Run with --fix to apply changes")
    else:
        print("MIGRATION CHAIN FIXED!")
        print("\nNext steps:")
        print("1. Review the changes")
        print("2. Test migrations: flask db upgrade")
        print("3. Commit the fixed migration files")
    print(f"{'='*60}\n")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
