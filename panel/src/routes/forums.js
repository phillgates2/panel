const express = require('express');
const router = express.Router();
const { query } = require('../database/schema');
const { requireAuth } = require('../security/security');

// 1. Forum Portal Main View (With Interactive Real-Time Live Chat Feature)
router.get('/', async (req, res) => {
  const user = req.session ? req.session.user : null;

  try {
    // Ensure default categories exist if none
    const catCheck = await query('SELECT COUNT(*) AS c FROM forum_categories');
    if (catCheck.rows[0].c === '0') {
      await query("INSERT INTO forum_categories (name, description, sort_order) VALUES ('General Gaming', 'General discussions, game announcements, and off-topic chat.', 1)");
      await query("INSERT INTO forum_categories (name, description, sort_order) VALUES ('Server Support & Help', 'Troubleshooting, Yolk configurations, and server error diagnostics.', 2)");
      await query("INSERT INTO forum_categories (name, description, sort_order) VALUES ('Community Suggestions', 'Suggestions for new CMS pages, Pterodactyl Eggs, and panel features.', 3)");
    }

    // Fetch Categories with topic and reply counts
    const categoriesRes = await query(`
      SELECT c.*, 
             (SELECT COUNT(*) FROM forum_topics WHERE category_id = c.id) AS topic_count,
             (SELECT COUNT(*) FROM forum_replies r JOIN forum_topics t ON r.topic_id = t.id WHERE t.category_id = c.id) AS reply_count
      FROM forum_categories c 
      ORDER BY c.sort_order
    `);

    // Fetch Recent Topics
    const recentTopicsRes = await query(`
      SELECT t.*, c.name AS category_name, u.username AS author_name, u.avatar AS author_avatar,
             (SELECT COUNT(*) FROM forum_replies WHERE topic_id = t.id) AS reply_count
      FROM forum_topics t
      JOIN forum_categories c ON t.category_id = c.id
      JOIN users u ON t.user_id = u.id
      ORDER BY t.created_at DESC 
      LIMIT 10
    `);

    // Fetch Recent Chat Messages for the built-in Forums Chat Shoutbox
    const chatRes = await query(`
      SELECT m.*, u.username, u.avatar, u.role 
      FROM forum_chat_messages m 
      JOIN users u ON m.user_id = u.id 
      ORDER BY m.created_at DESC 
      LIMIT 30
    `);

    res.render('forums', {
      user,
      categories: categoriesRes.rows,
      recentTopics: recentTopicsRes.rows,
      chatMessages: chatRes.rows.reverse(),
      error: req.query.error || null,
      success: req.query.success || null
    });

  } catch (err) {
    console.error('[Forums] Error loading forum homepage:', err);
    res.status(500).send('Internal Server Error');
  }
});

// 2. Category Topics List View
router.get('/category/:id', async (req, res) => {
  const user = req.session ? req.session.user : null;
  const categoryId = parseInt(req.params.id);

  try {
    const catRes = await query('SELECT * FROM forum_categories WHERE id = $1', [categoryId]);
    if (catRes.rows.length === 0) return res.status(404).render('404', { message: 'Forum Category Not Found.' });
    const category = catRes.rows[0];

    const topicsRes = await query(`
      SELECT t.*, u.username AS author_name, u.avatar AS author_avatar,
             (SELECT COUNT(*) FROM forum_replies WHERE topic_id = t.id) AS reply_count
      FROM forum_topics t
      JOIN users u ON t.user_id = u.id
      WHERE t.category_id = $1
      ORDER BY t.is_pinned DESC, t.created_at DESC
    `, [categoryId]);

    res.render('forum_category', {
      user,
      category,
      topics: topicsRes.rows
    });
  } catch (err) {
    console.error('[Forums] Category Error:', err);
    res.status(500).send('Internal Server Error');
  }
});

// 3. New Topic Wizard View
router.get('/new', requireAuth, async (req, res) => {
  const user = req.session.user;
  try {
    const categoriesRes = await query('SELECT * FROM forum_categories ORDER BY sort_order');
    res.render('forum_new_topic', {
      user,
      categories: categoriesRes.rows,
      selectedCategoryId: req.query.category_id || null
    });
  } catch (err) {
    res.status(500).send('Internal Server Error');
  }
});

router.post('/new', requireAuth, async (req, res) => {
  const { category_id, title, content } = req.body;
  const user = req.session.user;

  try {
    const insertTopic = await query(`
      INSERT INTO forum_topics (category_id, user_id, title, content)
      VALUES ($1, $2, $3, $4) RETURNING id
    `, [parseInt(category_id), user.id, title, content]);

    res.redirect(`/forums/topic/${insertTopic.rows[0].id}?success=Topic published successfully!`);
  } catch (err) {
    res.redirect(`/forums?error=Failed to publish topic: ${encodeURIComponent(err.message)}`);
  }
});

// 4. Topic Conversation & Replies View
router.get('/topic/:id', async (req, res) => {
  const user = req.session ? req.session.user : null;
  const topicId = parseInt(req.params.id);

  try {
    const topicRes = await query(`
      SELECT t.*, c.name AS category_name, c.id AS category_id, u.username AS author_name, u.avatar AS author_avatar, u.role AS author_role
      FROM forum_topics t
      JOIN forum_categories c ON t.category_id = c.id
      JOIN users u ON t.user_id = u.id
      WHERE t.id = $1
    `, [topicId]);

    if (topicRes.rows.length === 0) return res.status(404).render('404', { message: 'Topic Not Found.' });
    const topic = topicRes.rows[0];

    const repliesRes = await query(`
      SELECT r.*, u.username AS reply_author, u.avatar AS reply_avatar, u.role AS reply_role
      FROM forum_replies r
      JOIN users u ON r.user_id = u.id
      WHERE r.topic_id = $1
      ORDER BY r.created_at ASC
    `, [topicId]);

    res.render('forum_topic', {
      user,
      topic,
      replies: repliesRes.rows,
      success: req.query.success || null,
      error: req.query.error || null
    });
  } catch (err) {
    console.error('[Forums] Topic Error:', err);
    res.status(500).send('Internal Server Error');
  }
});

router.post('/topic/:id/reply', requireAuth, async (req, res) => {
  const user = req.session.user;
  const topicId = parseInt(req.params.id);
  const { content } = req.body;

  try {
    await query(`
      INSERT INTO forum_replies (topic_id, user_id, content)
      VALUES ($1, $2, $3)
    `, [topicId, user.id, content]);

    res.redirect(`/forums/topic/${topicId}?success=Reply posted successfully!`);
  } catch (err) {
    res.redirect(`/forums/topic/${topicId}?error=Reply Exception: ${encodeURIComponent(err.message)}`);
  }
});

module.exports = router;
