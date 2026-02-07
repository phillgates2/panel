from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

pytestmark = pytest.mark.e2e

if TYPE_CHECKING:  # pragma: no cover
    from playwright.sync_api import Page  # type: ignore


class TestAuthentication:
    def test_user_registration(self, page: Page):
        # Test complete registration flow
        page.goto("/register")
        page.fill("#email", "test@example.com")
        page.fill("#password", "TestPassword123!")
        page.fill("#confirm_password", "TestPassword123!")
        page.click("#register-button")
        # Add assertions
        assert page.url.endswith("/dashboard")

    def test_user_login(self, page: Page):
        # Test login with valid credentials
        page.goto("/login")
        page.fill("#email", "test@example.com")
        page.fill("#password", "TestPassword123!")
        page.click("#login-button")
        assert "dashboard" in page.url

    def test_social_login_google(self, page: Page):
        # Test OAuth login flow
        page.goto("/login")
        page.click("#google-login")
        # Mock OAuth flow
        assert page.url.endswith("/dashboard")
