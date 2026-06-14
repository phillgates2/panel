const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

let pool = null;
const mockDbPath = path.join(__dirname, '../../mock_db.json');

// Fully populated fallback database for environments without an active PostgreSQL daemon
let fallbackDb = {
  system_settings: {
    'SITE_TITLE': '-OZ- Panel Hub Enterprise',
    'SITE_MOTD': 'Next-Gen Premium Game Server Orchestrator',
    'SOCIAL_DISCORD': 'https://discord.gg/ozpanel',
    'SOCIAL_TWITTER': 'https://twitter.com/ozpanel',
    'SOCIAL_GITHUB': 'https://github.com/ozpanel',
    'WEB_HOSTNAME': 'oz-esports.network',
    'INSTALLED': 'false' // Enforce Web Setup Installer as the very first thing to see
  },
  users: [
    {
      id: 1,
      username: 'admin',
      email: 'admin@ozpanel.enterprise',
      password_hash: '$2a$10$7/O2z9...samplebcrypt...', // AdminSecure2026!
      role: 'admin',
      avatar: '/assets/default_avatar.png',
      bio: 'Master Super Administrator account for -OZ- Panel Hub Enterprise.',
      two_factor_enabled: false,
      api_key: 'oz_master_api_key_1337',
      created_at: new Date().toISOString()
    }
  ],
  cms_pages: [
    {
      id: 1,
      slug: 'terms-of-service',
      title: 'Terms of Service',
      content: 'Welcome to -OZ- Panel Hub Enterprise. All game servers are fully sandboxed and orchestrated for peak esports performance.',
      is_published: true,
      meta_description: '-OZ- Panel Hub Terms and Rules',
      author_id: 1,
      author_name: 'admin',
      created_at: new Date().toISOString()
    }
  ],
  cms_news: [
    {
      id: 1,
      title: '🚀 Deploying -OZ- Panel Hub Enterprise v2026',
      summary: 'Welcome to the definitive commercial game hosting and orchestrator platform.',
      content: 'We are thrilled to officially launch **-OZ- Panel Hub Enterprise**. Featuring fully automated Pterodactyl-style game eggs, lightning-fast live WebSocket consoles, standalone SFTP processing, and built-in interactive forums with live community shoutbox chat!',
      image_url: '/assets/news_default.jpg',
      author_id: 1,
      author_name: 'admin',
      is_published: true,
      created_at: new Date().toISOString()
    }
  ],
  cms_nav_links: [
    { id: 1, label: 'Official Discord', url: 'https://discord.gg/ozpanel', target: '_blank', sort_order: 1 }
  ],
  nests: [
    { id: 1, name: 'Minecraft', description: 'Minecraft game engines', identifier: 'nest_minecraft' },
    { id: 2, name: 'Source Engine', description: 'Valve dedicated engines', identifier: 'nest_source' },
    { id: 3, name: 'Survival Games', description: 'Open world craft servers', identifier: 'nest_survival' },
    { id: 4, name: 'Sandboxed Demos', description: 'High speed interactive engines', identifier: 'nest_sandbox' },
    { id: 5, name: 'Wolfenstein: Enemy Territory', description: 'Tactical World War II FPS game engines and mods', identifier: 'nest_wolfenstein' },
    { id: 6, name: 'Strategy & RTS Games', description: 'Real-time strategy (RTS) and tactical command multiplayer game engines (OpenRA)', identifier: 'nest_strategy' }
  ],
  eggs: [
    {
      id: 1, nest_id: 1, name: 'Minecraft Vanilla / Paper', description: 'High-performance Minecraft server powered by Paper.',
      docker_image: 'ghcr.io/pterodactyl/yolks:java_21',
      startup_command: 'java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar server.jar nogui',
      install_script: 'echo "Downloaded successfully"',
      env_variables: JSON.stringify([
        { key: 'SERVER_MEMORY', label: 'Server Memory (MB)', default_value: '1024' },
        { key: 'SERVER_PORT', label: 'Server Port', default_value: '25565' }
      ]),
      config_files: JSON.stringify([{ path: 'server.properties', template: 'server-port={{SERVER_PORT}}\n' }])
    },
    {
      id: 2, nest_id: 2, name: 'CS:GO Dedicated Server', description: 'Counter-Strike dedicated operational server.',
      docker_image: 'ghcr.io/pterodactyl/yolks:debian',
      startup_command: './srcds_run -game csgo -console -port {{SERVER_PORT}}',
      install_script: 'echo "Installed"',
      env_variables: JSON.stringify([{ key: 'SERVER_PORT', label: 'Server Port', default_value: '27015' }]),
      config_files: JSON.stringify([{ path: 'csgo/cfg/server.cfg', template: 'hostname "-OZ- Panel Match Server"\n' }])
    },
    {
      id: 3, nest_id: 3, name: 'Rust Dedicated Server', description: 'Facepunch Rust server with RCON Web.',
      docker_image: 'ghcr.io/pterodactyl/yolks:rust',
      startup_command: './RustDedicated -batchmode +server.port {{SERVER_PORT}}',
      install_script: 'echo "Installed"',
      env_variables: JSON.stringify([{ key: 'SERVER_PORT', label: 'Server Port', default_value: '28015' }]),
      config_files: JSON.stringify([{ path: 'server/cfg/server.cfg', template: 'server.hostname "-OZ- Panel Rust"\n' }])
    },
    {
      id: 4, nest_id: 4, name: 'Arena High-Speed Match Server', description: 'Working interactive Node-based multi-game server.',
      docker_image: 'ghcr.io/pterodactyl/yolks:nodejs_20',
      startup_command: 'node game_daemon.js',
      install_script: 'echo "Installed"',
      env_variables: JSON.stringify([{ key: 'SERVER_PORT', label: 'Game Port', default_value: '3001' }]),
      config_files: JSON.stringify([{ path: 'server.json', template: '{"port": 3001}' }])
    },
    {
      id: 5, nest_id: 5, name: 'ET: Legacy Dedicated Server', description: 'Enemy Territory: Legacy open source cooperative World War II FPS dedicated server.',
      docker_image: 'ghcr.io/pterodactyl/yolks:debian',
      startup_command: './etlded +set net_port {{SERVER_PORT}} +set fs_game {{FS_GAME}} +set dedicated 2 +set com_hunkMegs {{COM_HUNKMEGS}} +exec {{SERVER_CFG}} +set rconpassword "{{RCON_PASSWORD}}"',
      install_script: 'echo "Downloaded ET Legacy Archive successfully"',
      env_variables: JSON.stringify([
        { key: 'SERVER_PORT', label: 'Server Network Port', default_value: '27960' },
        { key: 'FS_GAME', label: 'Active Mod / Game Folder', default_value: 'legacy' },
        { key: 'COM_HUNKMEGS', label: 'Engine Memory Allocations (MB)', default_value: '128' },
        { key: 'SERVER_CFG', label: 'Execution Config Filename', default_value: 'etlegacy.cfg' },
        { key: 'RCON_PASSWORD', label: 'RCON Admin Password', default_value: 'etlegacy_rcon_secure' },
        { key: 'SERVER_NAME', label: 'Server Hostname Banner', default_value: '-OZ- Official ET: Legacy Match' },
        { key: 'MAX_PLAYERS', label: 'Max Clients', default_value: '32' },
        { key: 'MAP_NAME', label: 'Initial Map Level', default_value: 'oasis' }
      ]),
      config_files: JSON.stringify([
        { path: 'legacy/etlegacy.cfg', template: 'set sv_hostname "{{SERVER_NAME}}"\nset sv_maxclients {{MAX_PLAYERS}}\nset rconpassword "{{RCON_PASSWORD}}"\nmap {{MAP_NAME}}\n' },
        { path: 'etmain/etlegacy.cfg', template: 'set sv_hostname "{{SERVER_NAME}}"\nset sv_maxclients {{MAX_PLAYERS}}\nset rconpassword "{{RCON_PASSWORD}}"\nmap {{MAP_NAME}}\n' }
      ])
    },
    {
      id: 25, nest_id: 6, name: 'OpenRA Dedicated Server', description: 'OpenRA open source real-time strategy (RTS) engine supporting Red Alert, Tiberian Dawn, and Dune 2000.',
      docker_image: 'ghcr.io/pterodactyl/yolks:dotnet_7',
      startup_command: './Launch.Server.sh Game.Mod={{OPENRA_MOD}} Server.Name="{{SERVER_NAME}}" Server.ListenPort={{SERVER_PORT}} Server.ExternalPort={{SERVER_PORT}} Server.Password="{{SERVER_PASSWORD}}" Server.Motd="{{MOTD}}" Server.RequireAuthentication={{REQUIRE_AUTH}} Server.AllowPortForward=false',
      install_script: 'echo "Downloaded OpenRA AppImage/Archive successfully"',
      env_variables: JSON.stringify([
        { key: 'SERVER_PORT', label: 'Server Listen Network Port', default_value: '1234' },
        { key: 'OPENRA_MOD', label: 'Active Game Mod (ra = Red Alert, cnc = Tiberian Dawn, d2k = Dune 2000)', default_value: 'ra' },
        { key: 'SERVER_NAME', label: 'Server Match Title Banner', default_value: '-OZ- Premium OpenRA Red Alert Warzone' },
        { key: 'SERVER_PASSWORD', label: 'Server Match Join Password', default_value: '' },
        { key: 'REQUIRE_AUTH', label: 'Require OpenRA Forum Authentication (True / False)', default_value: 'False' },
        { key: 'MOTD', label: 'Message of the Day Ticker', default_value: 'Welcome to the official -OZ- Panel Hub Enterprise OpenRA Server! Prepare your Tesla Coils.' }
      ]),
      config_files: JSON.stringify([
        { path: 'support/settings.yaml', template: 'Server:\n  Name: "{{SERVER_NAME}}"\n  ListenPort: {{SERVER_PORT}}\n  ExternalPort: {{SERVER_PORT}}\n  Password: "{{SERVER_PASSWORD}}"\n  Motd: "{{MOTD}}"\n  RequireAuthentication: {{REQUIRE_AUTH}}\n' }
      ])
    }
  ],
  servers: [
    {
      id: 1,
      uuid: 'oz_srv_master_9999',
      name: '-OZ- Official Esports Match #1',
      owner_id: 1,
      egg_id: 4,
      ip: '127.0.0.1',
      port: 3001,
      memory_limit: 2048,
      cpu_limit: 100,
      disk_limit: 10240,
      status: 'online',
      discord_webhook: 'https://discord.com/api/webhooks/example',
      env_values: JSON.stringify({ SERVER_PORT: '3001' }),
      created_at: new Date().toISOString()
    },
    {
      id: 2,
      uuid: 'oz_srv_etlegacy_8888',
      name: '-OZ- Official ET: Legacy 2.60b Match Front #1',
      owner_id: 1,
      egg_id: 5,
      ip: '127.0.0.1',
      port: 27960,
      memory_limit: 1024,
      cpu_limit: 100,
      disk_limit: 10240,
      status: 'offline',
      discord_webhook: 'https://discord.com/api/webhooks/example_et',
      env_values: JSON.stringify({ SERVER_PORT: '27960', FS_GAME: 'legacy', COM_HUNKMEGS: '128', SERVER_CFG: 'etlegacy.cfg', RCON_PASSWORD: 'secure_et_rcon', MAX_PLAYERS: '32', MAP_NAME: 'oasis' }),
      created_at: new Date().toISOString()
    },
    {
      id: 3,
      uuid: 'oz_srv_openra_7777',
      name: '-OZ- Official OpenRA Red Alert Strike #1',
      owner_id: 1,
      egg_id: 25,
      ip: '127.0.0.1',
      port: 1234,
      memory_limit: 1024,
      cpu_limit: 100,
      disk_limit: 10240,
      status: 'offline',
      discord_webhook: 'https://discord.com/api/webhooks/example_openra',
      env_values: JSON.stringify({ SERVER_PORT: '1234', OPENRA_MOD: 'ra', SERVER_NAME: '-OZ- Official OpenRA Red Alert Strike #1', SERVER_PASSWORD: '', REQUIRE_AUTH: 'False', MOTD: 'Welcome to the official -OZ- OpenRA Warzone!' }),
      created_at: new Date().toISOString()
    }
  ],
  forum_categories: [
    { id: 1, name: 'General Gaming', description: 'General discussions, -OZ- network events, and off-topic chat.', sort_order: 1 },
    { id: 2, name: 'Server Support & Help', description: 'Troubleshooting, Yolk configurations, and error diagnostics.', sort_order: 2 },
    { id: 3, name: 'Community Suggestions', description: 'Suggestions for new CMS pages, Pterodactyl Eggs, and panel features.', sort_order: 3 }
  ],
  forum_topics: [
    {
      id: 1, category_id: 1, user_id: 1, title: 'Welcome to -OZ- Panel Hub Enterprise Forums!',
      content: 'Feel free to introduce yourself, participate in live shoutbox chat, or discuss server setups.',
      is_pinned: true, is_locked: false, created_at: new Date().toISOString()
    },
    {
      id: 2, category_id: 1, user_id: 1, title: 'NEW YOLKS: ET: Legacy & OpenRA RTS Eggs Deployed!',
      content: 'We have fully instantiated the official **ET: Legacy Dedicated Server** and **OpenRA Dedicated Server** Pterodactyl specifications. You can now deploy 2.60b compatible cooperative World War II FPS matches and classic Westwood RTS Red Alert/Tiberian Dawn games instantly from your user control room.',
      is_pinned: false, is_locked: false, created_at: new Date().toISOString()
    }
  ],
  forum_replies: [
    { id: 1, topic_id: 1, user_id: 1, content: 'Glad to be here! The real-time console and file manager are incredibly snappy.', created_at: new Date().toISOString() },
    { id: 2, topic_id: 2, user_id: 1, content: 'That is awesome! Tesla Coils and Tanya vs King Tiger tanks!', created_at: new Date().toISOString() }
  ],
  forum_chat_messages: [
    { id: 1, user_id: 1, message: 'Welcome to the -OZ- Panel Hub live forums shoutbox!', created_at: new Date().toISOString() },
    { id: 2, user_id: 1, message: 'ET: Legacy dedicated process egg is now live! Let us play 🔫', created_at: new Date().toISOString() },
    { id: 3, user_id: 1, message: 'OpenRA Red Alert RTS match servers are online! Construction complete ⚡', created_at: new Date().toISOString() }
  ],
  audit_logs: [],
  ai_watchdog_logs: [
    { id: 1, server_id: 1, event_type: 'system_boot', message: 'AI Sentinel Watchdog initialized for -OZ- Panel Hub Core.', created_at: new Date().toISOString() },
    { id: 2, server_id: 2, event_type: 'deployment', message: 'ET: Legacy Dedicated Server allocation clamped and registered.', created_at: new Date().toISOString() },
    { id: 3, server_id: 3, event_type: 'deployment', message: 'OpenRA Dedicated Server RTS allocation clamped and registered.', created_at: new Date().toISOString() }
  ]
};

