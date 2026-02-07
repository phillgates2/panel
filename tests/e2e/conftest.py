"""Playwright end-to-end test configuration and fixtures.

These tests are treated as optional and are deselected by default unless
RUN_E2E=1 is set (see tests/conftest.py).

Important: this file must not call pytest.skip() at import time, otherwise
default unit test runs will report skipped tests even when E2E is not selected.
"""

from __future__ import annotations

import json
import os

import pytest

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").lower() in ("1", "true", "yes")


def _load_env() -> None:
    if callable(load_dotenv):
        try:
            load_dotenv()
        except Exception:
            pass


def _require_e2e_ready() -> None:
    """Skip at runtime when E2E prerequisites are not met."""

    if _truthy_env("SKIP_E2E"):
        pytest.skip("End-to-end tests skipped by SKIP_E2E")

    # Playwright must be installed for these fixtures.
    pytest.importorskip("playwright.sync_api")

    test_base_url = os.getenv("TEST_BASE_URL", "http://localhost:8080")
    try:
        import requests

        r = requests.get(test_base_url, timeout=1)
        if r.status_code >= 400:
            pytest.skip(
                f"E2E server reachable but returned {r.status_code}; skipping end-to-end tests"
            )
    except Exception:
        pytest.skip(f"E2E server not reachable at {test_base_url}; skipping end-to-end tests")


_load_env()

# Test configuration
TEST_BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080")
TEST_USERNAME = os.getenv("TEST_USERNAME", "admin@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "admin123")
TEST_ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "admin@example.com")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

# Ensure test-results directories exist and use file paths for HAR to avoid OSError on Windows
_results_dir = os.path.join("test-results")
_videos_dir = os.path.join(_results_dir, "videos")
_har_dir = os.path.join(_results_dir, "har")
_screenshots_dir = os.path.join(_results_dir, "screenshots")

if os.getenv("RECORD_VIDEO"):
    os.makedirs(_videos_dir, exist_ok=True)
if os.getenv("RECORD_HAR"):
    os.makedirs(_har_dir, exist_ok=True)
