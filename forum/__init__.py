from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, abort
from ..app import db
from datetime import datetime

forum_bp = Blueprint('forum', __name__, url_prefix='/forum')


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
    threads = db.session.query(Thread).order_by(Thread.created_at.desc()).all()
    return render_template('forum/index.html', threads=threads)


@forum_bp.route('/thread/<int:thread_id>')
def view_thread(thread_id):
    thread = db.session.query(Thread).get(thread_id)
    if not thread:
        abort(404)
    return render_template('forum/thread.html', thread=thread)


@forum_bp.route('/thread/create', methods=['GET', 'POST'])
def create_thread():
    if request.method == 'POST':
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