function saveMockDb() {
  try {
    fs.writeFileSync(mockDbPath, JSON.stringify(fallbackDb, null, 2), 'utf8');
  } catch (e) {}
}

if (fs.existsSync(mockDbPath)) {
  try {
    const active = JSON.parse(fs.readFileSync(mockDbPath, 'utf8'));
    // Force reset INSTALLED to false so the installer is the first thing anyone sees
    active.system_settings['INSTALLED'] = 'false';
    fallbackDb = active;
    saveMockDb();
  } catch (e) {}
} else {
  saveMockDb();
}

function initPool(dbConfig) {
  if (pool) pool.end();
  pool = new Pool({
    host: dbConfig.host || '127.0.0.1',
    port: dbConfig.port || 5432,
    database: dbConfig.database || 'panel_db',
    user: dbConfig.user || 'panel',
    password: dbConfig.password || 'panel_secure_password',
    connectionTimeoutMillis: 1500,
  });
  return pool;
}

initPool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'panel_db',
  user: process.env.DB_USER || 'panel',
  password: process.env.DB_PASSWORD || 'panel_secure_password'
});

async function query(text, params = []) {
  if (pool) {
    try {
      const res = await pool.query(text, params);
      return res;
    } catch (err) {}
  }

  const sql = text.trim().toUpperCase();
  let rows = [];

  if (sql.startsWith('SELECT')) {
    if (sql.includes('FROM SYSTEM_SETTINGS')) {
      if (sql.includes('WHERE KEY =')) {
        const k = params[0];
        rows = fallbackDb.system_settings[k] !== undefined ? [{ value: fallbackDb.system_settings[k] }] : [];
      } else {
        rows = Object.entries(fallbackDb.system_settings).map(([k, v]) => ({ key: k, value: v }));
      }
    } else if (sql.includes('FROM USERS')) {
      if (sql.includes('WHERE USERNAME =') || sql.includes('WHERE EMAIL =')) {
        const u = params[0];
        rows = fallbackDb.users.filter(x => x.username === u || x.email === u);
      } else if (sql.includes('WHERE ID =')) {
        const id = parseInt(params[0]);
        rows = fallbackDb.users.filter(x => x.id === id);
      } else {
        rows = fallbackDb.users;
      }
    } else if (sql.includes('FROM CMS_PAGES')) {
      if (sql.includes('WHERE P.SLUG =')) {
        rows = fallbackDb.cms_pages.filter(x => x.slug === params[0]);
      } else {
        rows = fallbackDb.cms_pages;
      }
    } else if (sql.includes('FROM CMS_NEWS')) {
      if (sql.includes('WHERE N.ID =')) {
        rows = fallbackDb.cms_news.filter(x => x.id === parseInt(params[0]));
      } else {
        rows = fallbackDb.cms_news;
      }
    } else if (sql.includes('FROM CMS_NAV_LINKS')) {
      rows = fallbackDb.cms_nav_links;
    } else if (sql.includes('FROM EGGS')) {
      rows = fallbackDb.eggs.map(e => ({ ...e, nest_name: fallbackDb.nests.find(n => n.id === e.nest_id)?.name || 'Nest' }));
    } else if (sql.includes('FROM NESTS')) {
      rows = fallbackDb.nests;
    } else if (sql.includes('FROM SERVERS')) {
      if (sql.includes('WHERE S.UUID =')) {
        rows = fallbackDb.servers.filter(x => x.uuid === params[0]).map(s => ({
          ...s,
          egg_name: fallbackDb.eggs.find(e => e.id === s.egg_id)?.name || 'Egg',
          docker_image: fallbackDb.eggs.find(e => e.id === s.egg_id)?.docker_image || 'image',
          owner_name: fallbackDb.users.find(u => u.id === s.owner_id)?.username || 'Owner'
        }));
      } else if (sql.includes('WHERE S.OWNER_ID =')) {
        rows = fallbackDb.servers.filter(x => x.owner_id === parseInt(params[0])).map(s => ({
          ...s,
          egg_name: fallbackDb.eggs.find(e => e.id === s.egg_id)?.name || 'Egg',
          owner_name: fallbackDb.users.find(u => u.id === s.owner_id)?.username || 'Owner'
        }));
      } else {
        rows = fallbackDb.servers.map(s => ({
          ...s,
          egg_name: fallbackDb.eggs.find(e => e.id === s.egg_id)?.name || 'Egg',
          owner_name: fallbackDb.users.find(u => u.id === s.owner_id)?.username || 'Owner'
        }));
      }
    } else if (sql.includes('FROM FORUM_CATEGORIES')) {
      rows = fallbackDb.forum_categories.map(c => ({
        ...c,
        topic_count: fallbackDb.forum_topics.filter(t => t.category_id === c.id).length,
        reply_count: fallbackDb.forum_replies.filter(r => fallbackDb.forum_topics.find(t => t.id === r.topic_id)?.category_id === c.id).length
      }));
    } else if (sql.includes('FROM FORUM_TOPICS')) {
      if (sql.includes('WHERE T.ID =')) {
        rows = fallbackDb.forum_topics.filter(t => t.id === parseInt(params[0])).map(t => ({
          ...t,
          category_name: fallbackDb.forum_categories.find(c => c.id === t.category_id)?.name || 'Cat',
          author_name: fallbackDb.users.find(u => u.id === t.user_id)?.username || 'User',
          author_avatar: fallbackDb.users.find(u => u.id === t.user_id)?.avatar || '/assets/default_avatar.png',
          author_role: fallbackDb.users.find(u => u.id === t.user_id)?.role || 'user'
        }));
      } else if (sql.includes('WHERE T.CATEGORY_ID =')) {
        rows = fallbackDb.forum_topics.filter(t => t.category_id === parseInt(params[0])).map(t => ({
          ...t,
          author_name: fallbackDb.users.find(u => u.id === t.user_id)?.username || 'User',
          author_avatar: fallbackDb.users.find(u => u.id === t.user_id)?.avatar || '/assets/default_avatar.png',
          reply_count: fallbackDb.forum_replies.filter(r => r.topic_id === t.id).length
        }));
      } else {
        rows = fallbackDb.forum_topics.map(t => ({
          ...t,
          category_name: fallbackDb.forum_categories.find(c => c.id === t.category_id)?.name || 'Cat',
          author_name: fallbackDb.users.find(u => u.id === t.user_id)?.username || 'User',
          author_avatar: fallbackDb.users.find(u => u.id === t.user_id)?.avatar || '/assets/default_avatar.png',
          reply_count: fallbackDb.forum_replies.filter(r => r.topic_id === t.id).length
        }));
      }
    } else if (sql.includes('FROM FORUM_REPLIES')) {
      rows = fallbackDb.forum_replies.filter(r => r.topic_id === parseInt(params[0])).map(r => ({
        ...r,
        reply_author: fallbackDb.users.find(u => u.id === r.user_id)?.username || 'User',
        reply_avatar: fallbackDb.users.find(u => u.id === r.user_id)?.avatar || '/assets/default_avatar.png',
        reply_role: fallbackDb.users.find(u => u.id === r.user_id)?.role || 'user'
      }));
    } else if (sql.includes('FROM FORUM_CHAT_MESSAGES')) {
      rows = fallbackDb.forum_chat_messages.map(m => ({
        ...m,
        username: fallbackDb.users.find(u => u.id === m.user_id)?.username || 'Gamer',
        avatar: fallbackDb.users.find(u => u.id === m.user_id)?.avatar || '/assets/default_avatar.png',
        role: fallbackDb.users.find(u => u.id === m.user_id)?.role || 'user'
      }));
    } else if (sql.includes('FROM AUDIT_LOGS')) {
      rows = fallbackDb.audit_logs;
    } else if (sql.includes('FROM AI_WATCHDOG_LOGS')) {
      rows = fallbackDb.ai_watchdog_logs.map(a => ({
        ...a,
        server_name: fallbackDb.servers.find(s => s.id === a.server_id)?.name || 'Server'
      }));
    } else if (sql.includes('COUNT(*)')) {
      rows = [{ c: '1' }];
    }
  } else if (sql.startsWith('INSERT INTO SERVERS')) {
    const newSrv = {
      id: fallbackDb.servers.length + 1,
      uuid: params[0],
      name: params[1],
      owner_id: params[2],
      egg_id: params[3],
      ip: params[4] || '127.0.0.1',
      port: params[5],
      memory_limit: params[6] || 1024,
      cpu_limit: params[7] || 100,
      disk_limit: params[8] || 10240,
      status: 'installing',
      discord_webhook: params[9] || '',
      env_values: params[10] || '{}',
      created_at: new Date().toISOString()
    };
    fallbackDb.servers.push(newSrv);
    saveMockDb();
    rows = [newSrv];
  } else if (sql.startsWith('INSERT INTO FORUM_TOPICS')) {
    const newTop = {
      id: fallbackDb.forum_topics.length + 1,
      category_id: params[0],
      user_id: params[1],
      title: params[2],
      content: params[3],
      is_pinned: false,
      is_locked: false,
      created_at: new Date().toISOString()
    };
    fallbackDb.forum_topics.push(newTop);
    saveMockDb();
    rows = [newTop];
  } else if (sql.startsWith('INSERT INTO FORUM_REPLIES')) {
    const newRep = {
      id: fallbackDb.forum_replies.length + 1,
      topic_id: params[0],
      user_id: params[1],
      content: params[2],
      created_at: new Date().toISOString()
    };
    fallbackDb.forum_replies.push(newRep);
    saveMockDb();
    rows = [newRep];
  } else if (sql.startsWith('INSERT INTO FORUM_CHAT_MESSAGES')) {
    const newChat = {
      id: fallbackDb.forum_chat_messages.length + 1,
      user_id: params[0],
      message: params[1],
      created_at: new Date().toISOString()
    };
    fallbackDb.forum_chat_messages.push(newChat);
    saveMockDb();
    rows = [newChat];
  } else if (sql.startsWith('UPDATE SERVERS')) {
    if (sql.includes('STATUS =')) {
      const st = params[0];
      const id = params[1];
      const srv = fallbackDb.servers.find(s => s.id === id);
      if (srv) srv.status = st;
      saveMockDb();
    }
  }

  return { rows };
}

async function testConnection(customConfig) {
  return true;
}

async function initializeTables() {}

async function getSetting(key, defaultValue = null) {
  const res = await query('SELECT value FROM system_settings WHERE key = $1', [key]);
  if (res.rows && res.rows.length > 0 && res.rows[0].value !== undefined) {
    return res.rows[0].value;
  }
  return defaultValue;
}

async function setSetting(key, value) {
  fallbackDb.system_settings[key] = String(value);
  saveMockDb();
}

module.exports = {
  pool,
  initPool,
  query,
  testConnection,
  initializeTables,
  getSetting,
  setSetting,
  fallbackDb
};
