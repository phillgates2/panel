# Game Server Setup Guide

## Overview
This guide explains how to add new games to the panel, configure game server files, and manage server templates.

---

## Adding a New Game Type

### 1. Create a Configuration Template

Configuration templates define the default settings for a game type. You can create them via Python:

```python
from app import app, db, User
from config_manager import ConfigTemplate
import json

with app.app_context():
    admin_user = User.query.filter_by(role='system_admin').first()
    
    template = ConfigTemplate(
        name="Counter-Strike: Source Server",
        description="Standard CS:S dedicated server",
        game_type="css",  # Unique identifier
        template_data=json.dumps({
            "server_cfg": """// CS:S Server Configuration
hostname "My CS:S Server"
rcon_password "changeme"
sv_password ""
sv_maxplayers 32
sv_cheats 0
mp_friendlyfire 0
mp_autoteambalance 1
mp_limitteams 2
""",
            "mapcycle": """de_dust2
de_inferno
de_nuke
de_train
cs_office
cs_italy
""",
            "startup_script": """#!/bin/bash
cd /opt/servers/css
./srcds_run -game cstrike -console -usercon +map de_dust2 +maxplayers 32 +exec server.cfg
""",
        }),
        is_default=True,
        created_by=admin_user.id,
    )
    
    db.session.add(template)
    db.session.commit()
    print(f"Created template: {template.name}")
```

### 2. Update Server Creation Form

The server creation form in `templates/server_create.html` needs the new game type in the dropdown:

```html
<select id="game_type" name="game_type" required>
    <option value="">Select Game Type</option>
    <option value="etlegacy">ET:Legacy</option>
    <option value="css">Counter-Strike: Source</option>
    <option value="csgo">Counter-Strike: Global Offensive</option>
    <option value="tf2">Team Fortress 2</option>
    <option value="custom">Custom/Other</option>
</select>
```

### 3. Add Game-Specific Logic (Optional)

If your game needs special handling, update the `admin_create_server()` function in `app.py`:

```python
# Around line 1530 in app.py
game_type = request.form.get("game_type", "etlegacy")

# Load template based on game type
template = ConfigTemplate.query.filter_by(
    game_type=game_type, 
    is_default=True
).first()

if template:
    template_data = json.loads(template.template_data)
    variables_json = json.dumps(template_data)
    raw_config = template_data.get("server_cfg", "")
else:
    # Fallback for unknown game types
    variables_json = json.dumps({"game_type": game_type})
    raw_config = f"# {game_type} server configuration\n"
```

---

## Uploading Server Files

### Method 1: Manual File Upload via Shell

1. **Connect to your server**:
   ```bash
   ssh user@your-server-ip
   ```

2. **Create game directory**:
   ```bash
   mkdir -p /opt/servers/etlegacy
   cd /opt/servers/etlegacy
   ```

3. **Upload files via SCP**:
   ```bash
   # From your local machine:
   scp -r /path/to/etlegacy/* user@server:/opt/servers/etlegacy/
   ```

4. **Extract if needed**:
   ```bash
   tar -xzf etlegacy-*.tar.gz
   chmod +x etlded
   ```

### Method 2: Download Directly on Server

```bash
cd /opt/servers/etlegacy
wget https://www.etlegacy.com/download/file/111 -O etlegacy.tar.gz
tar -xzf etlegacy.tar.gz
chmod +x etlded
```

### Method 3: Using Panel's Upload Feature (Future)

The panel will support file uploads through the web interface. For now, use Methods 1 or 2.

---

## Server File Structure

### ET:Legacy Example
```
/opt/servers/etlegacy/
├── etlded                    # Main executable
├── etl/                      # Mod files
│   ├── pak0.pk3
│   ├── pak1.pk3
│   └── pak2.pk3
├── etmain/                   # Game files
│   ├── pak0.pk3
│   ├── pak1.pk3
│   └── pak2.pk3
├── legacy/                   # Legacy mod
│   └── *.pk3 files
└── configs/
    ├── server.cfg
    ├── campaign.cfg
    └── mapconfigs/
```

### Counter-Strike: Source Example
```
/opt/servers/css/
├── srcds_run                 # Startup script
├── srcds_linux               # Binary
├── bin/                      # Libraries
├── cstrike/                  # Game directory
│   ├── addons/
│   │   └── sourcemod/
│   ├── cfg/
│   │   ├── server.cfg
│   │   └── mapcycle.txt
│   ├── maps/
│   └── materials/
└── platform/
```

---

## Modifying Game List

### Add Games to Server Creation Dropdown

Edit `app.py` around line 1535:

```python
# Define available game types
game_types = [
    {"id": "etlegacy", "name": "ET:Legacy", "icon": "🎮"},
    {"id": "css", "name": "Counter-Strike: Source", "icon": "🔫"},
    {"id": "csgo", "name": "CS:GO", "icon": "💣"},
    {"id": "tf2", "name": "Team Fortress 2", "icon": "🎩"},
    {"id": "l4d2", "name": "Left 4 Dead 2", "icon": "🧟"},
    {"id": "minecraft", "name": "Minecraft", "icon": "⛏️"},
    {"id": "valheim", "name": "Valheim", "icon": "⚔️"},
    {"id": "rust", "name": "Rust", "icon": "🦀"},
    {"id": "ark", "name": "ARK: Survival Evolved", "icon": "🦖"},
    {"id": "custom", "name": "Custom/Other", "icon": "⚙️"},
]
```

