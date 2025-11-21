# Quick Reference: Game Server Management

## Fixed Issues

### ✅ Journalctl Errors
**Problem**: `Could not read memwatch log: [Errno 2] No such file or directory: 'journalctl'`

**Solution**: The panel now checks if `journalctl` exists before using it. In development environments (like this Alpine Linux container), it shows a friendly message instead of an error.

**What Changed**: Updated `/admin/tools` route to use `shutil.which("journalctl")` to detect availability.

### ✅ Database Page Syntax Errors
**Status**: No syntax errors found. Page loads correctly.

### ✅ Forum & CMS csrf_token Errors
**Solution**: Added context processors to both blueprints to inject `csrf_token` function.

---

## Game Server Setup

### Quick Start

1. **Add game templates** (already done):
   ```bash
   python scripts/manage_game_templates.py add-common
   ```

2. **Create a server**:
   - Go to Dashboard → Admin → Servers → Create Server
   - Select game type (ET:Legacy, CS:S, CS:GO, TF2, Minecraft, Rust, etc.)
   - Enter server name and description
   - Click Create

3. **Upload game files**:
   ```bash
   # Example for ET:Legacy
   mkdir -p /opt/servers/your-server-name
   cd /opt/servers/your-server-name

   # Download game files
   wget https://www.etlegacy.com/download/file/111 -O etlegacy.tar.gz
   tar -xzf etlegacy.tar.gz
   chmod +x etlded
   ```

4. **Configure & start**:
   - Edit server configuration in panel
   - Start server via panel or command line
   - Monitor via dashboard

---

## Available Commands

### List Game Templates
```bash
python scripts/manage_game_templates.py list
```

### Add Common Game Templates
```bash
python scripts/manage_game_templates.py add-common
```
Adds templates for:
- Counter-Strike: Source
- CS:GO
- Team Fortress 2
- Minecraft
- Rust

### Delete Template
```bash
python scripts/manage_game_templates.py delete <ID>
```

### Add Custom Template
```bash
python scripts/manage_game_templates.py add <game_type> "<name>" \
  --description "Description" \
  --config-file config.json
```

Example `config.json`:
```json
{
  "server_cfg": "// Server config content\nhostname \"My Server\"\n",
  "startup_script": "#!/bin/bash\n./server_binary\n"
}
```

---

## Game Types Supported

| Game | ID | Default Port | Template Available |
|------|----|--------------|--------------------|
| ET:Legacy | `etlegacy` | 27960 | ✅ |
| CS:Source | `css` | 27015 | ✅ |
| CS:GO | `csgo` | 27015 | ✅ |
| Team Fortress 2 | `tf2` | 27015 | ✅ |
| Minecraft | `minecraft` | 25565 | ✅ |
| Rust | `rust` | 28015 | ✅ |
| Valheim | `valheim` | 2456 | ⚪ |
| ARK | `ark` | 7777 | ⚪ |
| Custom | `custom` | varies | ⚪ |

⚪ = Can be added with custom template

---

## Server File Locations

### Default Base Directory
```
/opt/servers/
```

### Per-Server Structure
```
/opt/servers/<server-name>/
├── executable (etlded, srcds_run, etc.)
├── configs/
│   ├── server.cfg
│   └── ...
├── maps/
├── mods/
└── logs/
```

### Changing Base Directory
Edit `.env` or `config.py`:
```bash
DOWNLOAD_DIR=/opt/servers
```

---

## File Upload Methods

### 1. SCP (Secure Copy)
```bash
scp -r /local/path/* user@server:/opt/servers/server-name/
```

### 2. SFTP (Filezilla, WinSCP)
- Connect to server on port 22
- Navigate to `/opt/servers/`
- Upload files

### 3. Direct Download on Server
```bash
ssh user@server
cd /opt/servers/server-name
wget <download-url>
tar -xzf archive.tar.gz
```

### 4. Git Clone (for mods/plugins)
```bash
cd /opt/servers/server-name/mods
git clone https://github.com/user/mod.git
```

---

## Common Game Server Downloads

### ET:Legacy
```bash
wget https://www.etlegacy.com/download/file/111 -O etlegacy.tar.gz
```

### Source Games (CS:S, CS:GO, TF2)
Use SteamCMD:
```bash
# Install SteamCMD
apt-get install steamcmd

# Download CS:Source (example)
steamcmd +login anonymous +force_install_dir /opt/servers/css \
  +app_update 232330 validate +quit
```

### Minecraft
```bash
wget https://launcher.mojang.com/v1/objects/<hash>/server.jar
```

### Rust
Requires Steam account and SteamCMD with login.

---

## Troubleshooting

### Permission Denied
```bash
sudo chown -R panel-user:panel-user /opt/servers
chmod +x /opt/servers/*/server_binary
```

### Port Already in Use
Check with:
```bash
ss -tulpn | grep <port>
```

Kill conflicting process or change port in config.

### Missing Libraries
Check dependencies:
```bash
ldd /opt/servers/server-name/executable
```

Install missing packages:
```bash
apt-get install lib32gcc-s1 lib32stdc++6  # For 32-bit games
```

### Server Won't Start
1. Check logs: `/opt/servers/server-name/logs/`
2. Test manually: `./executable` in server directory
3. Check file permissions
4. Verify configuration files

---

## Next Steps

1. ✅ **Templates Created** - Run `python scripts/manage_game_templates.py list`
2. 📁 **Upload Game Files** - Use SCP/SFTP to upload binaries
3. 🎮 **Create Server** - Via panel web interface
4. ⚙️ **Configure** - Edit server settings
5. ▶️ **Start** - Launch server via panel
6. 📊 **Monitor** - Check dashboard for status

---

## Documentation

- Full guide: [`docs/GAME_SERVER_SETUP.md`](./GAME_SERVER_SETUP.md)
- API docs: [`docs/API_DOCUMENTATION.md`](./API_DOCUMENTATION.md)
- Troubleshooting: [`docs/TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)

---

## Summary of Changes

### Files Modified
- ✅ `app.py` - Fixed journalctl check with `shutil.which()`
- ✅ `forum/__init__.py` - Added csrf_token context processor
- ✅ `cms/__init__.py` - Added csrf_token context processor
- ✅ `templates/server_create.html` - Updated game type dropdown

### Files Created
- ✅ `docs/GAME_SERVER_SETUP.md` - Comprehensive game server guide
- ✅ `scripts/manage_game_templates.py` - Template management CLI tool
- ✅ `docs/QUICK_REFERENCE.md` - This file

### Templates Added
- Counter-Strike: Source Standard
- CS:GO Competitive 5v5
- Team Fortress 2 Standard
- Minecraft Vanilla Survival
- Rust Vanilla Server
