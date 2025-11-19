#!/usr/bin/env python3
"""
Import Ptero-Eggs game server templates into the panel.

This script parses egg JSON files from the Ptero-Eggs repository
and converts them to panel ConfigTemplate format.
"""

import sys
import os
import json
import re
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app, db, User
from config_manager import ConfigTemplate


def clean_game_type(name):
    """Convert egg name to a clean game_type identifier."""
    # Remove special characters and convert to lowercase
    clean = re.sub(r'[^\w\s-]', '', name.lower())
    # Replace spaces and dashes with underscores
    clean = re.sub(r'[-\s]+', '_', clean)
    # Remove leading/trailing underscores
    clean = clean.strip('_')
    return clean


def extract_config_from_egg(egg_data):
    """Extract configuration data from a Ptero-Eggs egg file."""
    config = {}
    
    # Add startup command
    if 'startup' in egg_data:
        config['startup_command'] = egg_data['startup']
    
    # Add stop command
    if 'config' in egg_data and 'stop' in egg_data['config']:
        config['stop_command'] = egg_data['config']['stop']
    
    # Add Docker image
    if 'docker_images' in egg_data:
        config['docker_images'] = egg_data['docker_images']
    
    # Extract variables and their defaults
    if 'variables' in egg_data:
        config['variables'] = {}
        for var in egg_data['variables']:
            var_name = var.get('env_variable', var.get('name', ''))
            if var_name:
                config['variables'][var_name] = {
                    'name': var.get('name', var_name),
                    'description': var.get('description', ''),
                    'default': var.get('default_value', ''),
                    'user_viewable': var.get('user_viewable', True),
                    'user_editable': var.get('user_editable', True),
                    'rules': var.get('rules', ''),
                }
    
    # Add installation script reference
    if 'scripts' in egg_data and 'installation' in egg_data['scripts']:
        installation = egg_data['scripts']['installation']
        config['installation'] = {
            'script_summary': f"Container: {installation.get('container', 'N/A')}",
            'entrypoint': installation.get('entrypoint', 'bash'),
        }
    
    # Add features
    if 'features' in egg_data:
        config['features'] = egg_data['features']
    
    return config


def import_egg_file(egg_path, admin_user_id):
    """Import a single egg file as a ConfigTemplate.
    
    Returns:
        'success': Template was imported
        'skip': Template already exists
        'error': An error occurred
    """
    try:
        with open(egg_path, 'r', encoding='utf-8') as f:
            egg_data = json.load(f)
        
        # Extract metadata
        name = egg_data.get('name', egg_path.stem)
        description = egg_data.get('description', '')
        author = egg_data.get('author', 'Ptero-Eggs Community')
        
        # Create game_type from name
        game_type = clean_game_type(name)
        
        # Extract config
        config_dict = extract_config_from_egg(egg_data)
        
        # Add metadata
        config_dict['egg_metadata'] = {
            'source': 'Ptero-Eggs',
            'author': author,
            'original_name': name,
            'exported_at': egg_data.get('exported_at', 'unknown'),
        }
        
        # Check if template already exists
        template_name = f"{name} (Ptero-Eggs)"
        existing = ConfigTemplate.query.filter_by(name=template_name).first()
        
        if existing:
            print(f"⚠️  Template '{template_name}' already exists (ID: {existing.id}), skipping")
            return 'skip'
        
        # Create new template
        template = ConfigTemplate(
            name=template_name,
            description=f"{description}\n\nSource: Ptero-Eggs\nAuthor: {author}",
            game_type=game_type,
            template_data=json.dumps(config_dict, indent=2),
            is_default=False,
            created_by=admin_user_id,
        )
        
        db.session.add(template)
        return 'success'
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON in {egg_path}: {e}")
        return 'error'
    except Exception as e:
        print(f"❌ Error importing {egg_path}: {e}")
        return 'error'


