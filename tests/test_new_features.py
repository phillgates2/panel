"""
Tests for user profile functionality including avatar upload and team management.
"""

import pytest
import os
import tempfile
from io import BytesIO
from PIL import Image
from datetime import date

from app import app, db, User
from models_extended import UserGroup, UserGroupMembership


@pytest.fixture()
def client(request):
    import tempfile

    fd, path = tempfile.mkstemp(prefix="panel_test_", suffix=".db")
    os.close(fd)
    try:
        from app import create_app

        local_app = create_app()
        local_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{path}"
        local_app.config["TESTING"] = True
        request.module.app = local_app
        try:
            with local_app.app_context():
                db.create_all()
                yield local_app.test_client()
        finally:
            with local_app.app_context():
                db.session.remove()
                db.drop_all()
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


class TestTeamManagement:
    """Test team management functionality."""

    def test_teams_dashboard_access(self, client):
        """Test teams dashboard access for admins."""
        with app.app_context():
            # Create admin user
            u = User(
                first_name="Admin",
                last_name="User",
                email="admin@example.com",
                dob=date(2000, 1, 1),
            )
            u.set_password("Password1!")
            u.role = "system_admin"
            db.session.add(u)
            db.session.commit()

            # Login
            response = client.post('/login', data={
                'email': 'admin@example.com',
                'password': 'Password1!'
            }, follow_redirects=True)
            assert response.status_code == 200

            response = client.get('/admin/teams')
            assert response.status_code == 200
            assert b'Team Management' in response.data

    def test_create_team(self, client):
        """Test creating a new team."""
        with app.app_context():
            # Create admin user
            u = User(
                first_name="Admin",
                last_name="User",
                email="admin@example.com",
                dob=date(2000, 1, 1),
            )
            u.set_password("Password1!")
            u.role = "system_admin"
            db.session.add(u)
            db.session.commit()

            # Login
            response = client.post('/login', data={
                'email': 'admin@example.com',
                'password': 'Password1!'
            }, follow_redirects=True)
            assert response.status_code == 200

            response = client.post('/admin/teams/create', data={
                'name': 'Test Team',
                'description': 'A test team'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'Team &#39;Test Team&#39; created successfully' in response.data

            # Check team was created
            team = UserGroup.query.filter_by(name='Test Team').first()
            assert team is not None
            assert team.description == 'A test team'

    def test_add_team_member(self, client):
        """Test adding a member to a team."""
        with app.app_context():
            # Create admin user
            admin = User(
                first_name="Admin",
                last_name="User",
                email="admin@example.com",
                dob=date(2000, 1, 1),
            )
            admin.set_password("Password1!")
            admin.role = "system_admin"
            db.session.add(admin)

            # Create regular user
            member = User(
                first_name="Member",
                last_name="User",
                email="member@example.com",
                dob=date(2000, 1, 1),
            )
            member.set_password("Password1!")
            db.session.add(member)

            # Create team
            team = UserGroup(name="Member Test Team", description="Test")
            db.session.add(team)
            db.session.commit()

            # Login as admin
            response = client.post('/login', data={
                'email': 'admin@example.com',
                'password': 'Password1!'
            }, follow_redirects=True)
            assert response.status_code == 200

            response = client.post(f'/admin/teams/{team.id}/add_member', data={
                'email': 'member@example.com'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'Added Member User to team' in response.data

            # Check membership was created
            membership = UserGroupMembership.query.filter_by(
                user_id=member.id, group_id=team.id
            ).first()
            assert membership is not None


class TestSecurityFeatures:
    """Test security management features."""

    def test_security_dashboard_access(self, client):
        """Test security dashboard access for admins."""
        with app.app_context():
            # Create admin user
            u = User(
                first_name="Admin",
                last_name="User",
                email="admin@example.com",
                dob=date(2000, 1, 1),
            )
            u.set_password("Password1!")
            u.role = "system_admin"
            db.session.add(u)
            db.session.commit()

            # Login
            response = client.post('/login', data={
                'email': 'admin@example.com',
                'password': 'Password1!'
            }, follow_redirects=True)
            assert response.status_code == 200

            response = client.get('/admin/security')
            assert response.status_code == 200
            assert b'Security Management' in response.data

    def test_add_ip_whitelist(self, client):
        """Test adding IP to whitelist."""
        with app.app_context():
            # Create admin user
            u = User(
                first_name="Admin",
                last_name="User",
                email="admin@example.com",
                dob=date(2000, 1, 1),
            )
            u.set_password("Password1!")
            u.role = "system_admin"
            db.session.add(u)
            db.session.commit()

            # Login
            response = client.post('/login', data={
                'email': 'admin@example.com',
                'password': 'Password1!'
            }, follow_redirects=True)
            assert response.status_code == 200

            response = client.post('/admin/security/whitelist/add', data={
                'ip_address': '192.168.1.100',
                'description': 'Test IP'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'IP 192.168.1.100 added to whitelist' in response.data

    def test_add_ip_blacklist(self, client):
        """Test adding IP to blacklist."""
        with app.app_context():
            # Create admin user
            u = User(
                first_name="Admin",
                last_name="User",
                email="admin@example.com",
                dob=date(2000, 1, 1),
            )
            u.set_password("Password1!")
            u.role = "system_admin"
            db.session.add(u)
            db.session.commit()

            # Login
            response = client.post('/login', data={
                'email': 'admin@example.com',
                'password': 'Password1!'
            }, follow_redirects=True)
            assert response.status_code == 200

            response = client.post('/admin/security/blacklist/add', data={
                'ip_address': '10.0.0.1',
                'reason': 'Suspicious activity'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'IP 10.0.0.1 added to blacklist' in response.data

    def test_invalid_ip_address(self, client):
        """Test validation of invalid IP addresses."""
        with app.app_context():
            # Create admin user
            u = User(
                first_name="Admin",
                last_name="User",
                email="admin@example.com",
                dob=date(2000, 1, 1),
            )
            u.set_password("Password1!")
            u.role = "system_admin"
            db.session.add(u)
            db.session.commit()

            # Login
            response = client.post('/login', data={
                'email': 'admin@example.com',
                'password': 'Password1!'
            }, follow_redirects=True)
            assert response.status_code == 200

            response = client.post('/admin/security/whitelist/add', data={
                'ip_address': 'invalid-ip',
                'description': 'Test'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert b'Invalid IP address format' in response.data


class TestAPIDocumentation:
    """Test API documentation access."""

    def test_api_docs_access(self, client):
        """Test API documentation is accessible."""
        with app.app_context():
            # Create test user
            u = User(
                first_name="Test",
                last_name="User",
                email="test@example.com",
                dob=date(2000, 1, 1),
            )
            u.set_password("Password1!")
            db.session.add(u)
            db.session.commit()

            # Login
            response = client.post('/login', data={
                'email': 'test@example.com',
                'password': 'Password1!'
            }, follow_redirects=True)
            assert response.status_code == 200

            response = client.get('/api/docs')
            assert response.status_code == 200
            assert b'API Documentation' in response.data
            assert b'Base URL' in response.data


class TestMobileResponsiveness:
    """Test mobile responsiveness features."""

    def test_mobile_viewport_meta(self, client):
        """Test that mobile viewport meta tag is present."""
        response = client.get('/')
        assert b'width=device-width, initial-scale=1.0' in response.data

    def test_responsive_css_loaded(self, client):
        """Test that responsive CSS is loaded."""
        response = client.get('/static/css/style.css')
        assert b'@media (max-width: 768px)' in response.data


class TestAccessibility:
    """Test accessibility features."""

    def test_skip_link_present(self, client):
        """Test that skip link is present for accessibility."""
        response = client.get('/')
        assert b'Skip to main content' in response.data

    def test_main_content_id(self, client):
        """Test that main content has proper ID."""
        with app.app_context():
            # Create test user
            u = User(
                first_name="Test",
                last_name="User",
                email="test@example.com",
                dob=date(2000, 1, 1),
            )
            u.set_password("Password1!")
            db.session.add(u)
            db.session.commit()

            # Login
            response = client.post('/login', data={
                'email': 'test@example.com',
                'password': 'Password1!'
            }, follow_redirects=True)
            assert response.status_code == 200

            response = client.get('/dashboard')
            assert b'id="main-content"' in response.data

    def test_focus_styles(self, client):
        """Test that focus styles are defined in CSS."""
        response = client.get('/static/css/style.css')
        assert b'outline: 2px solid var(--accent)' in response.data