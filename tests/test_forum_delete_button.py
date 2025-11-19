"""Test forum delete thread button functionality"""
import pytest
from datetime import date
from forum import Thread, Post


def test_forum_index_template_has_delete_code():
    """Test that forum index template file includes delete button code"""
    with open('/home/runner/work/panel/panel/templates/forum/index.html', 'r') as f:
        template_content = f.read()
    
    # Verify delete button code is in template
    assert 'delete_thread' in template_content
    assert 'Delete Thread' in template_content
    assert '🗑️' in template_content
    assert 'btn-delete' in template_content
    assert "confirm('Are you sure you want to delete this thread?" in template_content


def test_forum_index_renders_correctly(client, app):
    """Test forum index page renders correctly with threads"""
    with app.app_context():
        from app import db, User
        
        # Create test user
        user = User(
            email="user2@test.com",
            first_name="Test2",
            last_name="User2",
            role="user",
            dob=date(1992, 1, 1)
        )
        user.set_password("user123")
        db.session.add(user)
        db.session.commit()
        
        # Create thread
        thread = Thread(
            title="Test Thread 2",
            author_id=user.id
        )
        db.session.add(thread)
        db.session.flush()
        
        post = Post(
            thread_id=thread.id,
            author_id=user.id,
            content="Test post 2"
        )
        db.session.add(post)
        db.session.commit()
        
        # Visit forum
        response = client.get('/forum/')
        html = response.data.decode('utf-8')
        
        # Verify basic forum structure
        assert response.status_code == 200
        assert 'Test Thread 2' in html
        assert 'Forum' in html


def test_delete_button_styling_present():
    """Test that delete button styling is present in forum index template"""
    with open('/home/runner/work/panel/panel/templates/forum/index.html', 'r') as f:
        template_content = f.read()
    
    # Check for delete button CSS
    assert '.btn-delete' in template_content
    assert 'background: rgba(220, 53, 69' in template_content
    assert 'color: #dc3545' in template_content
