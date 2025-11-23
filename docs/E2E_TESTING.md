# End-to-End Testing with Playwright

This guide explains the comprehensive E2E testing setup using Playwright for the Panel application.

## Overview

The E2E testing suite covers:
- **User Authentication**: Login, registration, password reset, OAuth
- **Forum Features**: Thread creation, posting replies, search
- **Admin Functions**: User management, system settings, audit logs
- **GDPR Compliance**: Data export, privacy tools
- **PWA Features**: Offline functionality, install prompts
- **Responsive Design**: Mobile, tablet, and desktop layouts
- **Accessibility**: WCAG compliance and screen reader support

## Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install -r requirements/requirements-dev.txt
   ```

2. **Playwright Browsers**:
   ```bash
   playwright install
   ```

3. **Test Database**: PostgreSQL instance for testing

4. **Environment Variables**:
   ```bash
   export TEST_BASE_URL="http://localhost:8080"
   export TEST_USERNAME="admin@example.com"
   export TEST_PASSWORD="admin123"
   export TEST_ADMIN_USERNAME="admin@example.com"
   export TEST_ADMIN_PASSWORD="admin123"
   ```

## Running Tests

### Basic Test Execution

```bash
# Run all E2E tests
make test-e2e

# Run with browser visible
make test-e2e-headed

# Debug specific test
make test-e2e-debug
```

### Test Categories

```bash
# Run specific test file
pytest tests/e2e/test_authentication.py -v

# Run specific test class
pytest tests/e2e/test_authentication.py::TestAuthentication -v

# Run specific test method
pytest tests/e2e/test_authentication.py::TestAuthentication::test_user_login -v
```

### Parallel Execution

```bash
# Run tests in parallel (requires multiple browser instances)
pytest tests/e2e/ -n 4 --tb=short
```

## Test Configuration

### Playwright Configuration (`playwright.config.toml`)

```toml
[tool.playwright]
browser = "chromium"
headed = false
slow_mo = 0

[tool.playwright.project.chromium]
browser_name = "chromium"
viewport_size = { width: 1280, height: 720 }

[tool.playwright.project.firefox]
browser_name = "firefox"
viewport_size = { width: 1280, height: 720 }

[tool.playwright.project.webkit]
browser_name = "webkit"
viewport_size = { width: 1280, height: 720 }
```

### Test Fixtures (`tests/e2e/conftest.py`)

- **`test_server`**: Provides base URL for testing
- **`authenticated_page`**: Pre-authenticated browser session
- **`admin_page`**: Admin-authenticated browser session
- **Performance helpers**: Response time measurement
- **Accessibility helpers**: WCAG compliance checking

## Test Structure

### Authentication Tests

```python
class TestAuthentication:
    def test_user_registration(self, page: Page):
        # Test complete registration flow

    def test_user_login(self, page: Page):
        # Test login with valid credentials

    def test_social_login_google(self, page: Page):
        # Test OAuth login flow
```

### Forum Tests

```python
class TestForumFeatures:
    def test_create_thread(self, authenticated_page: Page):
        # Test thread creation

    def test_post_reply(self, authenticated_page: Page):
        # Test posting replies

    def test_forum_search(self, page: Page):
        # Test search functionality
```

### Admin Tests

```python
class TestAdminFeatures:
    def test_admin_login(self, admin_page: Page):
        # Test admin authentication

    def test_user_management(self, admin_page: Page):
        # Test user CRUD operations

    def test_system_settings(self, admin_page: Page):
        # Test configuration changes
```

## Advanced Testing Features

### Visual Regression Testing

```python
def test_visual_regression(page: Page):
    page.goto("/dashboard")
    take_screenshot_for_comparison(page, "dashboard")
    # Compare with baseline image
```

### Accessibility Testing

```python
def test_accessibility(page: Page):
    page.goto("/")
    violations = check_accessibility(page)
    assert len(violations) == 0, f"Accessibility issues: {violations}"
