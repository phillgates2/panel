const express = require('express');
const router = express.Router();
const { query } = require('../database/schema');

router.get('/', async (req, res) => {
  try {
    // Fetch News Stories
    const newsRes = await query('SELECT n.*, u.username AS author_name FROM cms_news n LEFT JOIN users u ON n.author_id = u.id WHERE n.is_published = TRUE ORDER BY n.created_at DESC LIMIT 6');
    // Fetch Published Custom Pages for Sidebar/Header
    const pagesRes = await query('SELECT slug, title, meta_description FROM cms_pages WHERE is_published = TRUE ORDER BY title');
    // Fetch Quick Public Server Roster
    const serversRes = await query('SELECT s.name, s.ip, s.port, s.status, e.name AS egg_name FROM servers s JOIN eggs e ON s.egg_id = e.id WHERE s.status = $1 LIMIT 8', ['online']);

    res.render('index', {
      news: newsRes.rows,
      pages: pagesRes.rows,
      publicServers: serversRes.rows
    });
  } catch (err) {
    console.error('[CMS] Error fetching home data:', err);
    res.render('index', { news: [], pages: [], publicServers: [] });
  }
});

router.get('/page/:slug', async (req, res) => {
  try {
    const pageRes = await query('SELECT p.*, u.username AS author_name FROM cms_pages p LEFT JOIN users u ON p.author_id = u.id WHERE p.slug = $1 AND p.is_published = TRUE', [req.params.slug]);
    if (pageRes.rows.length === 0) {
      return res.status(404).render('404', { message: 'Custom web page not found or unpublished.' });
    }
    
    res.render('cms_page', { page: pageRes.rows[0] });
  } catch (err) {
    console.error('[CMS] Error fetching custom page:', err);
    res.status(500).send('Internal Server Error');
  }
});

router.get('/news/:id', async (req, res) => {
  try {
    const newsRes = await query('SELECT n.*, u.username AS author_name FROM cms_news n LEFT JOIN users u ON n.author_id = u.id WHERE n.id = $1 AND n.is_published = TRUE', [req.params.id]);
    if (newsRes.rows.length === 0) {
      return res.status(404).render('404', { message: 'News announcement not found.' });
    }
    
    res.render('cms_news_detail', { article: newsRes.rows[0] });
  } catch (err) {
    console.error('[CMS] Error fetching news:', err);
    res.status(500).send('Internal Server Error');
  }
});

module.exports = router;
