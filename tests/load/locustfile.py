"""
Load Testing with Locust
Performance testing and stress testing for the Panel application
"""

import json
import os
import time

import gevent
from locust import HttpUser, TaskSet, between, events, task
from locust.contrib.fasthttp import FastHttpUser


class WebsiteUser(FastHttpUser):
    """Basic website user behavior"""

    wait_time = between(1, 5)

    def on_start(self):
        """Setup user session"""
        self.client.headers = {
            "User-Agent": "Panel Load Test/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @task(10)
    def index_page(self):
        """Load homepage"""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Homepage failed: {response.status_code}")

    @task(5)
    def forum_page(self):
        """Load forum page"""
        with self.client.get("/forum", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Forum page failed: {response.status_code}")

    @task(3)
    def login_page(self):
        """Load login page"""
        with self.client.get("/login", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Login page failed: {response.status_code}")

    @task(2)
    def static_assets(self):
        """Load static assets"""
        assets = [
            "/static/css/style.css",
            "/static/js/app.js",
            "/static/manifest.json",
            "/static/icons/icon-192.png",
        ]

        for asset in assets:
            with self.client.get(asset, catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Asset {asset} failed: {response.status_code}")


class AuthenticatedUser(FastHttpUser):
    """Authenticated user behavior"""

    wait_time = between(2, 8)

    def on_start(self):
        """Login user"""
        self.login()

    def login(self):
        """Perform login"""
        login_data = {
            "email": os.getenv("TEST_USER_EMAIL", "test@example.com"),
            "password": os.getenv("TEST_USER_PASSWORD", "test123"),
            "captcha": "TEST123",
        }

        with self.client.post("/login", data=login_data, catch_response=True) as response:
            if response.status_code == 302:  # Redirect after successful login
                response.success()
                # Store session cookies
                self.logged_in = True
            else:
                response.failure(f"Login failed: {response.status_code}")
                self.logged_in = False

    @task(8)
    def dashboard(self):
        """Load dashboard page"""
        if not getattr(self, "logged_in", False):
            self.login()
            return

        with self.client.get("/dashboard", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Dashboard failed: {response.status_code}")

    @task(6)
    def profile_page(self):
        """Load profile page"""
        if not getattr(self, "logged_in", False):
            self.login()
            return

        with self.client.get("/profile", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Profile failed: {response.status_code}")

    @task(4)
    def forum_interaction(self):
        """Interact with forum"""
        if not getattr(self, "logged_in", False):
            self.login()
            return

        # View forum
        with self.client.get("/forum", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Forum view failed: {response.status_code}")
                return

        # View a thread (assuming thread ID 1 exists)
        with self.client.get("/forum/thread/1", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Thread view failed: {response.status_code}")


class APIUser(FastHttpUser):
    """API user for testing API endpoints"""

    wait_time = between(1, 3)

    def on_start(self):
        """Setup API user"""
        self.client.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        # Login and get token if needed
        self.token = self.get_auth_token()

    def get_auth_token(self):
        """Get authentication token"""
        login_data = {
            "email": os.getenv("TEST_USER_EMAIL", "test@example.com"),
            "password": os.getenv("TEST_USER_PASSWORD", "test123"),
            "captcha": "TEST123",
        }

        with self.client.post("/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                # Extract token from response (adjust based on your auth system)
                data = response.json()
                return data.get("token")
            else:
                response.failure(f"API login failed: {response.status_code}")
                return None

    @task(10)
    def api_health(self):
        """Test API health endpoint"""
        with self.client.get("/api/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"API health failed: {response.status_code}")

    @task(8)
    def api_user_profile(self):
        """Test user profile API"""
        if self.token:
            self.client.headers["Authorization"] = f"Bearer {self.token}"

        with self.client.get("/api/user/profile", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"API profile failed: {response.status_code}")

    @task(6)
    def api_forum_data(self):
        """Test forum API endpoints"""
        endpoints = [
            "/api/forum/threads",
            "/api/forum/categories",
        ]

        for endpoint in endpoints:
            with self.client.get(endpoint, catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"API {endpoint} failed: {response.status_code}")

    @task(4)
    def api_gdpr_endpoints(self):
        """Test GDPR API endpoints"""
        if self.token:
            self.client.headers["Authorization"] = f"Bearer {self.token}"

        with self.client.get("/api/gdpr/consent", catch_response=True) as response:
            if response.status_code in [200, 401]:  # 401 is expected without auth
                response.success()
            else:
                response.failure(f"GDPR API failed: {response.status_code}")


class AdminUser(FastHttpUser):
    """Admin user behavior for testing admin functionality"""

    wait_time = between(3, 10)

    def on_start(self):
        """Login as admin"""
        self.admin_login()

    def admin_login(self):
        """Perform admin login"""
        login_data = {
            "email": os.getenv("TEST_ADMIN_EMAIL", "admin@example.com"),
            "password": os.getenv("TEST_ADMIN_PASSWORD", "admin123"),
            "captcha": "TEST123",
        }

        with self.client.post("/login", data=login_data, catch_response=True) as response:
            if response.status_code == 302:
                response.success()
                self.admin_logged_in = True
            else:
                response.failure(f"Admin login failed: {response.status_code}")
                self.admin_logged_in = False

    @task(5)
    def admin_dashboard(self):
        """Load admin dashboard"""
        if not getattr(self, "admin_logged_in", False):
            self.admin_login()
            return

        with self.client.get("/admin", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Admin dashboard failed: {response.status_code}")

    @task(3)
    def admin_users(self):
        """Load admin user management"""
        if not getattr(self, "admin_logged_in", False):
            self.admin_login()
            return

        with self.client.get("/admin/users", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Admin users failed: {response.status_code}")

    @task(2)
    def admin_audit(self):
        """Load admin audit log"""
        if not getattr(self, "admin_logged_in", False):
            self.admin_login()
            return

        with self.client.get("/admin/audit", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Admin audit failed: {response.status_code}")


class StressTestUser(FastHttpUser):
    """High-load stress testing user"""

    wait_time = between(0.1, 0.5)  # Very fast requests

    @task
    def stress_test_endpoint(self):
        """Hit endpoints rapidly for stress testing"""
        endpoints = ["/", "/forum", "/api/health", "/static/css/style.css", "/static/manifest.json"]

        import random

        endpoint = random.choice(endpoints)

        with self.client.get(endpoint, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Stress test {endpoint} failed: {response.status_code}")


# Custom event handlers for monitoring
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when a load test starts"""
    print(f"Load test started: {environment.runner.user_classes}")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when a load test stops"""
    print("Load test finished")

    # Generate summary report
    generate_load_test_report(environment)


@events.request.add_listener
def on_request(
    request_type, name, response_time, response_length, response, context, exception, **kwargs
):
    """Called for each request"""
    if exception:
        print(f"Request failed: {name} - {exception}")


def generate_load_test_report(environment):
    """Generate detailed load test report"""
    import datetime

    report = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "test_duration": environment.runner.stats.total_run_time,
        "total_requests": environment.runner.stats.num_requests,
        "total_failures": environment.runner.stats.num_failures,
        "requests_per_second": environment.runner.stats.total_rps,
        "average_response_time": environment.runner.stats.avg_response_time,
        "median_response_time": environment.runner.stats.median_response_time,
        "95th_percentile": environment.runner.stats.get_percentile(95),
        "99th_percentile": environment.runner.stats.get_percentile(99),
        "user_classes": {},
    }

    # Per-user-class statistics
    for user_class_name, user_class_stats in environment.runner.stats.entries.items():
        report["user_classes"][user_class_name] = {
            "num_requests": user_class_stats.num_requests,
            "num_failures": user_class_stats.num_failures,
            "average_response_time": user_class_stats.avg_response_time,
            "min_response_time": user_class_stats.min_response_time,
            "max_response_time": user_class_stats.max_response_time,
            "requests_per_second": user_class_stats.total_rps,
        }

    # Save report
    with open("test-results/load_test_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Load test report saved to test-results/load_test_report.json")

    # Print summary
    print("\n=== LOAD TEST SUMMARY ===")
    print(f"Duration: {report['test_duration']:.2f}s")
    print(f"Total Requests: {report['total_requests']}")
    print(f"Failures: {report['total_failures']}")
    print(f"Requests/sec: {report['requests_per_second']:.2f}")
    print(f"Average Response Time: {report['average_response_time']:.2f}ms")
    print(f"95th Percentile: {report['95th_percentile']:.2f}ms")
    print(f"99th Percentile: {report['99th_percentile']:.2f}ms")


# Performance monitoring integration
class PerformanceMonitor:
    """Monitor performance during load tests"""

    def __init__(self):
        self.metrics = {
            "response_times": [],
            "error_rates": [],
            "throughput": [],
            "memory_usage": [],
            "cpu_usage": [],
        }

    def record_response_time(self, response_time):
        """Record response time"""
        self.metrics["response_times"].append(response_time)

    def record_error(self):
        """Record error occurrence"""
        self.metrics["error_rates"].append(1)

    def record_success(self):
        """Record successful request"""
        self.metrics["error_rates"].append(0)

    def get_summary(self):
        """Get performance summary"""
        response_times = self.metrics["response_times"]
        error_rates = self.metrics["error_rates"]

        if not response_times:
            return {}

        return {
            "avg_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "error_rate": sum(error_rates) / len(error_rates) if error_rates else 0,
            "total_requests": len(response_times),
        }


# Global performance monitor
performance_monitor = PerformanceMonitor()


@events.request.add_listener
def record_performance(
    request_type, name, response_time, response_length, response, context, exception, **kwargs
):
    """Record performance metrics"""
    performance_monitor.record_response_time(response_time)

    if exception or response.status_code >= 400:
        performance_monitor.record_error()
    else:
        performance_monitor.record_success()


@events.test_stop.add_listener
def print_performance_summary(environment, **kwargs):
    """Print performance summary"""
    summary = performance_monitor.get_summary()
    if summary:
        print("\n=== PERFORMANCE SUMMARY ===")
        print(f"Average Response Time: {summary['avg_response_time']:.2f}ms")
        print(f"Min Response Time: {summary['min_response_time']:.2f}ms")
        print(f"Max Response Time: {summary['max_response_time']:.2f}ms")
        print(f"Error Rate: {summary['error_rate']:.2%}")
        print(f"Total Requests: {summary['total_requests']}")


# Load test configuration
# Run with: locust -f tests/load/locustfile.py --host=http://localhost:8080
# Web UI: http://localhost:8089
# API: http://localhost:8089/stats/requests
