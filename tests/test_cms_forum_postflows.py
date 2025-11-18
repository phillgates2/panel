import pytest
from datetime import date
from app import db, User


def create_admin(app):
    with app.app_context():
        u = User(
            first_name='Admin',
            last_name='User',
            email='admin@example.com',
            dob=date(1990, 1, 1),
            role='system_admin',
        )
        u.set_password('secret')
        db.session.add(u)
        db.session.commit()
        return u.email


def test_admin_login_and_cms_create(client, app):
    # create admin user
    user_email = create_admin(app)

    # login via CMS admin login
    rv = client.post('/cms/admin/login', data={'username': user_email, 'password': 'secret'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Logged in' in rv.data or b'Logged in as admin' in rv.data

    # create a page
    rv2 = client.post('/cms/create', data={'title': 'Test Page', 'slug': 'test-page', 'content': 'Hello world'}, follow_redirects=True)
    assert rv2.status_code == 200
    assert b'Page created' in rv2.data

    # verify the page is viewable
    rv3 = client.get('/cms/test-page')
    assert rv3.status_code == 200
    assert b'Test Page' in rv3.data


def test_forum_thread_reply_edit_delete(client, app):
    # create admin user and login
    user_email = create_admin(app)
    rv = client.post('/cms/admin/login', data={'username': user_email, 'password': 'secret'}, follow_redirects=True)
    assert rv.status_code == 200

    # create a thread
    rv2 = client.post('/forum/thread/create', data={'title': 'Thread One', 'author': 'Admin', 'content': 'First post'}, follow_redirects=True)
    assert rv2.status_code == 200
    assert b'Thread created' in rv2.data

    # find the thread id
    with app.app_context():
        # query Thread by title via direct model import
        from forum import Thread, Post
        thread = db.session.query(Thread).filter_by(title='Thread One').first()
        assert thread is not None
        tid = thread.id

    # reply to the thread
    rv3 = client.post(f'/forum/thread/{tid}/reply', data={'author': 'Replier', 'content': 'Reply content'}, follow_redirects=True)
    assert rv3.status_code == 200
    assert b'Reply posted' in rv3.data or b'Reply' in rv3.data

    # check post exists and edit it
    with app.app_context():
        from forum import Post
        post = db.session.query(Post).filter_by(thread_id=tid).order_by(Post.created_at.asc()).first()
        assert post is not None
        pid = post.id

    rv4 = client.post(f'/forum/post/{pid}/edit', data={'content': 'Edited content'}, follow_redirects=True)
    assert rv4.status_code == 200
    assert b'Post updated' in rv4.data

    rv5 = client.get(f'/forum/thread/{tid}')
    assert b'Edited content' in rv5.data

    # delete the post
    rv6 = client.post(f'/forum/post/{pid}/delete', follow_redirects=True)
    assert rv6.status_code == 200
    assert b'Post deleted' in rv6.data or b'deleted' in rv6.data

    rv7 = client.get(f'/forum/thread/{tid}')
    assert b'Edited content' not in rv7.data
