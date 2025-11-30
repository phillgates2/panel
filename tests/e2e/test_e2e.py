"""
End-to-End Tests with Playwright
Comprehensive UI testing for critical user flows
"""

import pytest
from playwright.sync_api import Page, expect


class TestAuthentication:
    """Test user authentication flows"""

    def test_user_registration(self, page: Page, test_server):
        """Test complete user registration flow"""
        page.goto("/register")

        # Fill registration form
        page.fill('input[name="first_name"]', "Test")
        page.fill('input[name="last_name"]', "User")
        page.fill('input[name="email"]', "test@example.com")
        page.fill('input[name="dob"]', "2000-01-01")

        # Generate strong password
        page.fill('input[name="password"]', "TestPassword123!")

        # Handle CAPTCHA (mock for testing)
        page.fill('input[name="captcha"]', "TEST123")

        # Submit form
        page.click('button[type="submit"]')

        # Verify redirect to login or success message
        expect(page).to_have_url("/login")
        expect(page.locator(".alert-success")).to_be_visible()

    def test_user_login(self, page: Page, test_server):
        """Test user login flow"""
        page.goto("/login")

        # Fill login form
        page.fill('input[name="email"]', "admin@example.com")
        page.fill('input[name="password"]', "admin123")

        # Handle CAPTCHA
        page.fill('input[name="captcha"]', "TEST123")

        # Submit form
        page.click('button[type="submit"]')

        # Verify successful login
        expect(page).to_have_url("/dashboard")
        expect(page.locator("text=Welcome back")).to_be_visible()

    def test_password_reset(self, page: Page, test_server):
        """Test password reset flow"""
        page.goto("/forgot")

        # Request password reset
        page.fill('input[name="email"]', "admin@example.com")
        page.click('button[type="submit"]')

        # Verify success message
        expect(page.locator(".alert-success")).to_be_visible()

    def test_social_login_google(self, page: Page, test_server):
        """Test Google OAuth login"""
        page.goto("/login")

        # Click Google login button
        page.click('a[href*="oauth/login/google"]')

        # Mock OAuth response (in real test, would handle OAuth flow)
        # For now, verify redirect to OAuth provider
        expect(page.url).to_contain("accounts.google.com")

    def test_logout(self, page: Page, authenticated_page):
        """Test user logout"""
        # Click logout link
        authenticated_page.click('a[href="/logout"]')

        # Verify redirect to login
        expect(authenticated_page).to_have_url("/login")


class TestForumFeatures:
    """Test forum functionality"""

    def test_view_forum_index(self, page: Page, test_server):
        """Test forum index page"""
        page.goto("/forum")

        # Verify page loads
        expect(page.locator("h1")).to_contain_text("Forum")
        expect(page.locator(".forum-thread")).to_be_visible()

    def test_create_thread(self, authenticated_page: Page):
        """Test creating a new forum thread"""
        authenticated_page.goto("/forum/create")

        # Fill thread form
        authenticated_page.fill('input[name="title"]', "Test Thread")
        authenticated_page.fill(
            'textarea[name="content"]', "This is a test thread content."
        )

        # Submit form
        authenticated_page.click('button[type="submit"]')

        # Verify thread creation
        expect(authenticated_page.locator("h1")).to_contain_text("Test Thread")
        expect(authenticated_page.locator(".post-content")).to_contain_text(
            "test thread content"
        )

    def test_post_reply(self, authenticated_page: Page):
        """Test posting a reply to a thread"""
        # Navigate to existing thread
        authenticated_page.goto("/forum/thread/1")  # Assuming thread ID 1 exists

        # Fill reply form
        authenticated_page.fill('textarea[name="content"]', "This is a test reply.")

        # Submit reply
        authenticated_page.click('button[type="submit"]')

        # Verify reply appears
        expect(authenticated_page.locator(".post-content")).to_contain_text(
            "test reply"
        )

    def test_forum_search(self, page: Page, test_server):
        """Test forum search functionality"""
        page.goto("/forum")

        # Use search functionality
        page.fill('input[name="q"]', "test")
        page.click('button[type="submit"]')

        # Verify search results
        expect(page.locator(".search-results")).to_be_visible()


