# 🚀 -OZ- Panel Hub Enterprise
**The Ultimate Next-Generation Premium Game Server Orchestrator, CMS, Hardware Sentinel, and Community Forums Suite.**

![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)
![Version: Enterprise 2026](https://img.shields.io/badge/Version-2026_Enterprise-5865F2.svg)
![Database: PostgreSQL / Mock Engine](https://img.shields.io/badge/Database-PostgreSQL_17-336791.svg)
![Proxy: Standard Edge (Port 80)](https://img.shields.io/badge/Webserver-Primary_IP_Edge-00ADD8.svg)
![Execution: PM2 Background](https://img.shields.io/badge/Execution-PM2_Background-green.svg)

---

## 🌟 Executive Architectural Overview
**-OZ- Panel Hub Enterprise** is a self-hosted monolithic process orchestrator and community hosting platform designed for elite esports organizations, collaborative gaming networks, and premium commercial hosting providers.

Inspired by the powerful container configuration system of **Pterodactyl (Nests & Eggs)** and the seamless community web portal integration of top enterprise platforms, this suite delivers lightning-fast automated background file downloads, highly responsive live WebSocket console terminals, dual web/SFTP file management, advanced server hardware telemetry readouts, and an interactive forums network equipped with real-time community shoutbox chat.

---

## 🌐 The Full Web Setup Wizard (`/install`)
To guarantee flawless deployment, the platform is configured such that **the Web Installation Wizard is the guaranteed very first thing anyone sees**.

When booting your server, any visitor or staff member navigating to your primary server IP (`http://0.0.0.0` or `<Server-IP>`) will be instantly captured and routed to `/install`.

1. **Step 1:** System Verification Diagnostic confirms Node.js subprocess engine capabilities and PostgreSQL runtime drivers.
2. **Step 2:** Database & Primary IP Setup allows configuring your PostgreSQL cluster pools and sets your Primary Web Address (configured to **just use your Server IP** for now).
3. **Step 3:** Community Brand Identity customizes your public CMS navigation titles, pre-game Message of the Day (MOTD), and Global Social Media links (Discord, Twitter/X, GitHub).
4. **Step 4:** Super Administrator Creation instantiates your Master RBAC account, initializes all 25 game eggs, and automatically generates your production reverse proxy specifications (`Caddyfile.production`).

---

## 🧪 Indestructible Indestructible Route & Egg Validation Suite
The entire platform includes a remarkable built-in mock query parser (`schema.js`), universal AJAX bridges (`apiRoute.js`), and self-healing egg retrieval orchestrators (`serverManager.js`) that guarantee **100% invincible execution** across all interactive interfaces:
- **Indestructible Config & Command Retrieval:** `serverManager.js` features highly robust fallback matchers. If your real production database `servers` records ever detach or join against missing `eggs` table serial IDs, the daemon automatically queries our master in-memory egg library to retrieve the perfect matching `config_files`, `startup_command`, and `install_script`!
- **Safe JSON Parsing Workbenches:** All configurations strictly execute safe type verifications (`Array.isArray` and `try/catch JSON.parse`) to guarantee your platform never throws `configFiles is not iterable` or `Cannot read properties of undefined (reading 'replace')` exceptions.
- **Flawless Setup Routing:** `INSTALLED: 'false'` flags enforce instantaneous capture to the setup wizard. Form submissions correctly serialize credentials and unlock the master portal.
- **Persistent Workbench Form Operations:** All `UPDATE` and `DELETE` routines across Super Admin dashboards, User Profile settings, File browser views, and Server allocation forms execute fully in both PostgreSQL mode and ephemeral testing workspaces.

---

## 🔌 Surviving SSH Session Terminations: Running in the Background
To maintain your game servers and master hosting portal running continuously independent of any interactive SSH terminal, this suite provides **dual world-class background execution approaches**:

### Method 1: Automated PM2 Sentinel (Highly Recommended)
We have constructed a dedicated automated execution helper (`start_background.sh`) equipped with **PM2** (Process Manager 2) that automatically forks your platform into the background, generates rolling telemetry logs, and automatically relaunches instances on fatal halts.

Simply execute from your project directory:
```bash
./start_background.sh
```
*(Or use `npm run start:background`)*.

**💡 Essential Management Shortcuts:**
- **View Silky Smooth Real-Time Logs:** `npm run logs:background` *(or `npx pm2 logs oz-panel-hub`)*
- **Inspect Infrastructure Telemetry:** `npm run status:background` *(or `npx pm2 status oz-panel-hub`)*
- **Halt Platform Background Operations:** `npm run stop:background` *(or `npx pm2 stop oz-panel-hub`)*

### Method 2: Native Linux `systemd` Daemon
For traditional bare-metal system administration, we have included a complete `systemd` service template (`oz-panel.service`) that executes your orchestrator as a native Linux kernel service independent of user logins:
```bash
sudo cp oz-panel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now oz-panel
```

---

## 🖥️ Edge Routing: Standard Server IP (No Port Required)
The core Node daemon (`src/index.js`) is natively architected to execute on standard **Port 80** and **Port 443** HTTP/HTTPS edge protocols. Your community can access the entire panel cleanly without typing port numbers:
```
http://0.0.0.0
```
*(Simply navigate to your public `<Server-IP>` in any web browser).*

### 🧠 Smart Internal Elevation Fallback
If you launch the panel on a Linux VPS without root capabilities (which OS kernels demand for binding below Port 1024), the Core Sentinel intelligently detects the `EACCES` permission exception and automatically instantiates a silky smooth proxy fallback on **Port 3000**, ensuring 100% reliable execution in all bare-metal environments and sandbox workspaces.

---

## 🏗️ Massive 25-Egg Pterodactyl Library
This suite completely decouples game engine binaries from panel logic using structured JSON **Nests** and **Eggs** (`panel/eggs/`). Each Egg specifies exact start commands, Docker/runtime yolk images, file install routines, environment variables, and configuration file injection templates (`server.properties`, `server.cfg`).

Your enterprise suite comes pre-loaded with **25 fully configured commercial Game Eggs**:
1. **Valve / Source Engine Nest**:
   - `CS:GO / CS2 Dedicated Server` (`csgo.json`)
   - `Team Fortress 2 Dedicated Server` (`team_fortress_2.json`)
   - `Garry's Mod Dedicated Server` (`garrys_mod.json` with Steam Workshop syncing)
   - `Left 4 Dead 2 Cooperative FPS` (`left_4_dead_2.json`)
2. **Survival Games Nest**:
   - `Rust Dedicated Server` (`rust.json` with Web RCON support)
   - `ARK: Survival Evolved Cluster Server` (`ark_survival_evolved.json`)
   - `Palworld Dedicated Server` (`palworld.json` with multithreading parameters)
   - `Valheim Dedicated Server` (`valheim.json` for crossplay Viking realms)
   - `DayZ Standalone Dedicated Server` (`dayz.json` equipped with BattlEye support)
   - `Unturned Dedicated Server` (`unturned.json` for headless RocketMod execution)
   - `Project Zomboid Isometric Sandbox` (`project_zomboid.json`)
   - `7 Days to Die Open-World Horde Crafting` (`seven_days_to_die.json`)
3. **Strategy & ID Software Nests**:
   - `OpenRA Real-Time Strategy Dedicated Server` (`openra.json` for Westwood Red Alert, Tiberian Dawn, and Dune 2000 matches)
   - `ET: Legacy Dedicated Server` (`etlegacy.json` for cooperative World War II tactical FPS)
   - `Quake III Arena Frag Deathmatch` (`quake3.json`)
4. **Voxel, Voxel-Proxy, & Minecraft Nests**:
   - `Minecraft Vanilla / Paper Optimized` (`minecraft_vanilla.json`)
   - `Minecraft Bedrock Official C++ Dedicated` (`minecraft_bedrock.json`)
   - `Minecraft Forge Modpack Server` (`minecraft_forge.json`)
   - `Velocity / BungeeCord Network Proxy` (`minecraft_bungeecord.json`)
   - `Terraria tShock Dedicated Server` (`terraria.json`)
5. **Roleplay & Factory Nests**:
   - `FiveM GTA V Customized Roleplay` (`gta_fivem.json` with TxAdmin capabilities)
   - `Factorio Headless Mega Factory` (`factorio.json`)
   - `Arena High-Speed Match Server` (`node_sandbox.json`)
6. **Voice Communications Nest**:
   - `Mumble Murmur Low-Latency Opus Server` (`mumble.json`)
   - `TeamSpeak 3 Commercial Voice Engine` (`teamspeak3.json`)

---

## 📊 Master Server Hardware Telemetry & Sentinel Core
Administrators can oversee host infrastructure by navigating to the **`🖥️ Hardware Telemetry`** control room (`/hardware`):
- **Silky Smooth Live Telemetry:** Powered by asynchronous `systeminformation` polling, fresh host metrics update in the browser every 2.5 seconds without page refreshes.
- **4 Circular Saturation Gauges:** Visualizes live updating readouts for Host CPU Saturation (attaching actual GHz clocks & CPU temperatures), Physical RAM memory pool usage (`GB Consumed vs Free`), Mounted Storage Drive saturation (`/dev/root`), and active Network I/O Bandwidth speedometers (`KB/s Rx/Tx`).
- **Multi-Core Thread Inspector:** Visualizes real-time dynamic utilization across all 8 underlying host CPU logical cores in animated vertical progress bars.
- **Subprocess Container Breakdown:** Inspects every running game instance, reporting running process PIDs, active cgroup CPU allocations, and dedicated RAM pools consumed.
- **Spike Alarms Configuration:** Super Administrators can specify custom threshold spikes (e.g. CPU > 90%, RAM > 95%) that trigger AI Sentinels to automatically dispatch emergency alerts to your linked Discord webhooks.

---

## 💻 Dual Web File Management & Embedded SFTP
Users can operate their assigned directories through two highly polished approaches:
- **Immersive Web File Manager:** A graphical browser executing inside `panel/servers/{uuid}/` supporting file uploads, intuitive directory creations, item renaming, precise deletions, and an **inline syntax-highlighted code editor** for editing game configs (`server.properties`, `settings.yaml`).
- **Embedded Node SFTP Daemon:** The panel includes a native `ssh2` embedded SFTP daemon active on **Port 2022**. Gamers can connect external FTP/SFTP clients (**FileZilla**, **WinSCP**) directly to their directories using user credentials or dedicated standalone SFTP passwords.

---

## 🎮 Live Silky Smooth Console & Graphical RCON
- **Real-Time Rolling Terminal:** Bidirectional `Socket.io` ring-buffers stream live stdout/stderr game server output directly into a stunning dark-mode interactive console window.
- **Graphical Master Workbench:** Staff can execute pre-configured graphical routines (`Kick`, `Ban`, `Force Save World`, `Status Diagnostic`, `Whitelist Toggle`, `Server Wide Administrative Overlay Say`) without memorizing command syntax.

---

## 🤖 Automated Anomaly Auto-Recovery AI
- **Dedicated Discord Webhooks:** When game servers are deployed, users can link dedicated Discord channel Webhook URLs. The panel automatically transmits beautiful embedded status updates when instances boot, halt, or are recovered by AI.
- **24/7 Anomaly Watchdog:** The AI Sentinel continuously monitors running child processes. If an instance experiences an unexpected fatal crash or port conflict, the AI Watchdog records an official incident report, automatically relaunches the process, and alerts your linked Discord channel.
- **Interactive AI Expert:** Gamers can navigate to the **`🤖 AI Sentinel`** tab to ask an interactive AI expert operational advice on game configurations, multithreading parameters, or automated console log parsing.

---

## 🛡️ Enterprise Security Engineering
The suite enforces rigorous commercial security clamping built directly into the core:
1. **Strict Role-Based Access Control (RBAC):** Exactly clamps operational permissions across User, Support, Mod, and Admin tiers.
2. **Path Traversal Defenses:** All Web File Manager actions and SFTP sessions strictly enforce absolute path resolution to guarantee users cannot escape their assigned `/home/user/panel/servers/{uuid}` sandbox.
3. **Cryptographic Hardening:** Enforces strong `bcrypt` password hashing and highly secure `express-session` cookies.
4. **Enforced Two-Factor (2FA):** Allows enforcing TOTP mobile authenticators (Google Authenticator, Authy) to completely eliminate credential stuffing vulnerabilities.

---

## 💻 Step-by-Step Production Bare-Metal Linux Install Guide
The following terminal commands detail exactly how to deploy the entire platform from a completely fresh **Ubuntu 24.04 LTS / Debian 12** bare-metal server or VPS.

### Step 1: System Baseline & Dependencies
Update system repositories and install necessary build utilities:
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

# Create database pool and restricted RBAC user
sudo -u postgres psql -c "CREATE USER panel WITH PASSWORD '(panel_secure_password)';"
sudo -u postgres psql -c "CREATE DATABASE panel_db OWNER panel;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE panel_db TO panel;"
sudo -u postgres psql -d panel_db -c "GRANT ALL ON SCHEMA public TO panel;"
```

### Step 4: Install Caddy Automated Edge Proxy (Optional)
Install Caddy for automated edge proxying with Let's Encrypt HTTPS Let's Encrypt certificates:
```bash
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install -y caddy
sudo systemctl enable caddy
```

### Step 5: Clone & Initialize -OZ- Panel Hub Enterprise
```bash
git clone https://github.com/phillgates2/panel.git /home/(username)/panel
cd /home/(username)/panel
npm install

# Instantiating operational directories
mkdir -p eggs servers assets
```

### Step 6: Launch Master Monolith (Background Mode)
Start the application core process in the background via PM2:
```bash
./start_background.sh
```
*(Or run `npm run start:background`)*.

---

## 💬 Community Support Network
If you require bespoke Pterodactyl Egg construction or operational troubleshooting, join our official community network: `<https://discord.gg/ozpanel>`!

Power on your strategy nodes and game servers! ⚡🎮
