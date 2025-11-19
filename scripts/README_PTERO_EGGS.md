# Ptero-Eggs Import Script

This directory contains a script to import game server templates from the [Ptero-Eggs](https://github.com/Ptero-Eggs/game-eggs) repository.

## Overview

The `import_ptero_eggs.py` script parses egg JSON files from the Ptero-Eggs repository and converts them to panel's `ConfigTemplate` format, making 240+ game server templates available in your panel.

## Quick Start

### 1. Clone Ptero-Eggs Repository

```bash
git clone https://github.com/Ptero-Eggs/game-eggs.git /tmp/game-eggs
```

### 2. Import All Templates

```bash
cd ~/panel
source venv/bin/activate
python3 scripts/import_ptero_eggs.py import /tmp/game-eggs
```

This will:
- Parse all 240+ egg JSON files
- Extract configuration, variables, and startup commands
- Create ConfigTemplate entries in the database
- Skip any templates that already exist

### 3. List Imported Templates

```bash
python3 scripts/import_ptero_eggs.py list
```

## Supported Games

The import includes templates for popular games such as:

- **Survival**: ARK, Rust, Valheim, Palworld, 7 Days to Die, Conan Exiles
- **FPS**: Counter-Strike (1.6, Source, 2), Team Fortress 2, Insurgency Sandstorm
- **Sandbox**: Minecraft (multiple variants), Terraria, Satisfactory
- **Racing**: Assetto Corsa, BeamNG, TrackMania
- **Strategy**: OpenRA, Factorio, RimWorld
- **MMO**: FiveM, alt:V, RageMP
- And 200+ more!

## Template Structure

Each imported template contains:

```json
{
  "startup_command": "Server startup command with variables",
  "stop_command": "Graceful shutdown command",
  "docker_images": {
    "SteamCMD_Debian": "ghcr.io/ptero-eggs/steamcmd:debian"
  },
  "variables": {
    "SERVER_NAME": {
      "name": "Server Name",
      "description": "The display name of your server",
      "default": "My Game Server",
      "user_viewable": true,
      "user_editable": true,
      "rules": "required|string|max:64"
    }
  },
  "installation": {
    "script_summary": "Container: ghcr.io/ptero-eggs/installers:debian",
    "entrypoint": "bash"
  },
  "features": ["steam_disk_space"],
  "egg_metadata": {
    "source": "Ptero-Eggs",
    "author": "Ptero-Eggs Community",
    "original_name": "Palworld",
    "exported_at": "2024-07-15T18:52:08+02:00"
  }
}
```

## Commands

### Import Templates

```bash
# Import from default location (/tmp/game-eggs)
python3 scripts/import_ptero_eggs.py import

# Import from custom location
python3 scripts/import_ptero_eggs.py import /path/to/game-eggs
```

### List Templates

```bash
# Show all imported Ptero-Eggs templates
python3 scripts/import_ptero_eggs.py list
```

### Clear Templates

```bash
# Remove all Ptero-Eggs templates (prompts for confirmation)
python3 scripts/import_ptero_eggs.py clear
```

## Template Access

After importing, templates are available through:

1. **Database**: Query the `config_template` table
2. **Python API**: `ConfigTemplate.query.filter_by(game_type='palworld').first()`
3. **Web UI**: Templates can be listed and used via the panel's web interface

## Example: Using a Template

```python
from app import app, db
from config_manager import ConfigTemplate
import json

with app.app_context():
    # Find a template
    template = ConfigTemplate.query.filter_by(name='Palworld (Ptero-Eggs)').first()
    
    if template:
        # Load configuration
        config = json.loads(template.template_data)
        
        # Access variables
        server_name_var = config['variables']['SERVER_NAME']
        print(f"Default server name: {server_name_var['default']}")
        
        # Access startup command
        print(f"Startup: {config['startup_command']}")
```

## Updating Existing Servers

To update existing servers with egg configurations:

```python
from app import app, db, Server
from config_manager import ConfigTemplate
import json

with app.app_context():
    # Get a server
    server = Server.query.filter_by(name='My Palworld Server').first()
    
    # Get the template
    template = ConfigTemplate.query.filter_by(name='Palworld (Ptero-Eggs)').first()
    
    if server and template:
        config = json.loads(template.template_data)
        
        # Update server configuration
        server.game_type = template.game_type
        # Apply other configuration as needed
        
        db.session.commit()
```

## Troubleshooting

### No admin user found

```bash
# Create an admin user first
python3 scripts/create_admin.py
```

### Directory not found

```bash
# Make sure you've cloned the repository
git clone https://github.com/Ptero-Eggs/game-eggs.git /tmp/game-eggs
```

### Import errors

Check the error message for specific files. Some eggs may have invalid JSON or missing fields. The importer will skip these and continue with the rest.

## Integration with Existing System

The imported templates work seamlessly with the existing panel infrastructure:

- **ConfigTemplate model**: Standard database model
- **manage_game_templates.py**: Can be used alongside the Ptero-Eggs importer
- **Version control**: Templates can be versioned using `ConfigVersion`
- **Deployment**: Templates can be deployed using `ConfigDeployment`

## Source

Templates are imported from: https://github.com/Ptero-Eggs/game-eggs

This repository is maintained by the Pterodactyl community and contains high-quality, tested configurations for game servers.

## License

The panel code is licensed per the repository license. Ptero-Eggs templates are licensed under their respective licenses in the Ptero-Eggs repository.
