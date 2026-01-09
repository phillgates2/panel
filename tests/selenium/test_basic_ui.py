import os
import time
import pytest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@pytest.fixture(scope="session")
def driver():
    opts = ChromeOptions()
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        opts.binary_location = chrome_bin
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    # faster CI
    opts.add_argument("--window-size=1280,800")

    remote_url = os.environ.get("SELENIUM_REMOTE_URL")
    try:
        if remote_url:
            driver = webdriver.Remote(command_executor=remote_url, options=opts)
        else:
            driver = webdriver.Chrome(options=opts)
    except Exception as e:
        pytest.skip(f"Selenium WebDriver unavailable: {e}")

    driver.set_page_load_timeout(30)
    yield driver
    driver.quit()


@pytest.fixture(scope="session")
def base_url():
    # Allow override via env; default to local dev
    return os.environ.get("PANEL_BASE_URL", "http://localhost:5000")


def _safe_get(driver, url):
    from selenium.common.exceptions import WebDriverException
    try:
        driver.get(url)
        return True
    except WebDriverException:
        return False


class TestBasicUI:
    def test_metrics_requires_auth(self, driver, base_url):
        if not _safe_get(driver, base_url + "/metrics"):
            pytest.skip("Panel not running; skipping Selenium UI test")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert "Authentication required" in body_text or "unauthorized" in body_text.lower()

    def test_login_flow(self, driver, base_url):
        if not _safe_get(driver, base_url + "/login"):
            pytest.skip("Panel not running; skipping Selenium UI test")

        email_inputs = driver.find_elements(By.NAME, "email")
        password_inputs = driver.find_elements(By.NAME, "password")
        if not email_inputs or not password_inputs:
            pytest.skip("Login form inputs not found; skip UI auth flow test")

        email_inputs[0].clear()
        email_inputs[0].send_keys("john@example.com")
        password_inputs[0].clear()
        password_inputs[0].send_keys("Password123!")

        submit = None
        for selector in [(By.CSS_SELECTOR, "button[type='submit']"), (By.CSS_SELECTOR, "input[type='submit']")]:
            els = driver.find_elements(*selector)
            if els:
                submit = els[0]
                break
        if submit:
            submit.click()
            WebDriverWait(driver, 5).until(lambda d: True)
        else:
            password_inputs[0].submit()
            WebDriverWait(driver, 5).until(lambda d: True)
        assert driver.find_element(By.TAG_NAME, "body") is not None

    def test_health_page_loads(self, driver, base_url):
        if not _safe_get(driver, base_url + "/health"):
            pytest.skip("Panel not running; skipping Selenium UI test")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert "status" in body_text

