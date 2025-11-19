#!/usr/bin/env python3
"""
Game Template Manager
Add, list, and manage game server templates for the panel.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app, db, User
from config_manager import ConfigTemplate
import json

def list_templates():
    """List all existing templates."""
    with app.app_context():
        templates = ConfigTemplate.query.all()
        if not templates:
            print("No templates found.")
            return
        
        print(f"\n{'ID':<5} {'Game Type':<15} {'Name':<40} {'Default'}")
        print("-" * 80)
        for t in templates:
            print(f"{t.id:<5} {t.game_type:<15} {t.name:<40} {'Yes' if t.is_default else 'No'}")
        print()

def add_template(game_type, name, description, config_dict, is_default=True):
    """Add a new template."""
    with app.app_context():
        admin = User.query.filter_by(role='system_admin').first()
        if not admin:
            print("❌ No admin user found!")
            return False
        
        existing = ConfigTemplate.query.filter_by(name=name).first()
        if existing:
            print(f"❌ Template '{name}' already exists (ID: {existing.id})")
            return False
        
        template = ConfigTemplate(
            name=name,
            description=description,
            game_type=game_type,
            template_data=json.dumps(config_dict),
            is_default=is_default,
            created_by=admin.id,
        )
        db.session.add(template)
        db.session.commit()
        print(f"✅ Created template: {name} (ID: {template.id})")
        return True

def delete_template(template_id):
    """Delete a template by ID."""
    with app.app_context():
        template = db.session.get(ConfigTemplate, template_id)
        if not template:
            print(f"❌ Template ID {template_id} not found")
            return False
        
        name = template.name
        db.session.delete(template)
        db.session.commit()
        print(f"✅ Deleted template: {name}")
        return True

def add_common_games():
    """Add templates for common game servers."""
    games = [
        {
            "game_type": "css",
            "name": "Counter-Strike: Source Standard",
            "description": "Standard CS:S dedicated server with SourceMod",
            "config": {
                "server_cfg": """// Counter-Strike: Source Server Configuration
hostname "My CS:S Server"
rcon_password "changeme"
sv_password ""
sv_maxplayers 32
sv_region 255
sv_lan 0
sv_cheats 0

// Gameplay Settings
mp_friendlyfire 0
mp_autoteambalance 1
mp_limitteams 2
mp_autokick 0
mp_tkpunish 0
mp_forcecamera 0
mp_allowspectators 1
mp_chattime 10
mp_roundtime 5
mp_freezetime 6
mp_buytime 0.25
mp_startmoney 800
mp_maxrounds 30
mp_winlimit 0
mp_timelimit 0

// Server Settings
sv_alltalk 0
sv_pausable 0
sv_pure 1
sv_contact "admin@example.com"
sv_downloadurl ""

exec banned_user.cfg
exec banned_ip.cfg
""",
                "mapcycle": """de_dust2
de_dust
de_inferno
de_nuke
de_train
de_aztec
de_cbble
de_prodigy
cs_office
cs_italy
cs_assault
""",
                "startup_script": """#!/bin/bash
cd /opt/servers/css
./srcds_run -game cstrike -console -usercon +map de_dust2 +maxplayers 32 +exec server.cfg
""",
            },
        },
        {
            "game_type": "csgo",
            "name": "CS:GO Competitive 5v5",
            "description": "CS:GO competitive matchmaking style server",
            "config": {
                "server_cfg": """// CS:GO Competitive Server
hostname "CS:GO Competitive 5v5"
rcon_password "changeme"
sv_password ""
sv_cheats 0
sv_lan 0

// Server Settings
sv_maxplayers 12
mp_autoteambalance 1
mp_limitteams 1
mp_teamname_1 "Terrorists"
mp_teamname_2 "Counter-Terrorists"

// Game Mode: Competitive
game_type 0
game_mode 1
mp_maxrounds 30
mp_overtime_enable 1
mp_overtime_maxrounds 6
mp_overtime_startmoney 10000

// Round Settings
mp_roundtime 1.92
mp_freezetime 15
mp_buytime 20
mp_buy_anywhere 0
mp_startmoney 800

// Gameplay
mp_friendlyfire 1
mp_autokick 0
mp_tkpunish 0
sv_alltalk 0
sv_deadtalk 0
sv_full_alltalk 0
sv_voiceenable 1
sv_coaching_enabled 1
""",
                "mapgroup": """de_dust2
