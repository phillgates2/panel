from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, abort
from flask import g
from werkzeug.utils import secure_filename
from ..app import db
from datetime import datetime

cms_bp = Blueprint('cms', __name__, url_prefix='/cms')


class Page(db.Model):
    __tablename__ = 'cms_page'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    updated_at = db.Column(db.DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())


@cms_bp.route('/')
def index():
    pages = db.session.query(Page).order_by(Page.title).all()
    return render_template('cms/index.html', pages=pages)


@cms_bp.route('/<slug>')
def view(slug):
    page = db.session.query(Page).filter_by(slug=slug).first()
    if not page:
        abort(404)
    return render_template('cms/view.html', page=page)


@cms_bp.route('/create', methods=['GET', 'POST'])
def create():
    # Placeholder admin check
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip()
        content = request.form.get('content', '')
        if not title or not slug:
            flash('Title and slug are required', 'error')
            return redirect(url_for('cms.create'))
        p = Page(title=title, slug=slug, content=content)
        db.session.add(p)
        db.session.commit()
        flash('Page created', 'success')
        return redirect(url_for('cms.view', slug=slug))
    return render_template('cms/create.html')
