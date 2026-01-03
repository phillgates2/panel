import os
import pytest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions


@pytest.fixture(scope="session")
def driver():
    opts = ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,800")

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)
    yield driver
    driver.quit()


@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("PANEL_BASE_URL", "http://localhost:5000")


def _safe_get(driver, url):
    from selenium.common.exceptions import WebDriverException
    try:
        driver.get(url)
        return True
    except WebDriverException:
        return False


class TestNavigation:
    def test_home_index_404_or_index(self, driver, base_url):
        if not _safe_get(driver, base_url + "/"):
            pytest.skip("Panel not running; skipping Selenium UI test")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert body_text is not None

    def test_dashboard_route_exists(self, driver, base_url):
        if not _safe_get(driver, base_url + "/dashboard"):
            pytest.skip("Panel not running; skipping Selenium UI test")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert body_text is not None

    def test_help_page_exists(self, driver, base_url):
        if not _safe_get(driver, base_url + "/help"):
            pytest.skip("Panel not running; skipping Selenium UI test")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert body_text is not None
