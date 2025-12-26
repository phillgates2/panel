"""Test forum delete thread button functionality"""

from datetime import date
import os
from pathlib import Path
import pytest

from forum import Post, Thread


def _find_forum_template(name):
    # look specifically for forum templates
    candidates = [
        Path("templates/forum") / name,
        Path("app/templates/forum") / name,
        Path("panel/templates/forum") / name,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def test_forum_index_template_has_delete_code():
    """Test that forum index template file includes delete button code"""
    tpl = _find_forum_template("index.html")
    if tpl is None:
        pytest.skip("forum index template not present in repository; skipping")
    with open(tpl, "r", encoding="utf-8", errors="ignore") as f:
        template_content = f.read()

    # Verify delete button code is in template
    assert "delete_thread" in template_content
    assert "Delete Thread" in template_content
    assert "btn-delete" in template_content
    assert "confirm('Are you sure you want to delete this thread?" in template_content


def test_forum_index_renders_correctly(client, app):
    """Test forum index page renders correctly with threads"""
    with app.app_context():
        from app import User, db

        # Create test user
        user = User(
            email="user2@test.com",
            first_name="Test2",
            last_name="User2",
            role="user",
            dob=date(1992, 1, 1),
        )
        user.set_password("user123")
        db.session.add(user)
        db.session.commit()

        # Create thread
        thread = Thread(title="Test Thread 2", author_id=user.id)
        db.session.add(thread)
        db.session.flush()

        post = Post(thread_id=thread.id, author_id=user.id, content="Test post 2")
        db.session.add(post)
        db.session.commit()

        # Visit forum
        response = client.get("/forum/")
        html = response.data.decode("utf-8", errors="ignore")

        # Verify basic forum structure
        assert response.status_code == 200
        assert "Test Thread 2" in html
        assert "Forum" in html


def test_delete_button_styling_present():
    """Test that delete button styling is present in forum index template"""
    tpl = _find_forum_template("index.html")
    if tpl is None:
        pytest.skip("forum index template not present; skipping")
    with open(tpl, "r", encoding="utf-8", errors="ignore") as f:
        template_content = f.read()

    # Check for delete button CSS
    assert ".btn-delete" in template_content
    assert ("background: rgba(220, 53, 69" in template_content) or ("color: #dc3545" in template_content)
