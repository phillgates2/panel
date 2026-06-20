require('dotenv').config();
const express = require('express');
const http = require('http');
const path = require('path');
const session = require('express-session');
const cookieParser = require('cookie-parser');
const cors = require('cors');
const { Server } = require('socket.io');

const { initPool, initializeTables, getSetting, setSetting, fallbackDb } = require('./database/schema');
const { startSFTPServer } = require('./sftp/sftpServer');
const { runAiWatchdogLoop } = require('./ai/aiWatchdog');
const { checkInstallerMiddleware, securityHeaders } = require('./security/security');

const app = express();
const server = http.createServer(app);

const io = new Server(server, { cors: { origin: '*' } });
global.io = io;

io.on('connection', socket => {
  socket.on('subscribe_console', uuid => {
    socket.join(`console:${uuid}`);
  });

  socket.on('subscribe_forum_chat', () => {
    socket.join('forum_chat_room');
  });
});

app.use(securityHeaders);
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());
app.use(session({
  secret: process.env.SESSION_SECRET || 'oz_panel_hub_enterprise_master_secret_2026',
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 86400000 }
}));

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use('/assets', express.static(path.join(__dirname, '../assets')));
app.use('/favicon.ico', (req, res) => res.status(204).end());

// Global Brand Middleware for EJS views
app.use(async (req, res, next) => {
  res.locals.user = req.session ? req.session.user : null;
  
  try {
    res.locals.siteTitle = await getSetting('SITE_TITLE', '-OZ- Panel Hub Enterprise');
    res.locals.siteMotd = await getSetting('SITE_MOTD', 'Next-Gen Premium Game Server Orchestrator');
    res.locals.socialDiscord = await getSetting('SOCIAL_DISCORD', 'https://discord.gg/ozpanel');
    res.locals.socialTwitter = await getSetting('SOCIAL_TWITTER', 'https://twitter.com/ozpanel');
    res.locals.socialGithub = await getSetting('SOCIAL_GITHUB', 'https://github.com/ozpanel');
    
    const { query } = require('./database/schema');
    const navRes = await query('SELECT * FROM cms_nav_links ORDER BY sort_order');
    res.locals.navLinks = navRes.rows || [];
  } catch (err) {
    res.locals.siteTitle = '-OZ- Panel Hub Enterprise';
    res.locals.siteMotd = 'Esports Hosting Core';
    res.locals.socialDiscord = 'https://discord.gg/ozpanel';
    res.locals.socialTwitter = 'https://twitter.com/ozpanel';
    res.locals.socialGithub = 'https://github.com/ozpanel';
    res.locals.navLinks = [];
  }
  next();
});

const installerRouter = require('./installer/installer');
const authRouter = require('./routes/auth');
const cmsRouter = require('./routes/cms');
const dashboardRouter = require('./routes/dashboard');
const serversRouter = require('./routes/servers');
const forumsRouter = require('./routes/forums');
const aiAssistantRouter = require('./routes/aiAssistantRoute');
const userSettingsRouter = require('./routes/userSettingsRoute');
const adminRouter = require('./routes/adminRoute');
const apiRouter = require('./routes/apiRoute');
const hardwareRouter = require('./routes/hardwareRoute');

app.use('/install', installerRouter);
app.use(checkInstallerMiddleware);

app.use('/', authRouter);
app.use('/', cmsRouter);
app.use('/dashboard', dashboardRouter);
app.use('/servers', serversRouter);
app.use('/forums', forumsRouter);
app.use('/ai-assistant', aiAssistantRouter);
app.use('/hardware', hardwareRouter);
app.use('/settings', userSettingsRouter);
app.use('/admin', adminRouter);
app.use('/api', apiRouter);

app.use((req, res) => {
  res.status(404).render('404', { message: 'The requested -OZ- Sandboxed game instance or endpoint does not exist.' });
});

// Boot Master Daemons and Web Server on Standard HTTP Port 80
const PORT = process.env.PORT || 80;
let daemonsStarted = false;

function launchServer(targetPort) {
  server.listen(targetPort, '0.0.0.0', () => {
    console.log(`[Master Sentinel] Application Core successfully initialized.`);
    console.log(`[Web Host] -OZ- Panel Hub Enterprise fully operational on http://0.0.0.0${targetPort === 80 ? '' : ':' + targetPort} (Primary IP)`);
    
    if (!daemonsStarted) {
      daemonsStarted = true;
      try {
        startSFTPServer(2022);
        runAiWatchdogLoop();
      } catch (e) {
        console.error('[Boot Warning] Embedded Daemon execution issue:', e.message);
      }
    }
  }).on('error', err => {
    if (err.code === 'EACCES') {
      console.log(`[Port Security] Binding directly to standard Port ${targetPort} requires root capabilities. Instantiating automated proxy fallback on Port 3000...`);
      launchServer(3000);
    } else {
      console.error('[Web Host Error]', err.message);
    }
  });
}

launchServer(PORT);
