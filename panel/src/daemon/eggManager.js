const fs = require('fs');
const path = require('path');
const { query } = require('../database/schema');

async function seedEggs() {
  const eggsDir = path.join(__dirname, '../../eggs');
  if (!fs.existsSync(eggsDir)) return;

  const files = fs.readdirSync(eggsDir).filter(f => f.endsWith('.json'));

  for (const file of files) {
    try {
      const content = fs.readFileSync(path.join(eggsDir, file), 'utf8');
      const eggData = JSON.parse(content);

      // 1. Ensure Nest exists
      let nestId = null;
      const nestRes = await query('SELECT id FROM nests WHERE identifier = $1', [eggData.nest_identifier]);
      if (nestRes.rows && nestRes.rows.length > 0) {
        nestId = nestRes.rows[0].id;
      } else {
        const insertNest = await query(
          'INSERT INTO nests (name, description, identifier) VALUES ($1, $2, $3) RETURNING id',
          [eggData.nest, eggData.nest_description || 'No description', eggData.nest_identifier]
        );
        if (insertNest.rows && insertNest.rows.length > 0) {
          nestId = insertNest.rows[0].id;
        }
      }

      // 2. Ensure Egg exists
      if (nestId !== null) {
        const eggRes = await query('SELECT id FROM eggs WHERE nest_id = $1 AND name = $2', [nestId, eggData.name]);
        if (eggRes.rows && eggRes.rows.length === 0) {
          await query(
            `INSERT INTO eggs (nest_id, name, description, docker_image, startup_command, install_script, env_variables, config_files)
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
            [
              nestId,
              eggData.name,
              eggData.description || '',
              eggData.docker_image || 'ghcr.io/pterodactyl/yolks:debian',
              eggData.startup_command,
              eggData.install_script || '',
              JSON.stringify(eggData.env_variables || []),
              JSON.stringify(eggData.config_files || [])
            ]
          );
          console.log(`[EggManager] Seeded new Egg: "${eggData.name}" under Nest "${eggData.nest}"`);
        }
      }
    } catch (err) {
      console.error(`[EggManager] Error seeding egg from ${file}:`, err.message);
    }
  }
}

// Dynamically read all eggs from the disk repository for high-speed robust mock/production parsing
async function getAllEggs() {
  const eggsDir = path.join(__dirname, '../../eggs');
  if (!fs.existsSync(eggsDir)) return [];

  const files = fs.readdirSync(eggsDir).filter(f => f.endsWith('.json'));
  const dynamicEggs = [];
  let eggCounter = 1;

  for (const file of files) {
    try {
      const content = fs.readFileSync(path.join(eggsDir, file), 'utf8');
      const data = JSON.parse(content);
      dynamicEggs.push({
        id: eggCounter++,
        nest_id: data.nest_identifier === 'nest_minecraft' ? 1 : data.nest_identifier === 'nest_source' ? 2 : data.nest_identifier === 'nest_survival' ? 3 : data.nest_identifier === 'nest_wolfenstein' ? 5 : 4,
        nest_name: data.nest,
        nest_identifier: data.nest_identifier,
        name: data.name,
        description: data.description || '',
        docker_image: data.docker_image || 'ghcr.io/pterodactyl/yolks:debian',
        startup_command: data.startup_command,
        install_script: data.install_script || '',
        env_variables: typeof data.env_variables === 'string' ? data.env_variables : JSON.stringify(data.env_variables || []),
        config_files: typeof data.config_files === 'string' ? data.config_files : JSON.stringify(data.config_files || [])
      });
    } catch (e) {}
  }

  // Sort by nest name, then egg name
  dynamicEggs.sort((a, b) => a.nest_name.localeCompare(b.nest_name) || a.name.localeCompare(b.name));
  return dynamicEggs;
}

async function getNests() {
  const res = await query('SELECT * FROM nests ORDER BY name');
  return res.rows || [];
}

module.exports = {
  seedEggs,
  getAllEggs,
  getNests
};