os.makedirs(_screenshots_dir, exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _e2e_prereqs_guard():
    """Run prerequisite checks only when E2E tests are actually executing."""

    _require_e2e_ready()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for all tests"""
    # Playwright expects a file path for HAR output. Use a consistent per-session file.
    har_path = None
    if os.getenv("RECORD_HAR"):
        har_path = os.path.join(_har_dir, "session.har")

    return {
        **browser_context_args,
        "base_url": TEST_BASE_URL,
        "viewport": {"width": 1280, "height": 720},
        "record_video_dir": _videos_dir if os.getenv("RECORD_VIDEO") else None,
        "record_har_path": har_path,
        "permissions": ["notifications"] if os.getenv("ENABLE_NOTIFICATIONS") else [],
    }


@pytest.fixture(scope="session")
def browser_args(browser_args):
    """Configure browser launch arguments"""
    return {
        **browser_args,
        "headless": not os.getenv("HEADLESS", "true").lower() == "false",
        "slow_mo": int(os.getenv("SLOW_MO", "0")),
        "args": [
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    }


@pytest.fixture
def test_server():
    """Provide test server URL"""
    return TEST_BASE_URL


@pytest.fixture
def authenticated_page(page):
    """Create authenticated page session"""
    page.goto("/login")

    # Handle potential CAPTCHA
    try:
        captcha_input = page.locator('input[name="captcha"]')
        if captcha_input.is_visible():
            captcha_input.fill("TEST123")
    except:
        pass  # CAPTCHA might not be present

    # Login
    page.fill('input[name="email"]', TEST_USERNAME)
    page.fill('input[name="password"]', TEST_PASSWORD)
    page.click('button[type="submit"]')

    # Wait for successful login
    page.wait_for_url("/dashboard", timeout=10000)

    return page


@pytest.fixture
def admin_page(page):
    """Create admin authenticated page session"""
    page.goto("/login")

    # Handle CAPTCHA
    try:
        captcha_input = page.locator('input[name="captcha"]')
        if captcha_input.is_visible():
            captcha_input.fill("TEST123")
    except:
        pass

    # Login with admin credentials
    page.fill('input[name="email"]', TEST_ADMIN_USERNAME)
    page.fill('input[name="password"]', TEST_ADMIN_PASSWORD)
    page.click('button[type="submit"]')

    # Wait for successful login and verify admin access
    page.wait_for_url("/dashboard", timeout=10000)

    # Verify admin panel access
    admin_section = page.locator(".admin-section")
    assert admin_section.is_visible(), "Admin access not available"

    return page


@pytest.fixture(autouse=True)
def setup_test_environment(page):
    """Setup test environment for each test"""
    # Set longer timeout for slower environments
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(30000)

    # Clear any existing state
    page.context.clear_cookies()
    page.context.clear_permissions()

    yield

    # Cleanup after test
    try:
        # Take screenshot on failure
        if hasattr(page, "_test_failed") and page._test_failed:
            test_name = getattr(page, "_test_name", "unknown_test")
            page.screenshot(path=f"test-results/screenshots/{test_name}_failure.png")
    except Exception as e:
        print(f"Screenshot capture failed: {e}")


@pytest.fixture(autouse=True)
def log_test_info(request, page):
    """Log test information"""
    test_name = request.node.name
    page._test_name = test_name

    print(f"\n?? Starting test: {test_name}")

    def log_failure():
        page._test_failed = True
        print(f"? Test failed: {test_name}")

    request.node.addfinalizer(log_failure)


@pytest.fixture
def mock_api_responses(page):
    """Mock API responses for testing"""

    def mock_response(url_pattern, response_data, status=200):
        """Mock API endpoint responses"""
        page.route(
            url_pattern,
            lambda route: route.fulfill(
                status=status,
                content_type="application/json",
                body=json.dumps(response_data),
            ),
        )

    return mock_response


@pytest.fixture
def disable_animations(page):
    """Disable CSS animations for faster testing"""
    page.add_style_tag(
        content="""
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
        }
    """
    )


@pytest.fixture
def mock_geolocation(page):
    """Mock geolocation for testing"""
    page.context.set_geolocation({"latitude": 37.7749, "longitude": -122.4194})


@pytest.fixture
def mock_notifications(page):
    """Mock notification permissions"""
    page.context.grant_permissions(["notifications"])


# Test data helpers
def generate_test_user():
    """Generate test user data"""
    import random
    import string
    import uuid

    user_id = str(uuid.uuid4())[:8]
    return {
        "email": f"test_{user_id}@example.com",
        "first_name": "Test",
        "last_name": f"User{user_id}",
        "password": "TestPassword123!",
        "dob": "2000-01-01",
    }


def generate_test_thread():
    """Generate test forum thread data"""
    import uuid

    thread_id = str(uuid.uuid4())[:8]
    return {
        "title": f"Test Thread {thread_id}",
        "content": f"This is test content for thread {thread_id}. It contains some sample text to make it more realistic.",
    }


def generate_test_post(thread_id=None):
    """Generate test forum post data"""
    import uuid

    post_id = str(uuid.uuid4())[:8]
    return {
        "thread_id": thread_id,
        "content": f"This is a test reply {post_id}. Testing forum functionality with realistic content.",
    }


# Performance testing helpers
def measure_page_load_time(page, url):
    """Measure page load time"""
    import time

    start_time = time.time()
    page.goto(url)
    page.wait_for_load_state("networkidle")
    load_time = time.time() - start_time

    return load_time


def measure_action_time(page, action_func):
    """Measure time taken for an action"""
    import time

    start_time = time.time()
    result = action_func()
    action_time = time.time() - start_time

    return result, action_time


# Accessibility testing helpers
def check_accessibility(page):
    """Run basic accessibility checks"""
    violations = []

    # Check for missing alt text
    images = page.query_selector_all("img:not([alt])")
    if images:
        violations.append(f"Found {len(images)} images without alt text")

    # Check for missing labels
    inputs = page.query_selector_all("input:not([aria-label]):not([aria-labelledby])")
    if inputs:
        violations.append(f"Found {len(inputs)} inputs without labels")

    # Check color contrast (basic check)
    text_elements = page.query_selector_all("*")
    low_contrast = []
    for element in text_elements:
        try:
            color = page.evaluate(
                """
                (el) => {
                    const style = window.getComputedStyle(el);
                    return {
                        color: style.color,
                        backgroundColor: style.backgroundColor
                    };
                }
            """,
                element,
            )

            # Basic contrast check (would need more sophisticated analysis)
            if color["color"] == color["backgroundColor"]:
                low_contrast.append(element)
        except:
            pass

    if low_contrast:
        violations.append(
            f"Found {len(low_contrast)} elements with potential contrast issues"
        )

    return violations


# Visual regression helpers
def take_screenshot_for_comparison(page, name):
    """Take screenshot for visual regression testing"""
    screenshot_path = f"test-results/screenshots/{name}.png"
    page.screenshot(path=screenshot_path, full_page=True)
    return screenshot_path


def compare_screenshots(baseline_path, current_path):
    """Compare screenshots for visual differences"""
    # This would integrate with a visual diff tool like pixelmatch
    # For now, just check if files exist
    import os

    return os.path.exists(baseline_path) and os.path.exists(current_path)