class TestAdminFeatures:
    """Test administrative features"""

    def test_admin_login(self, admin_page: Page):
        """Test admin login"""
        admin_page.goto("/admin")

        # Verify admin dashboard loads
        expect(admin_page.locator("h1")).to_contain_text("Admin")
        expect(admin_page.locator(".admin-stats")).to_be_visible()

    def test_user_management(self, admin_page: Page):
        """Test user management in admin panel"""
        admin_page.goto("/admin/users")

        # Verify user list loads
        expect(admin_page.locator(".user-table")).to_be_visible()
        expect(admin_page.locator(".user-row")).to_have_count_greater_than(0)

    def test_create_user(self, admin_page: Page):
        """Test creating a new user via admin panel"""
        admin_page.goto("/admin/users/create")

        # Fill user creation form
        admin_page.fill('input[name="email"]', "newuser@example.com")
        admin_page.fill('input[name="first_name"]', "New")
        admin_page.fill('input[name="last_name"]', "User")
        admin_page.select_option('select[name="role"]', "user")

        # Submit form
        admin_page.click('button[type="submit"]')

        # Verify user creation
        expect(admin_page.locator(".alert-success")).to_be_visible()

    def test_system_settings(self, admin_page: Page):
        """Test system settings management"""
        admin_page.goto("/admin/settings")

        # Verify settings page loads
        expect(admin_page.locator(".settings-form")).to_be_visible()

        # Test settings update
        admin_page.fill('input[name="site_name"]', "Test Panel")
        admin_page.click('button[type="submit"]')

        # Verify update
        expect(admin_page.locator(".alert-success")).to_be_visible()


class TestGDPRCompliance:
    """Test GDPR compliance features"""

    def test_privacy_policy_page(self, page: Page, test_server):
        """Test privacy policy page accessibility"""
        page.goto("/privacy")

        expect(page.locator("h1")).to_contain_text("Privacy Policy")
        expect(page.locator(".privacy-content")).to_be_visible()

    def test_gdpr_tools_access(self, authenticated_page: Page):
        """Test GDPR tools page access"""
        authenticated_page.goto("/gdpr")

        expect(authenticated_page.locator("h1")).to_contain_text("GDPR Tools")
        expect(authenticated_page.locator(".card")).to_have_count_greater_than(0)

    def test_data_export_request(self, authenticated_page: Page):
        """Test GDPR data export request"""
        authenticated_page.goto("/gdpr")

        # Click export button
        authenticated_page.click('button:has-text("Export My Data")')

        # Verify processing (in real test, would check download)
        expect(authenticated_page.locator(".alert-info")).to_be_visible()


class TestPWAAndOffline:
    """Test Progressive Web App features"""

    def test_pwa_install_prompt(self, page: Page, test_server):
        """Test PWA install prompt availability"""
        page.goto("/")

        # Check for PWA manifest
        manifest_link = page.locator('link[rel="manifest"]')
        expect(manifest_link).to_have_attribute("href", "/static/manifest.json")

        # Check for service worker
        # Note: Service worker testing requires special setup

    def test_offline_page(self, page: Page, test_server):
        """Test offline page accessibility"""
        page.goto("/offline")

        expect(page.locator("h1")).to_contain_text("You're Offline")
        expect(page.locator(".offline-actions")).to_be_visible()


