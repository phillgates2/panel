# 🚀 -OZ- Panel Hub Enterprise
**The Ultimate Next-Generation Premium Game Server Orchestrator, CMS, Hardware Sentinel, and Community Forums Suite.**

![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)
![Version: Enterprise 2026](https://img.shields.io/badge/Version-2026_Enterprise-5865F2.svg)
![Database: PostgreSQL / Mock Engine](https://img.shields.io/badge/Database-PostgreSQL_17-336791.svg)
![Proxy: Caddy / Direct Edge](https://img.shields.io/badge/Webserver-Port_80_Edge-00ADD8.svg)

---

## 🌟 Executive Architectural Overview
**-OZ- Panel Hub Enterprise** is a self-hosted monolithic process orchestrator and community hosting platform designed for elite esports organizations, collaborative gaming networks, and premium commercial hosting providers.

Inspired by the powerful container configuration system of **Pterodactyl (Nests & Eggs)** and the seamless community web portal integration of top enterprise platforms, this suite delivers lightning-fast automated background file downloads, highly responsive live WebSocket console terminals, dual web/SFTP file management, advanced server hardware monitoring, and an interactive forums network equipped with real-time community shoutbox chat.

---

## 🌐 The Full Web Setup Wizard (`/install`)
To guarantee flawless deployment, the platform is configured such that **the Web Installation Wizard is the very first thing anyone sees**.

When booting your server, any visitor or staff member navigating to your default IP or web address (`http://0.0.0.0` or `http://oz-esports.network`) will be instantly captured and routed to `/install`.

1. **Step 1:** System Verification Diagnostic confirms Node.js subprocess engine capabilities and PostgreSQL runtime drivers.
2. **Step 2:** Database & Proxy Setup allows configuring your PostgreSQL cluster pools and primary web hostnames.
3. **Step 3:** Community Brand Identity customizes your public CMS navigation titles, pre-game Message of the Day (MOTD), and Global Social Media links (Discord, Twitter/X, GitHub).
4. **Step 4:** Super Administrator Creation instantiates your Master RBAC account, initializes all 25 game eggs, and automatically generates your edge reverse proxy configurations (`Caddyfile.production`).

---

## 🖥️ Edge Routing: Default Web Address (No Port Required)
The core Node daemon (`src/index.js`) is natively architected to execute on standard **Port 80** and **Port 443** HTTP/HTTPS edge protocols. Your community can access the entire panel cleanly without typing port numbers:
```
http://oz-esports.network
```

### 🧠 Smart Unprivileged Proxy Elevation Fallback
If you launch the panel on a Linux VPS without root capabilities (which OS kernels demand for binding below Port 1024), the Core Sentinel intelligently detects the `EACCES` permission exception and automatically instantiates a silky smooth reverse proxy fallback on **Port 3000**, ensuring 100% reliable execution in all bare-metal and sandboxed testing workspaces.

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
- **Silky Smooth Live si Polling:** Powered by asynchronous `systeminformation` telemetry, fresh host metrics update in the browser every 2.5 seconds without page refreshes.
- **4 Circular Saturation Gauges:** Visualizes live updating readouts for Host CPU Saturation (attaching actual GHz clocks & CPU temperatures), Physical RAM memory pool usage (`GB Consumed vs Free`), Mounted Storage Drive saturation (`/dev/root`), and active Network I/O Bandwidth speedometers (`KB/s Rx/Tx`).
- **Multi-Core Thread Inspector:** Visualizes real-time dynamic loads across all 8 underlying host CPU logical cores in animated vertical progress bars.
- **Subprocess Roster Breakdown:** Inspects every running game container, reporting running process PIDs, active cgroup CPU allocations, and dedicated RAM pools consumed.
- **Spike Alarms Configuration:** Super Administrators can specify warning threshold spikes (e.g. CPU > 90%, RAM > 95%) that trigger AI Sentinels to automatically dispatch emergency alerts to your linked Discord webhooks.

---

## 💻 Dual Dual File Management & SFTP
Users can oversee their sandboxed server files through two highly polished approaches:
- **Immersive Web File Manager:** A graphical visual browser executing inside `panel/servers/{uuid}/` supporting file uploads, intuitive directory creations, item renaming, precise deletions, and an **inline syntax-highlighted code editor** for editing game configs (`server.properties`, `settings.yaml`).
- **Embedded Node SFTP Daemon:** The panel includes a native `ssh2` embedded SFTP daemon running on **Port 2022**. Gamers can connect standard external FTP/SFTP clients (**FileZilla**, **WinSCP**) directly to their directories using user credentials or dedicated standalone SFTP passwords.

---

## 🎮 Live Bidirectional Server Console & Graphical RCON
- **Real-Time Rolling Terminal:** Bidirectional `Socket.io` ring-buffers stream live stdout/stderr game server output directly into a stunning dark-mode interactive console window.
- **Graphical Quick Workbench:** Staff can execute pre-configured graphical routines (`Kick`, `Ban`, `Force Save World`, `Status Diagnostic`, `Whitelist Toggle`, `Server Wide Administrative Overlay Say`) without memorizing command syntax.

---

## 🤖 Automated Auto-Recovery AI Watchdog & Discord Links
- **Dedicated Discord Webhooks:** When game servers are deployed, users can link dedicated Discord channel Webhook URLs. The panel automatically transmits beautiful embedded status updates when instances boot, halt, or are recovered by AI.
- **24/7 Anomaly Auto-Recovery:** The AI Sentinel continuously monitors running child processes. If an instance experiences an unexpected fatal crash or port conflict, the AI Watchdog records an official incident report, automatically relaunches the process, and alerts your linked Discord channel.
- **Interactive AI Expert:** Gamers can navigate to the **`🤖 AI Sentinel`** tab to ask an interactive AI expert advice on game configurations, multithreading parameters, or automated console log parsing.

---

## 🛡️ Enterprise Security Engineering
The suite enforces rigorous commercial security clamping built directly into the core:
1. **Strict Role-Based Access Control (RBAC):** Exactly clamps operational permissions across User, Support, Mod, and Admin tiers.
2. **Path Traversal Defenses:** All Web File Manager actions and SFTP sessions strictly enforce absolute path resolution to guarantee users cannot escape their assigned `/home/user/panel/servers/{uuid}` container sandbox.
3. **Cryptographic Hardening:** Enforces strong `bcrypt` password hashing and highly secure `express-session` cookies.
4. **Enforced Two-Factor (2FA):** Allows enforcing TOTP mobile authenticators (Google Authenticator, Authy) to completely eliminate credential stuffing vulnerabilities.
5. **Caddy Edge Proxy defencing:** Completely optimized for standard edge deployment or direct reverse proxy automation with automated Let's Encrypt SSL.

---

## 💻 Step-by-Step Production Bare-Metal Linux Install Guide
The following step-by-step commands detail exactly how to deploy the entire platform from a completely fresh **Ubuntu 24.04 LTS / Debian 12** server.

### Step 1: System Baseline & Dependencies
Update system package repositories and install necessary build utilities:
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

# Create active database pool and restricted RBAC user
sudo -u postgres psql -c "CREATE USER panel WITH PASSWORD 'panel_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE panel_db OWNER panel;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE panel_db TO panel;"
sudo -u postgres psql -d panel_db -c "GRANT ALL ON SCHEMA public TO panel;"
```

### Step 4: Install Caddy Automated Reverse Proxy (Optional)
Install Caddy for automatic edge proxying with built-in Let's Encrypt HTTPS certificates:
```bash
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install -y caddy
sudo systemctl enable caddy
```

### Step 5: Clone & Initialize -OZ- Panel Hub Enterprise
```bash
git clone https://github.com/your-org/oz-panel-hub.git /home/user/panel
cd /home/user/panel
npm install

# Instantiating active directories
mkdir -p eggs servers assets
```

### Step 6: Power On Platform Monolith
Launch the core orchestrator process:
```bash
npm start
```
*Note: For production hosting, we highly recommend maintaining the master process using `PM2` (`pm2 start src/index.js --name "oz-hub"`) or a dedicated `systemd` service script.*

---

## 💬 Community Support Network
If you require bespoke Pterodactyl Egg construction or require operational advice, join our official community network: `<https://discord.gg/ozpanel>`!

Prepare your factory lines and game servers! ⚡🎮