```

### Performance Testing

```python
def test_page_load_performance(page: Page):
    start_time = time.time()
    page.goto("/dashboard")
    load_time = time.time() - start_time
    assert load_time < 2.0, f"Page load too slow: {load_time}s"
```

### Cross-Browser Testing

```python
@pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
def test_cross_browser(page: Page, browser_name):
    # Test runs on all browsers
    page.goto("/")
    expect(page.locator("h1")).to_be_visible()
```

## Test Data Management

### Test Data Generation

```python
def generate_test_user():
    return {
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "TestPassword123!"
    }
```

### Database Seeding

```python
@pytest.fixture(scope="session", autouse=True)
def seed_test_data():
    # Create test users, forums, etc.
    # Clean up after tests
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          pip install -r requirements/requirements-dev.txt
          playwright install

      - name: Run E2E tests
        run: make test-e2e
        env:
          TEST_BASE_URL: http://localhost:8080

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: test-results/
```

## Debugging Tests

### Visual Debugging

```bash
# Run tests with browser visible
PWDEBUG=1 pytest tests/e2e/test_authentication.py::TestAuthentication::test_user_login

# Generate code for test creation
make test-playwright-codegen
```

### Screenshot on Failure

```python
@pytest.fixture(autouse=True)
def screenshot_on_failure(page, request):
    yield
    if request.node.rep_call.failed:
        page.screenshot(path=f"test-results/failures/{request.node.name}.png")
```

### Network Monitoring

```python
def test_network_requests(page: Page):
    requests = []
    page.on("request", lambda req: requests.append(req.url))

    page.goto("/dashboard")

    # Analyze network requests
    assert len([r for r in requests if "api" in r]) > 0
```

## Performance Optimization

### Test Parallelization

```bash
# Run tests across multiple processes
pytest tests/e2e/ -n auto --tb=short

# Distribute across multiple machines
pytest tests/e2e/ --maxfail=3 --tb=short -x
```

### Selective Test Execution

```bash
# Run only critical tests
pytest -m "critical" tests/e2e/

# Skip slow tests
pytest -m "not slow" tests/e2e/
```

### Test Result Analysis

```bash
# Generate detailed report
pytest tests/e2e/ --html=report.html --self-contained-html

# JUnit XML for CI
pytest tests/e2e/ --junitxml=results.xml
```

## Best Practices

### Test Organization
- **Page Objects**: Encapsulate page interactions
- **Data Builders**: Create test data fluently
- **Custom Assertions**: Domain-specific assertions

### Reliability
- **Wait Strategies**: Explicit waits over sleep
- **Retry Logic**: Handle flaky tests
- **Cleanup**: Proper test isolation

### Maintenance
- **DRY Principle**: Avoid code duplication
- **Descriptive Names**: Clear test naming
- **Documentation**: Inline test documentation

## Troubleshooting

### Common Issues

1. **Flaky Tests**:
   - Add explicit waits
   - Use stable selectors
   - Handle async operations

2. **Timeout Errors**:
   - Increase timeout values
   - Check network conditions
   - Debug with `--headed` mode

3. **Selector Issues**:
   - Use data attributes for selectors
   - Avoid brittle CSS selectors
   - Test selector stability

### Debug Tools

```bash
# Playwright Inspector
playwright install-deps
npx playwright install
npx playwright test --headed --debug

# Browser DevTools
page.pause()  # Pause execution for debugging
```

## Integration with Other Tools

### TestRail Integration

```python
def report_to_testrail(results):
    # Send test results to TestRail
    pass
```

### Slack Notifications

```python
def notify_slack(results):
    # Send test results to Slack
    pass
```

### Allure Reports

```bash
# Generate Allure reports
pytest tests/e2e/ --alluredir=allure-results
allure serve allure-results
```

This comprehensive E2E testing setup ensures the Panel application works correctly across all user journeys and maintains quality through automated testing.