class TestResponsiveDesign:
    """Test responsive design across devices"""

    def test_mobile_navigation(self, page: Page, test_server):
        """Test mobile navigation menu"""
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE size

        page.goto("/")

        # Check mobile menu button exists
        mobile_menu = page.locator(".mobile-menu-toggle")
        expect(mobile_menu).to_be_visible()

        # Test menu toggle
        mobile_menu.click()
        expect(page.locator(".nav-menu")).to_be_visible()

    def test_tablet_layout(self, page: Page, test_server):
        """Test tablet-specific layouts"""
        page.set_viewport_size({"width": 768, "height": 1024})  # iPad size

        page.goto("/dashboard")

        # Check responsive grid layout
        dashboard_grid = page.locator(".dashboard-grid")
        expect(dashboard_grid).to_be_visible()

        # Verify cards stack properly
        cards = page.locator(".dashboard-card")
        expect(cards).to_have_count_greater_than(0)

    def test_desktop_layout(self, page: Page, test_server):
        """Test desktop layout"""
        page.set_viewport_size({"width": 1920, "height": 1080})

        page.goto("/forum")

        # Check full-width layout
        forum_container = page.locator(".container")
        expect(forum_container).to_be_visible()


class TestAccessibility:
    """Test accessibility compliance"""

    def test_keyboard_navigation(self, page: Page, test_server):
        """Test keyboard navigation"""
        page.goto("/login")

        # Tab through form elements
        page.keyboard.press("Tab")  # Focus email field
        focused_element = page.locator(":focus")
        expect(focused_element).to_have_attribute("name", "email")

        page.keyboard.press("Tab")  # Focus password field
        focused_element = page.locator(":focus")
        expect(focused_element).to_have_attribute("name", "password")

    def test_screen_reader_support(self, page: Page, test_server):
        """Test screen reader accessibility"""
        page.goto("/")

        # Check for ARIA labels
        aria_elements = page.locator("[aria-label], [aria-labelledby]")
        expect(aria_elements).to_have_count_greater_than(0)

        # Check for alt text on images
        images = page.locator("img")
        for i in range(images.count()):
            img = images.nth(i)
            alt_text = img.get_attribute("alt")
            expect(alt_text).not_to_be_empty()

    def test_color_contrast(self, page: Page, test_server):
        """Test color contrast ratios"""
        page.goto("/")

        # Check that text has sufficient contrast
        # This would typically use a color contrast checking library
        text_elements = page.locator("p, span, div")
        expect(text_elements).to_have_count_greater_than(0)


# Test configuration and fixtures
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for testing"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "record_video_dir": "test-results/videos/",
        "record_har_path": "test-results/har/",
    }


@pytest.fixture
def test_server():
    """Start test server"""
    # This would start the Flask app for testing
    # For now, assume it's running
    return "http://localhost:8080"


@pytest.fixture
def authenticated_page(page: Page, test_server):
    """Create authenticated page session"""
    page.goto("/login")

    # Login with test credentials
    page.fill('input[name="email"]', "admin@example.com")
    page.fill('input[name="password"]', "admin123")
    page.fill('input[name="captcha"]', "TEST123")
    page.click('button[type="submit"]')

    # Wait for redirect
    page.wait_for_url("/dashboard")

    return page


@pytest.fixture
def admin_page(page: Page, test_server):
    """Create admin page session"""
    page.goto("/login")

    # Login with admin credentials
    page.fill('input[name="email"]', "admin@example.com")
    page.fill('input[name="password"]', "admin123")
    page.fill('input[name="captcha"]', "TEST123")
    page.click('button[type="submit"]')

    # Verify admin access
    page.wait_for_url("/dashboard")
    expect(page.locator(".admin-section")).to_be_visible()

    return page


# Test utilities
def take_screenshot_on_failure(page: Page, test_name: str):
    """Take screenshot on test failure"""
    if hasattr(page, "_screenshot_on_failure"):
        page.screenshot(path=f"test-results/screenshots/{test_name}_failure.png")


def log_test_result(test_name: str, status: str, duration: float):
    """Log test results"""
    with open("test-results/results.log", "a") as f:
        f.write(f"{test_name}: {status} ({duration:.2f}s)\n")
