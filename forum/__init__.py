from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    session,
)
from app import db, verify_csrf
from datetime import datetime

forum_bp = Blueprint('forum', __name__, url_prefix='/forum')


def admin_required(fn):
    def wrapped(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('cms.admin_login', next=request.path))
        return fn(*args, **kwargs)
    wrapped.__name__ = getattr(fn, '__name__', 'wrapped')
    return wrapped


class Thread(db.Model):
    __tablename__ = 'forum_thread'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow())


class Post(db.Model):
    __tablename__ = 'forum_post'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('forum_thread.id'), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow())

    thread = db.relationship('Thread', backref='posts')


@forum_bp.route('/')
def index():
    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    per_page = int(current_app.config.get('FORUM_PER_PAGE', 10))
    q = db.session.query(Thread).order_by(Thread.created_at.desc())
    total = q.count()
    threads = q.offset((page-1)*per_page).limit(per_page).all()
    return render_template('forum/index.html', threads=threads, page=page, per_page=per_page, total=total)


@forum_bp.route('/thread/<int:thread_id>')
def view_thread(thread_id):
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)
    # paginate replies
    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    per_page = int(current_app.config.get('FORUM_REPLIES_PER_PAGE', 20))
    q = db.session.query(Post).filter_by(thread_id=thread_id).order_by(Post.created_at.asc())
    total = q.count()
    posts = q.offset((page-1)*per_page).limit(per_page).all()
    # optional markdown for posts
    try:
        from markdown import markdown as md
        for p in posts:
            p._html = md(p.content or '')
    except Exception:
        for p in posts:
            p._html = p.content
    return render_template('forum/thread.html', thread=thread, posts=posts, page=page, per_page=per_page, total=total)


@forum_bp.route('/thread/<int:thread_id>/reply', methods=['POST'])
def reply_thread(thread_id):
    thread = db.session.get(Thread, thread_id)
    if not thread:
        abort(404)
    # CSRF protection
    try:
        verify_csrf()
    except Exception:
        flash('Invalid CSRF token', 'error')
        return redirect(url_for('forum.view_thread', thread_id=thread_id))

    author = request.form.get('author', 'anonymous').strip()
    content = request.form.get('content', '').strip()
    if not content:
        flash('Content required', 'error')
        return redirect(url_for('forum.view_thread', thread_id=thread_id))
    p = Post(thread_id=thread_id, author=author, content=content)
    db.session.add(p)
    db.session.commit()
    flash('Reply posted', 'success')
    return redirect(url_for('forum.view_thread', thread_id=thread_id))


@forum_bp.route('/thread/create', methods=['GET', 'POST'])
@admin_required
def create_thread():
    if request.method == 'POST':
        # CSRF protection
        try:
            verify_csrf()
        except Exception:
            flash('Invalid CSRF token', 'error')
            return redirect(url_for('forum.create_thread'))

        title = request.form.get('title', '').strip()
        author = request.form.get('author', 'anonymous').strip()
        content = request.form.get('content', '').strip()
        if not title or not content:
            flash('Title and content required', 'error')
            return redirect(url_for('forum.create_thread'))
        t = Thread(title=title)
        db.session.add(t)
        db.session.flush()
        p = Post(thread_id=t.id, author=author, content=content)
        db.session.add(p)
        db.session.commit()
        flash('Thread created', 'success')
        return redirect(url_for('forum.view_thread', thread_id=t.id))
    return render_template('forum/create_thread.html')


@forum_bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_post(post_id):
    p = db.session.get(Post, post_id)
    if not p:
        abort(404)
    if request.method == 'POST':
        try:
            verify_csrf()
        except Exception:
            flash('Invalid CSRF token', 'error')
            return redirect(url_for('forum.view_thread', thread_id=p.thread_id))
        p.content = request.form.get('content', p.content)
        db.session.commit()
        flash('Post updated', 'success')
        return redirect(url_for('forum.view_thread', thread_id=p.thread_id))
    return render_template('forum/edit_post.html', post=p)


@forum_bp.route('/post/<int:post_id>/delete', methods=['POST'])
@admin_required
def delete_post(post_id):
    p = db.session.get(Post, post_id)
    if not p:
        abort(404)
    try:
        verify_csrf()
    except Exception:
        flash('Invalid CSRF token', 'error')
        return redirect(url_for('forum.view_thread', thread_id=p.thread_id))
    thread_id = p.thread_id
    db.session.delete(p)
    db.session.commit()
    flash('Post deleted', 'success')
    return redirect(url_for('forum.view_thread', thread_id=thread_id))


@forum_bp.route('/thread/<int:thread_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_thread(thread_id):
    t = db.session.get(Thread, thread_id)
    if not t:
        abort(404)
    if request.method == 'POST':
        try:
            verify_csrf()
        except Exception:
            flash('Invalid CSRF token', 'error')
            return redirect(url_for('forum.view_thread', thread_id=thread_id))
        t.title = request.form.get('title', t.title)
        db.session.commit()
        flash('Thread updated', 'success')
        return redirect(url_for('forum.view_thread', thread_id=thread_id))
    return render_template('forum/edit_thread.html', thread=t)


@forum_bp.route('/thread/<int:thread_id>/delete', methods=['POST'])
@admin_required
def delete_thread(thread_id):
    t = db.session.get(Thread, thread_id)
    if not t:
        abort(404)
    try:
        verify_csrf()
    except Exception:
        flash('Invalid CSRF token', 'error')
        return redirect(url_for('forum.view_thread', thread_id=thread_id))
    # delete posts first
    db.session.query(Post).filter_by(thread_id=thread_id).delete()
    db.session.delete(t)
    db.session.commit()
    flash('Thread deleted', 'success')
    return redirect(url_for('forum.index'))
