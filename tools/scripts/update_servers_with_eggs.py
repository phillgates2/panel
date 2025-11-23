#!/usr/bin/env python3
"""
Update existing servers with Ptero-Eggs configurations.

This script helps apply Ptero-Eggs templates to existing game servers
in the panel database.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import Server, app, db
from config_manager import ConfigTemplate


def list_servers():
    """List all servers in the database."""
    with app.app_context():
        servers = Server.query.all()

        if not servers:
            print("\n❌ No servers found in database")
            return

        print(f"\n📋 Found {len(servers)} servers:")
        print("=" * 80)
        print(f"{'ID':<5} {'Name':<30} {'Game Type':<20} {'Status'}")
        print("-" * 80)

        for server in servers:
            game_type = getattr(server, "game_type", "N/A")
            status = "Active" if getattr(server, "is_active", True) else "Inactive"
            name = server.name[:27] + "..." if len(server.name) > 30 else server.name
            print(f"{server.id:<5} {name:<30} {game_type:<20} {status}")

        print("=" * 80)


def find_matching_templates(game_type):
    """Find Ptero-Eggs templates matching a game type."""
    with app.app_context():
        # Try exact match first
        templates = (
            ConfigTemplate.query.filter_by(game_type=game_type)
            .filter(ConfigTemplate.name.like("%(Ptero-Eggs)%"))
            .all()
        )

        if not templates:
            # Try partial match
            templates = (
                ConfigTemplate.query.filter(ConfigTemplate.game_type.like(f"%{game_type}%"))
                .filter(ConfigTemplate.name.like("%(Ptero-Eggs)%"))
                .all()
            )

        return templates


def update_server(server_id, template_id, dry_run=True):
    """Update a server with a Ptero-Eggs template configuration.

    Args:
        server_id: ID of the server to update
        template_id: ID of the ConfigTemplate to apply
        dry_run: If True, show what would be updated without making changes
    """
    with app.app_context():
        server = db.session.get(Server, server_id)
        if not server:
            print(f"❌ Server with ID {server_id} not found")
            return False

        template = db.session.get(ConfigTemplate, template_id)
        if not template:
            print(f"❌ Template with ID {template_id} not found")
            return False

        print(f"\n{'DRY RUN - ' if dry_run else ''}Updating server:")
        print(f"  Server: {server.name} (ID: {server.id})")
        print(f"  Template: {template.name} (ID: {template.id})")
        print(f"  Game Type: {template.game_type}")
        print()

        # Parse template configuration
        config = json.loads(template.template_data)

        # Display what would be updated
        updates = []

        if hasattr(server, "game_type"):
            if server.game_type != template.game_type:
                updates.append(f"  game_type: {server.game_type} → {template.game_type}")

        if "startup_command" in config:
            updates.append(f"  startup_command: {config['startup_command'][:60]}...")

        if "stop_command" in config:
            updates.append(f"  stop_command: {config['stop_command']}")

        if "variables" in config:
            updates.append(f"  variables: {len(config['variables'])} configuration variables")

        if updates:
            print("Changes to be applied:")
            for update in updates:
                print(update)
        else:
            print("No changes needed (server already matches template)")

        if not dry_run:
            # Apply updates
            if hasattr(server, "game_type"):
                server.game_type = template.game_type

            # Store template reference if server has a config field
            if hasattr(server, "config"):
                if server.config:
                    try:
                        server_config = json.loads(server.config)
                    except:
                        server_config = {}
                else:
                    server_config = {}

                server_config["ptero_egg_template_id"] = template.id
                server_config["ptero_egg_applied_at"] = str(db.func.current_timestamp())

                # Merge egg configuration
                for key in ["startup_command", "stop_command", "variables", "docker_images"]:
                    if key in config:
                        server_config[key] = config[key]

                server.config = json.dumps(server_config, indent=2)

            db.session.commit()
            print("\n✅ Server updated successfully!")
        else:
            print("\n⚠️  Dry run - no changes made. Use --apply to make actual changes.")

        return True


def match_servers_to_templates():
    """Find and display potential template matches for all servers."""
    with app.app_context():
        servers = Server.query.all()

        if not servers:
            print("\n❌ No servers found")
            return

        print(f"\n🔍 Searching for template matches for {len(servers)} servers...")
        print("=" * 80)

        matches = []
        for server in servers:
            game_type = getattr(server, "game_type", None)
            if not game_type:
                continue

            templates = find_matching_templates(game_type)
            if templates:
                matches.append((server, templates))

        if not matches:
            print("\n❌ No matching templates found for any servers")
            return

        print(f"\n✅ Found matches for {len(matches)} servers:")
        print()

        for server, templates in matches:
            print(f"Server: {server.name} (ID: {server.id}, Type: {server.game_type})")
            print(f"  Matching templates:")
            for template in templates:
                print(f"    - {template.name} (ID: {template.id})")
            print()

        print("=" * 80)
        print("\nTo update a server, run:")
        print("  python3 scripts/update_servers_with_eggs.py update <server_id> <template_id>")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Update servers with Ptero-Eggs templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all servers
  %(prog)s list

  # Find matching templates for servers
  %(prog)s match

  # Preview updating a server (dry run)
  %(prog)s update 1 42

  # Actually update a server
  %(prog)s update 1 42 --apply
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    subparsers.add_parser("list", help="List all servers")

    # Match command
    subparsers.add_parser("match", help="Find template matches for servers")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update a server with a template")
    update_parser.add_argument("server_id", type=int, help="Server ID to update")
    update_parser.add_argument("template_id", type=int, help="Template ID to apply")
    update_parser.add_argument(
        "--apply", action="store_true", help="Actually apply changes (default is dry run)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "list":
        list_servers()
    elif args.command == "match":
        match_servers_to_templates()
    elif args.command == "update":
        dry_run = not args.apply
        update_server(args.server_id, args.template_id, dry_run=dry_run)


if __name__ == "__main__":
    main()
