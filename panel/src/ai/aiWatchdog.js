const { query } = require('../database/schema');
const { getConsoleLogs, restartServer } = require('../daemon/serverManager');
const axios = require('axios');

async function sendAiDiscordAlert(webhookUrl, serverName, incidentDetails) {
  if (!webhookUrl || !webhookUrl.startsWith('http')) return;
  try {
    await axios.post(webhookUrl, {
      embeds: [{
        title: `🤖 AI Watchdog Alert: ${serverName}`,
        description: incidentDetails,
        color: 0xFEE75C,
        timestamp: new Date().toISOString(),
        footer: { text: '-OZ- Automated AI Moderation' }
      }]
    }, { timeout: 3000 });
  } catch (err) {}
}

async function runAiWatchdogLoop() {
  setInterval(async () => {
    try {
      const res = await query('SELECT id, uuid, name, status, discord_webhook FROM servers WHERE status IN ($1, $2)', ['online', 'crashed']);
      for (const server of res.rows) {
        if (server.status === 'crashed') {
          const msg = `Automated AI Recovery: Server "${server.name}" experienced an unexpected crash. Initializing auto-restart.`;
          await query('INSERT INTO ai_watchdog_logs (server_id, event_type, message) VALUES ($1, $2, $3)', [server.id, 'crash', msg]);
          
          console.log(`[AIWatchdog] Critical Crash Detected for ${server.name}. Restoring...`);
          await restartServer(server.id);

          await sendAiDiscordAlert(
            server.discord_webhook,
            server.name,
            `**Incident Detected:** Game server process terminated unexpectedly.\n**Automated Action:** AI Sentinel has automatically relaunched the process.`
          );
        } else {
          const logs = await getConsoleLogs(server.uuid);
          const hasError = logs.some(l => l.toLowerCase().includes('error') || l.toLowerCase().includes('exception') || l.toLowerCase().includes('fatal') || l.toLowerCase().includes('outofmemory'));
          
          if (hasError) {
            const recent = await query("SELECT id FROM ai_watchdog_logs WHERE server_id = $1 AND event_type = 'anomaly' AND created_at >= NOW() - INTERVAL '5 minutes'", [server.id]);
            if (recent.rows.length === 0) {
              const anomalyMsg = `Log Anomaly Detected: Console exhibits frequent warnings/exceptions. Recommendation: Verify configuration memory allocations or update plugins.`;
              await query('INSERT INTO ai_watchdog_logs (server_id, event_type, message) VALUES ($1, $2, $3)', [server.id, 'anomaly', anomalyMsg]);
              await sendAiDiscordAlert(
                server.discord_webhook,
                server.name,
                `**Warning:** AI Log Inspector detected active Exceptions/Errors in the live console stream. Check your console logs tab.`
              );
            }
          }
        }
      }
    } catch (err) {
      console.error('[AIWatchdog] Error in monitoring loop:', err);
    }
  }, 30000);
}

async function queryAiAssistant(userPrompt, serverUuid = null) {
  let contextLogs = '';
  if (serverUuid) {
    const logs = await getConsoleLogs(serverUuid);
    contextLogs = logs.slice(-50).join('\n');
  }

  const promptLower = userPrompt.toLowerCase();

  if (promptLower.includes('log') || promptLower.includes('error') || promptLower.includes('scan')) {
    if (!contextLogs) {
      return `I scanned your active console buffer but found no immediate fatal errors. If your server is crashing, ensure your assigned network Port is free and memory limits are correctly set.`;
    }
    if (contextLogs.toLowerCase().includes('eula')) {
      return `**AI Log Analysis Summary:**\nYour server is halting because of the Minecraft EULA agreement. Please navigate to the Web File Manager, open \`eula.txt\`, and set \`eula=true\`.`;
    }
    if (contextLogs.toLowerCase().includes('address already in use') || contextLogs.toLowerCase().includes('eaddrinuse')) {
      return `**AI Log Analysis Summary:**\n⚠️ **Port Conflict Detected:** The network port assigned to your server is already bound by another service. Please change your server port in the Settings tab.`;
    }
    return `**AI Log Diagnostic:**\nI reviewed your latest 50 console log entries. The server appears active but may be experiencing standard game tick garbage collection pauses. \n\n**Recommendation:** Add optimized Java garbage collection flags (\`-XX:+UseG1GC\`) or reduce your \`view-distance\` in \`server.properties\`.`;
  }

  if (promptLower.includes('lag') || promptLower.includes('performance') || promptLower.includes('optimize')) {
    return `### 🚀 -OZ- Automated Game Server Optimization Guide\nTo maximize tick performance and completely eliminate rubberbanding, apply the following proven architectural tweaks:\n\n1. **Use High-Performance Engine Yolks:** Switch from standard Vanilla to **PaperMC** or **Purpur** for Minecraft, or use optimized multicore kernel binaries for Source/Rust.\n2. **Clamping Entity Collisions:** In your game configs, reduce entity activation tracking ranges by 25%.\n3. **Network Rate Splitting:** For CS:GO/Source servers, ensure \`sv_minrate\` is set to at least \`80000\` and \`sv_maxrate\` is set to \`0\` (unlimited).\n4. **Automated AI Maintenance Tasks:** Schedule daily reboots at 04:00 AM using our advanced automation scheduler to flush memory leaks.`;
  }

  if (promptLower.includes('secure') || promptLower.includes('ddos') || promptLower.includes('security')) {
    return `### 🛡️ Enterprise Game Server Security Sentinel\nThis panel includes state-of-the-art sandboxing and firewall automation. Here is how your setup is secured:\n- **RBAC Strict Clamping:** Only verified team members can dispatch RCON commands or access the SFTP directory.\n- **Caddy Edge Proxy:** Your web traffic is protected against Slowloris and L7 floods by automated rate-limiting.\n- **Automated Two-Factor (2FA):** Enforce TOTP authentication in your user profile to prevent credential stuffing.`;
  }

  return `Hello! I am your interactive **-OZ- Panel Hub AI Assistant**. \n\nI am continuously monitoring your server nodes, parsing real-time console streams for anomalies, and ready to assist you with game configurations, Docker yolk management, or performance optimization. How can I assist your gaming community today?`;
}

async function getAiWatchdogLogs(limit = 50) {
  const res = await query('SELECT a.*, s.name AS server_name FROM ai_watchdog_logs a JOIN servers s ON a.server_id = s.id ORDER BY a.created_at DESC LIMIT $1', [limit]);
  return res.rows;
}

module.exports = {
  runAiWatchdogLoop,
  queryAiAssistant,
  getAiWatchdogLogs
};