def import_all_eggs(eggs_dir):
    """Import all egg files from the Ptero-Eggs directory."""
    eggs_path = Path(eggs_dir)
    
    if not eggs_path.exists():
        print(f"❌ Directory not found: {eggs_dir}")
        print(f"Please clone the Ptero-Eggs repository first:")
        print(f"  git clone https://github.com/Ptero-Eggs/game-eggs.git /tmp/game-eggs")
        return
    
    # Find all egg JSON files
    egg_files = list(eggs_path.rglob('egg-*.json'))
    
    if not egg_files:
        print(f"❌ No egg files found in {eggs_dir}")
        return
    
    print(f"\n📦 Found {len(egg_files)} egg files in {eggs_dir}")
    print("=" * 80)
    
    with app.app_context():
        # Get admin user
        admin = User.query.filter_by(role='system_admin').first()
        if not admin:
            print("❌ No system admin user found!")
            print("Please create an admin user first.")
            return
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for egg_file in sorted(egg_files):
            relative_path = egg_file.relative_to(eggs_path)
            print(f"\n📄 Processing: {relative_path}")
            
            result = import_egg_file(egg_file, admin.id)
            
            if result == 'success':
                success_count += 1
                print(f"✅ Imported successfully")
            elif result == 'skip':
                skip_count += 1
            elif result == 'error':
                error_count += 1
        
        # Commit all changes
        if success_count > 0:
            try:
                db.session.commit()
                print("\n" + "=" * 80)
                print(f"✅ Successfully imported {success_count} templates")
                if skip_count > 0:
                    print(f"⚠️  Skipped {skip_count} existing templates")
                if error_count > 0:
                    print(f"❌ Failed to import {error_count} templates")
                print(f"📊 Total processed: {len(egg_files)}")
                print("=" * 80)
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Error committing to database: {e}")
        else:
            print("\n⚠️  No new templates to import")


def list_imported_eggs():
    """List all imported Ptero-Eggs templates."""
    with app.app_context():
        templates = ConfigTemplate.query.filter(
            ConfigTemplate.name.like('%(Ptero-Eggs)%')
        ).all()
        
        if not templates:
            print("\n❌ No Ptero-Eggs templates found in database")
            return
        
        print(f"\n📋 Found {len(templates)} Ptero-Eggs templates:")
        print("=" * 80)
        print(f"{'ID':<5} {'Game Type':<20} {'Name':<50}")
        print("-" * 80)
        
        for t in templates:
            # Truncate name if too long
            display_name = t.name[:47] + '...' if len(t.name) > 50 else t.name
            print(f"{t.id:<5} {t.game_type:<20} {display_name}")
        
        print("=" * 80)


def clear_ptero_eggs():
    """Remove all Ptero-Eggs templates from database."""
    with app.app_context():
        templates = ConfigTemplate.query.filter(
            ConfigTemplate.name.like('%(Ptero-Eggs)%')
        ).all()
        
        if not templates:
            print("\n❌ No Ptero-Eggs templates found to remove")
            return
        
        count = len(templates)
        print(f"\n⚠️  Found {count} Ptero-Eggs templates to remove")
        
        confirm = input("Are you sure you want to remove them? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Cancelled")
            return
        
        for template in templates:
            db.session.delete(template)
        
        db.session.commit()
        print(f"✅ Removed {count} Ptero-Eggs templates")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Import Ptero-Eggs game server templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all eggs from default location
  %(prog)s import /tmp/game-eggs
  
  # List imported templates
  %(prog)s list
  
  # Clear all Ptero-Eggs templates
  %(prog)s clear
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import egg files')
    import_parser.add_argument(
        'eggs_dir',
        nargs='?',
        default='/tmp/game-eggs',
        help='Path to Ptero-Eggs repository directory (default: /tmp/game-eggs)'
    )
    
    # List command
    subparsers.add_parser('list', help='List imported Ptero-Eggs templates')
    
    # Clear command
    subparsers.add_parser('clear', help='Remove all Ptero-Eggs templates')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'import':
        import_all_eggs(args.eggs_dir)
    elif args.command == 'list':
        list_imported_eggs()
    elif args.command == 'clear':
        clear_ptero_eggs()


if __name__ == '__main__':
    main()
