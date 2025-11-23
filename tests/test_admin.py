import pytest
from flask import url_for

from src.panel import models


def test_admin_dashboard_requires_login(client):
    """Test that admin dashboard requires login."""
    response = client.get("/admin/teams")
    assert response.status_code == 302  # Redirect to login


def test_admin_dashboard_access_denied_for_regular_user(client, regular_user):
    """Test that regular users cannot access admin dashboard."""
    with client:
        client.post("/login", data={"email": regular_user.email, "password": "password"})
        response = client.get("/admin/teams")
        assert response.status_code == 302  # Redirect to dashboard with error


def test_admin_dashboard_access_granted_for_system_admin(client, system_admin):
    """Test that system admins can access admin dashboard."""
    with client:
        client.post("/login", data={"email": system_admin.email, "password": "password"})
        response = client.get("/admin/teams")
        assert response.status_code == 200
        assert b"Team Management" in response.data


def test_create_team(client, system_admin):
    """Test creating a new team."""
    with client:
        client.post("/login", data={"email": system_admin.email, "password": "password"})
        response = client.post("/admin/teams/create", data={"name": "Test Team", "description": "A test team"})
        assert response.status_code == 302  # Redirect back
        # Check if team was created
        from src.panel.models_extended import UserGroup
        team = UserGroup.query.filter_by(name="Test Team").first()
        assert team is not None
        assert team.description == "A test team"


def test_add_team_member(client, system_admin, regular_user):
    """Test adding a member to a team."""
    with client:
        client.post("/login", data={"email": system_admin.email, "password": "password"})
        # First create a team
        client.post("/admin/teams/create", data={"name": "Test Team", "description": "A test team"})
        team = models.UserGroup.query.filter_by(name="Test Team").first()
        # Add member
        response = client.post(f"/admin/teams/{team.id}/add_member", data={"email": regular_user.email})
        assert response.status_code == 302
        # Check membership
        from src.panel.models_extended import UserGroupMembership
        membership = UserGroupMembership.query.filter_by(user_id=regular_user.id, group_id=team.id).first()
        assert membership is not None