de_mirage
de_inferno
de_nuke
de_overpass
de_train
de_vertigo
de_ancient
""",
            },
        },
        {
            "game_type": "tf2",
            "name": "Team Fortress 2 Standard",
            "description": "Standard TF2 server with basic settings",
            "config": {
                "server_cfg": """// Team Fortress 2 Server Configuration
hostname "Team Fortress 2 Server"
rcon_password "changeme"
sv_password ""
sv_cheats 0
sv_lan 0

// Server Settings
maxplayers 24
sv_visiblemaxplayers 24
sv_region 255

// Gameplay Settings
mp_friendlyfire 0
mp_autoteambalance 1
mp_teams_unbalance_limit 1
mp_disable_respawn_times 0
mp_tournament 0
mp_highlander 0

// Performance
sv_maxrate 30000
sv_minrate 20000
sv_maxupdaterate 66
sv_minupdaterate 10
sv_maxcmdrate 66
sv_mincmdrate 10

// Download Settings
sv_allowupload 1
sv_allowdownload 1
sv_downloadurl ""

// Communication
sv_alltalk 0
sv_voiceenable 1
""",
                "mapcycle": """ctf_2fort
cp_dustbowl
cp_granary
cp_well
pl_badwater
pl_goldrush
koth_harvest
koth_viaduct
""",
            },
        },
        {
            "game_type": "minecraft",
            "name": "Minecraft Vanilla Survival",
            "description": "Standard Minecraft Java Edition survival server",
            "config": {
                "server_properties": """#Minecraft server properties
server-port=25565
server-ip=
max-players=20
white-list=false
online-mode=true
enable-rcon=true
rcon.password=changeme
rcon.port=25575

# World Settings
level-name=world
level-seed=
level-type=DEFAULT
generator-settings=
allow-nether=true
allow-flight=false
spawn-protection=16
spawn-npcs=true
spawn-animals=true
spawn-monsters=true
generate-structures=true

# Gameplay
gamemode=survival
difficulty=normal
hardcore=false
pvp=true
force-gamemode=false
max-world-size=29999984

# Performance
view-distance=10
simulation-distance=10
max-tick-time=60000
network-compression-threshold=256

# Other
motd=A Minecraft Server
enable-command-block=false
enable-query=false
enable-status=true
""",
                "startup_script": """#!/bin/bash
cd /opt/servers/minecraft
java -Xmx2G -Xms2G -jar server.jar nogui
""",
            },
        },
        {
            "game_type": "rust",
            "name": "Rust Vanilla Server",
            "description": "Standard Rust dedicated server (vanilla)",
            "config": {
                "server_cfg": """// Rust Server Configuration
server.hostname "Rust Server"
server.url "https://example.com"
server.headerimage "https://example.com/banner.jpg"
server.description "Welcome to our Rust server!"
server.maxplayers 100
server.worldsize 4000
server.seed 12345

// RCON
rcon.password "changeme"
rcon.port 28016
rcon.web 1

// Server Settings
server.saveinterval 300
server.globalchat true
server.stability true
server.radiation true
server.pve false
server.secure true

// Admin Settings
server.adminsteamid 76561198012345678
""",
                "startup_script": """#!/bin/bash
cd /opt/servers/rust
./RustDedicated -batchmode \\
    +server.port 28015 \\
    +server.tickrate 30 \\
    +server.hostname "Rust Server" \\
    +server.maxplayers 100 \\
    +server.worldsize 4000 \\
    +server.seed 12345 \\
    +server.saveinterval 300 \\
    +rcon.port 28016 \\
    +rcon.password changeme \\
    +rcon.web 1
""",
            },
        },
        {
            "game_type": "palworld",
            "name": "Palworld Standard Server",
            "description": (
                "Palworld multiplayer survival and crafting game server "
                "(based on Ptero-Eggs)"
            ),
            "config": {
                "server_cfg": """# Palworld Server Configuration
# Based on Ptero-Eggs game-eggs configuration
# https://github.com/Ptero-Eggs/game-eggs/tree/main/palworld

# Server Settings
server_name=A Palworld Server
server_password=
admin_password=changeme
max_players=32
public_lobby=true
server_port=8211

# RCON Settings
rcon_enabled=true
rcon_port=25575

