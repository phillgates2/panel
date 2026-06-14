# 🚀 -OZ- Panel Hub Enterprise
**The Ultimate Next-Generation Premium Game Server Orchestrator, CMS, and Community Forums Suite.**

![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)
![Version: Enterprise 2026](https://img.shields.io/badge/Version-2026_Enterprise-5865F2.svg)
![Database: PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_17-336791.svg)
![Proxy: Caddy Proxy](https://img.shields.io/badge/Webserver-Caddy_Proxy-00ADD8.svg)

---

## 🌟 Executive Architectural Overview
**-OZ- Panel Hub Enterprise** is a self-hosted monolithic process orchestrator and community management platform designed for esports organizations, gaming communities, and premium server hosting providers. 

Inspired by the powerful container configuration system of **Pterodactyl (Nests & Eggs)** and the highly polished seamless web portal integration of top enterprise panels, this suite delivers fully automated background downloads, highly responsive real-time WebSocket console terminals, an embedded SSH2/SFTP server, a complete web Content Management System (CMS), and an interactive forums network equipped with real-time community shoutbox chat.

---

## 🏗️ Pterodactyl-Style Nests & Game Eggs
This suite completely decouples game engine binaries from panel logic using JSON **Nests** and **Eggs**. Each Game Egg specifies exactly how a server should instantiate, execute, and clamp host resources.

### Sample Egg Specification (`panel/eggs/minecraft_vanilla.json`)
```json
{
  "nest": "Minecraft",
  "nest_identifier": "nest_minecraft",
  "name": "Minecraft Vanilla / Paper",
  "description": "Standard high-performance Minecraft server powered by Vanilla/Paper.",
  "docker_image": "ghcr.io/pterodactyl/yolks:java_21",
  "startup_command": "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar nogui",
  "install_script": "echo \"Downloading server.jar...\" && curl -o server.jar -L \"https://api.papermc.io/v2/projects/paper/versions/1.20.4/builds/496/downloads/paper-1.20.4-496.jar\" && echo \"eula=true\" > eula.txt",
  "env_variables": [
    { "key": "SERVER_MEMORY", "label": "Server Memory (MB)", "default_value": "1024", "required": true },
    { "key": "SERVER_PORT", "label": "Server Port", "default_value": "25565", "required": true }
  ],
  "config_files": [
    {
      "path": "server.properties",
      "template": "server-port={{SERVER_PORT}}\nenable-rcon=true\nrcon.password={{RCON_PASSWORD}}\nmotd={{MOTD}}\nmax-players={{MAX_PLAYERS}}\n"
    }
  ]
}
```

---

## 💻 Step-by-Step Fresh Bare-Metal Server Install
The following manual details exactly how to deploy the entire suite from a completely fresh **Ubuntu 24.04 LTS / Debian 12** server.

### Step 1: System Baseline & Package Dependencies
Update kernel repositories and install necessary runtime utilities:
```bash
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y curl wget git sudo build-essential unzip tar
```

### Step 2: Install Node.js v20.x LTS
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v && npm -v
```

### Step 3: Deploy PostgreSQL 17 Database Cluster
```bash
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl enable postgresql && sudo systemctl start postgresql

# Create panel database pool and restricted RBAC user
sudo -u postgres psql -c "CREATE USER panel WITH PASSWORD 'panel_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE panel_db OWNER panel;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE panel_db TO panel;"
sudo -u postgres psql -d panel_db -c "GRANT ALL ON SCHEMA public TO panel;"
```

### Step 4: Install Caddy Automated Edge Proxy
Install Caddy for enterprise-grade automated reverse proxying with built-in Let's Encrypt certificates:
```bash
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install -y caddy
sudo systemctl enable caddy
```

### Step 5: Clone & Initialize -OZ- Panel Hub Enterprise
```bash
git clone https://github.com/phillgates2/panel.git /home/user/panel
cd /home/user/panel
npm install

# Build active directory stores
mkdir -p eggs servers assets
```

### Step 6: Power Boot Master Process
Launch the application core daemon:
```bash
npm start
```
*Note: In production environments, it is highly recommended to manage the core daemon using `PM2` or a dedicated `systemd` service routine.*

---

## 🌐 The Full Web Setup Wizard (`/install`)
Before production execution, all settings can be completely instantiated via the **Web Setup Wizard**.
1. Navigate to `http://<your-server-ip>:3000/install`.
2. **Step 1:** System Verification Check confirms Node.js runtime yolks and PostgreSQL execution availability.
3. **Step 2:** Database & Proxy Setup allows configuring PostgreSQL credentials and external production web hostnames.
4. **Step 3:** Branding Setup customizes CMS navigation headers, community MOTD, and Global Social Media Discord links.
5. **Step 4:** Super Administrator Creation instantiates your master Master RBAC account and automatically writes your production `/etc/caddy/Caddyfile`.

### Automated Production Caddyfile Output
When submitted, the installer writes an optimized edge configuration:
```caddyfile
panel.oz-esports.network:80 {
    reverse_proxy 127.0.0.1:3000
    encode gzip zstd
    file_server
}
```

---

## 📁 Embedded SFTP Daemon & Web File Manager
Users can orchestrate their sandboxed server directories through two world-class approaches:
- **Rich Web File Manager:** An immersive web browser interface executing inside `panel/servers/{uuid}/` supporting file uploads, inline syntax-highlighted code file editing (`server.properties`, `server.cfg`), folder instantiation, item renaming, and exact file deletions.
- **Standalone SFTP Daemon:** The panel includes a native `ssh2` embedded SFTP daemon active on port `2022`. Gamers can connect external SFTP clients (like **FileZilla** or **WinSCP**) directly using their panel credentials or a standalone SFTP password.

---

## 🎮 Live Graphical RCON & Server Console
- **Silky Smooth Real-Time Streaming:** Powered by bidirectional `Socket.io` ring-buffers, live console `stdout` / `stderr` streams directly into an interactive dark-mode terminal window.
- **Graphical Action Workbench:** Includes pre-configured graphical routine buttons (`Kick`, `Ban`, `Force Save World`, `Whitelist Toggle`, `Status Report`, `Server Wide Overlay Say`) so staff never have to memorize command syntax.

---

## 🤖 24/7 AI Watchdog Sentinel & Discord Webhooks
- **Automated Incident Recovery:** The AI Sentinel continuously monitors online container allocations. If a fatal crash or abnormal RAM/CPU usage spike is detected, the AI logs an official incident report, automatically relaunches the server binary, and dispatches an immediate embedded **Discord Webhook Alert**.
- **Interactive AI Expert:** Gamers can navigate to the **AI Consultant Tab** to ask an AI questions about gameplay optimization, garbage collection clamping parameters, or automated console error diagnostics!

---

## 🛡️ Enterprise Security Clamping Built-In
The platform enforces state-of-the-art multi-layered security engineering:
1. **Strict Role-Based Access Control (RBAC):** Exactly clamps operational permissions across User, Support, Mod, and Admin tiers.
2. **Path Traversal Clamping:** All Web File Manager operations and embedded SFTP sessions strictly evaluate absolute path resolving to guarantee users cannot escape their assigned `/home/user/panel/servers/{uuid}` sandbox.
3. **Cryptographic Hardening:** Enforces strong `bcrypt` password hashing and secure `express-session` cookies.
4. **Automated Two-Factor (2FA):** Allows enforcing TOTP mobile authenticators (Google Authenticator, Authy) to eliminate credential stuffing vulnerabilities.
5. **Caddy Edge Defenses:** Caddy automates HTTPS Let's Encrypt Let's Encrypt encryption and provides robust L7 rate-limiting.

---

## 💡 Professional Community Support
If you encounter deployment exceptions or require bespoke Egg creation, join our official Discord community: `<https://discord.gg/ozpanel>`!

Happy Sandboxed Hosting! 🚀🎮
