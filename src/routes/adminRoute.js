const express = require('express');
const router = express.Router();
const { query, setSetting } = require('../database/schema');
const { requireAdmin, logAudit } = require('../security/security');
const { seedEggs, getAllEggs } = require('../daemon/eggManager');

router.get('/', requireAdmin, async (req, res) => {
  const user = req.session.user;

  try {
    const usersRes = await query('SELECT * FROM users ORDER BY created_at DESC');
    const pagesRes = await query('SELECT p.*, u.username AS author_name FROM cms_pages p LEFT JOIN users u ON p.author_id = u.id ORDER BY p.created_at DESC');
    const newsRes = await query('SELECT n.*, u.username AS author_name FROM cms_news n LEFT JOIN users u ON n.author_id = u.id ORDER BY n.created_at DESC');
    const navRes = await query('SELECT * FROM cms_nav_links ORDER BY sort_order');
    const settingsRes = await query('SELECT * FROM system_settings ORDER BY key');
    const allEggs = await getAllEggs();

    const settingsMap = {};
    if (settingsRes.rows) {
      settingsRes.rows.forEach(r => settingsMap[r.key] = r.value);
    }

    res.render('admin_dashboard', {
      user,
      users: usersRes.rows || [],
      cmsPages: pagesRes.rows || [],
      cmsNews: newsRes.rows || [],
      navLinks: navRes.rows || [],
      settings: settingsMap,
      eggs: allEggs,
      activeTab: req.query.tab || 'overview',
      success: req.query.success || null,
      error: req.query.error || null
    });

  } catch (err) {
    console.error('[Admin] Error loading master dashboard:', err);
    res.status(500).send('Internal Server Error');
  }
});

router.post('/users/:id/role', requireAdmin, async (req, res) => {
  const userId = parseInt(req.params.id);
  const { role } = req.body;
  try {
    await query('UPDATE users SET role = $1 WHERE id = $2', [role, userId]);
    await logAudit(req.session.user.id, 'admin_update_user_role', req, `Updated user ${userId} to role ${role}`);
    res.redirect('/admin?tab=users&success=User role updated successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=users&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/users/:id/delete', requireAdmin, async (req, res) => {
  const userId = parseInt(req.params.id);
  try {
    await query('DELETE FROM users WHERE id = $1', [userId]);
    await logAudit(req.session.user.id, 'admin_delete_user', req, `Deleted user ${userId}`);
    res.redirect('/admin?tab=users&success=User deleted successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=users&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/cms/page', requireAdmin, async (req, res) => {
  const { slug, title, content, meta_description } = req.body;
  try {
    await query(`
      INSERT INTO cms_pages (slug, title, content, meta_description, author_id)
      VALUES ($1, $2, $3, $4, $5)
      ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title, content = EXCLUDED.content, meta_description = EXCLUDED.meta_description
    `, [slug, title, content, meta_description, req.session.user.id]);

    await logAudit(req.session.user.id, 'admin_save_cms_page', req, `Saved CMS page ${slug}`);
    res.redirect('/admin?tab=cms_pages&success=CMS web page published successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=cms_pages&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/cms/page/:id/delete', requireAdmin, async (req, res) => {
  try {
    await query('DELETE FROM cms_pages WHERE id = $1', [parseInt(req.params.id)]);
    res.redirect('/admin?tab=cms_pages&success=CMS web page deleted successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=cms_pages&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/cms/news', requireAdmin, async (req, res) => {
  const { title, summary, content, image_url } = req.body;
  try {
    await query(`
      INSERT INTO cms_news (title, summary, content, image_url, author_id)
      VALUES ($1, $2, $3, $4, $5)
    `, [title, summary, content, image_url || '/assets/news_default.jpg', req.session.user.id]);

    await logAudit(req.session.user.id, 'admin_publish_news', req, `Published announcement ${title}`);
    res.redirect('/admin?tab=cms_news&success=News article published successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=cms_news&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/cms/news/:id/delete', requireAdmin, async (req, res) => {
  try {
    await query('DELETE FROM cms_news WHERE id = $1', [parseInt(req.params.id)]);
    res.redirect('/admin?tab=cms_news&success=News announcement deleted successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=cms_news&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/cms/nav', requireAdmin, async (req, res) => {
  const { label, url, target, sort_order } = req.body;
  try {
    await query('INSERT INTO cms_nav_links (label, url, target, sort_order) VALUES ($1, $2, $3, $4)', [
      label, url, target || '_self', parseInt(sort_order || 0)
    ]);
    res.redirect('/admin?tab=nav&success=Custom navigation widget link added successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=nav&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/cms/nav/:id/delete', requireAdmin, async (req, res) => {
  try {
    await query('DELETE FROM cms_nav_links WHERE id = $1', [parseInt(req.params.id)]);
    res.redirect('/admin?tab=nav&success=Navigation link deleted successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=nav&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/brand', requireAdmin, async (req, res) => {
  const { site_title, site_motd, social_discord, social_twitter, social_github, web_hostname } = req.body;
  try {
    await setSetting('SITE_TITLE', site_title);
    await setSetting('SITE_MOTD', site_motd);
    await setSetting('SOCIAL_DISCORD', social_discord);
    await setSetting('SOCIAL_TWITTER', social_twitter);
    await setSetting('SOCIAL_GITHUB', social_github);
    await setSetting('WEB_HOSTNAME', web_hostname);

    await logAudit(req.session.user.id, 'admin_update_brand', req);
    res.redirect('/admin?tab=settings&success=Brand settings and social URLs updated successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=settings&error=${encodeURIComponent(err.message)}`);
  }
});

router.post('/eggs/reseed', requireAdmin, async (req, res) => {
  try {
    await seedEggs();
    res.redirect('/admin?tab=eggs&success=Pterodactyl Game Eggs re-seeded and verified successfully!');
  } catch (err) {
    res.redirect(`/admin?tab=eggs&error=${encodeURIComponent(err.message)}`);
  }
});

module.exports = router;