# World Settings
difficulty=normal
day_time_speed_rate=1.0
night_time_speed_rate=1.0
exp_rate=1.0
pal_capture_rate=1.0
pal_spawn_num_rate=1.0

# Gameplay Settings
pal_damage_rate_attack=1.0
pal_damage_rate_defense=1.0
player_damage_rate_attack=1.0
player_damage_rate_defense=1.0
player_stomach_decrease_rate=1.0
player_stamina_decrease_rate=1.0
player_auto_hp_regen_rate=1.0
player_auto_hp_regen_rate_in_sleep=1.0

# Death Settings
drop_item_max_num=3000
drop_item_max_num_unko=100
base_camp_max_num=128
base_camp_worker_max_num=15

# Community Settings
enable_invader_enemy=true
active_unko=false
enable_aim_assist_pad=true
enable_aim_assist_keyboard=false
""",
                "startup_script": """#!/bin/bash
cd /opt/servers/palworld
./Pal/Binaries/Linux/PalServer-Linux-Shipping Pal \\
    -publiclobby \\
    -useperfthreads \\
    -NoAsyncLoadingThread \\
    -UseMultithreadForDS \\
    -port=${SERVER_PORT} \\
    -publicport=${SERVER_PORT} \\
    -servername="${SERVER_NAME}" \\
    -players=${MAX_PLAYERS} \\
    -adminpassword="${ADMIN_PASSWORD}" \\
    -rcon
""",
            },
        },
        {
            "game_type": "openra",
            "name": "OpenRA Red Alert Server",
            "description": "OpenRA Red Alert RTS game server (based on Ptero-Eggs)",
            "config": {
                "server_cfg": """# OpenRA Red Alert Server Configuration
# Based on Ptero-Eggs game-eggs configuration
# https://github.com/Ptero-Eggs/game-eggs/tree/main/openra

# Server Settings
server_name=OpenRA Red Alert Server
server_port=1234
server_password=

# Server Options
advertise_online=false
enable_singleplayer=false
enable_geoip=false
share_anonymized_ips=true

# Map Settings
map_rotation=
dedicated_server=true

# Game Settings
allow_cheats=false
allow_version_mismatch=false
""",
                "startup_script": """#!/bin/bash
cd /opt/servers/openra
./squashfs-root/AppRun --server \\
    Server.Name="${SERVER_NAME}" \\
    Server.ListenPort=${SERVER_PORT} \\
    Server.AdvertiseOnline=${ADVERTISE_ONLINE} \\
    Server.EnableSingleplayer=${ENABLE_SINGLEPLAYER} \\
    Server.Password="${SERVER_PASSWORD}" \\
    Server.EnableGeoIP=${ENABLE_GEOIP} \\
    Server.ShareAnonymizedIPs=${SHARE_ANONYMIZED_IPS}
""",
            },
        },
    ]
    
    print("\nAdding common game templates...\n")
    success_count = 0
    for game in games:
        if add_template(
            game["game_type"],
            game["name"],
            game["description"],
            game["config"]
        ):
            success_count += 1
    
    print(f"\n✅ Successfully added {success_count}/{len(games)} templates")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manage game server templates",
        epilog="""
For importing 240+ game templates from Ptero-Eggs, see:
  scripts/import_ptero_eggs.py
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List templates
    subparsers.add_parser("list", help="List all templates")
    
    # Add common games
    subparsers.add_parser("add-common", help="Add templates for common games")
    
    # Delete template
    delete_parser = subparsers.add_parser("delete", help="Delete a template by ID")
    delete_parser.add_argument("id", type=int, help="Template ID to delete")
    
    # Add custom template
    add_parser = subparsers.add_parser("add", help="Add a custom template")
    add_parser.add_argument("game_type", help="Game type identifier (e.g., 'css')")
    add_parser.add_argument("name", help="Template name")
    add_parser.add_argument("--description", default="", help="Template description")
    add_parser.add_argument("--config-file", required=True, help="JSON file with config data")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "list":
        list_templates()
    elif args.command == "add-common":
        add_common_games()
    elif args.command == "delete":
        delete_template(args.id)
    elif args.command == "add":
        with open(args.config_file, 'r') as f:
            config_data = json.load(f)
        add_template(args.game_type, args.name, args.description, config_data)

if __name__ == "__main__":
    main()