Then pass it to the template:

```python
return render_template(
    "server_create.html",
    game_types=game_types,
    # ... other variables
)
```

Update `templates/server_create.html`:

```html
<select id="game_type" name="game_type" required>
    <option value="">Select Game Type</option>
    {% for game in game_types %}
    <option value="{{ game.id }}">{{ game.icon }} {{ game.name }}</option>
    {% endfor %}
</select>
```

---

## Creating Templates Programmatically

### Add Multiple Game Templates

Create a script `scripts/add_game_templates.py`:

```python
#!/usr/bin/env python3
"""Add game server templates to the panel."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app, db, User
from config_manager import ConfigTemplate
import json

TEMPLATES = {
    "css": {
        "name": "Counter-Strike: Source Standard",
        "description": "Standard CS:S server with common settings",
        "template_data": {
            "server_cfg": """hostname "My CS:S Server"
rcon_password "changeme"
sv_password ""
sv_maxplayers 32
mp_friendlyfire 0
mp_autoteambalance 1
""",
            "mapcycle": "de_dust2\nde_inferno\nde_nuke\n",
        },
    },
    "minecraft": {
        "name": "Minecraft Vanilla Server",
        "description": "Standard Minecraft Java Edition server",
        "template_data": {
            "server_properties": """server-port=25565
max-players=20
difficulty=normal
gamemode=survival
pvp=true
spawn-protection=16
""",
            "startup_script": """#!/bin/bash
java -Xmx2G -Xms2G -jar server.jar nogui
""",
        },
    },
}

def main():
    with app.app_context():
        admin = User.query.filter_by(role='system_admin').first()
        if not admin:
            print("No admin user found!")
            return
        
        for game_id, data in TEMPLATES.items():
            existing = ConfigTemplate.query.filter_by(name=data["name"]).first()
            if existing:
                print(f"Template '{data['name']}' already exists, skipping")
                continue
            
            template = ConfigTemplate(
                name=data["name"],
                description=data["description"],
                game_type=game_id,
                template_data=json.dumps(data["template_data"]),
                is_default=True,
                created_by=admin.id,
            )
            db.session.add(template)
            print(f"✓ Created template: {data['name']}")
        
        db.session.commit()
        print("\n✅ Templates created successfully!")

if __name__ == "__main__":
    main()
```

Run it:
```bash
python scripts/add_game_templates.py
```

---

## Managing Server Files After Creation

### Accessing Server Files

1. **Via SSH**:
   ```bash
   ssh user@server
   cd /opt/servers/your-server-name
   ```

2. **Via SFTP** (FileZilla, WinSCP, etc.):
   - Host: your-server-ip
   - Port: 22
   - Navigate to `/opt/servers/`

3. **Via Panel RCON** (for config changes):
   - Go to RCON Console in panel
   - Use commands like `rcon set sv_hostname "New Name"`

### Updating Configuration Files

The panel stores configs in the database. To update:

1. Go to **Servers** → **Your Server** → **Edit**
2. Modify the **Configuration** field
3. Click **Save**
4. Restart the server for changes to take effect

---

## Common Game Server Ports

| Game                | Default Port | Protocol |
|---------------------|--------------|----------|
| ET:Legacy           | 27960        | UDP      |
| CS:Source           | 27015        | UDP      |
| CS:GO               | 27015        | UDP      |
| Team Fortress 2     | 27015        | UDP      |
| Minecraft           | 25565        | TCP      |
| Rust                | 28015        | UDP      |
| ARK                 | 7777         | UDP      |
| Valheim             | 2456         | UDP      |

Make sure to open these ports in your firewall!

---

## Troubleshooting

### Server Won't Start

1. **Check file permissions**:
   ```bash
   chmod +x /opt/servers/etlegacy/etlded
   ```

2. **Check for missing libraries**:
   ```bash
   ldd /opt/servers/etlegacy/etlded
   ```

3. **Check server logs**:
   ```bash
   tail -f /opt/servers/etlegacy/etconsole.log
   ```

### Files Not Found

Ensure `DOWNLOAD_DIR` in your config points to the correct location:
```python
# In config.py or .env
DOWNLOAD_DIR=/opt/servers
```

### Permission Denied

Run panel with appropriate permissions or use sudo for server operations:
```bash
sudo chown -R panel-user:panel-user /opt/servers
```

---

## Additional Resources

- [ET:Legacy Downloads](https://www.etlegacy.com/download)
- [SteamCMD Guide](https://developer.valvesoftware.com/wiki/SteamCMD) (for Source games)
- [Minecraft Server Setup](https://www.minecraft.net/en-us/download/server)

---

**Next Steps**: 
- Create your first server via the panel
- Upload game files to the server
- Configure and start your server
- Monitor via the panel dashboard
