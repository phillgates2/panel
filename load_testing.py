"""
Load Testing Setup for Panel Application

This module provides comprehensive load testing capabilities using Locust
to simulate real-world usage patterns and stress test the application.
"""

import json
import random
import time
from datetime import datetime

from locust import HttpUser, SequentialTaskSet, between, task


class PanelUserBehavior(SequentialTaskSet):
    """Simulates realistic user behavior patterns"""

    def on_start(self):
        """Login and setup user session"""
        self.login()

    def login(self):
        """Authenticate user"""
        # Try different login methods
        login_methods = [
            self.jwt_login,
            self.oauth_login_google,
            self.oauth_login_github,
            self.api_key_login,
        ]

        # Randomly select login method
        login_method = random.choice(login_methods)
        login_method()

    def jwt_login(self):
        """JWT token-based login"""
        response = self.client.post(
            "/auth/jwt/login",
            json={
                "email": f"user{random.randint(1, 1000)}@example.com",
                "password": "password123",
            },
        )

        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    def oauth_login_google(self):
        """Simulate OAuth Google login flow"""
        # This would normally redirect to Google, but for testing we simulate
        response = self.client.get("/auth/login/google")
        if response.status_code in [302, 200]:
            self.authenticated = True

    def oauth_login_github(self):
        """Simulate OAuth GitHub login flow"""
        response = self.client.get("/auth/login/github")
        if response.status_code in [302, 200]:
            self.authenticated = True

    def api_key_login(self):
        """API key authentication"""
        api_key = f"pk_test_{random.randint(100000, 999999)}"
        self.client.headers.update({"X-API-Key": api_key})

    @task(3)
    def view_dashboard(self):
        """View main dashboard"""
        self.client.get("/")

    @task(2)
    def list_servers(self):
        """List user servers"""
        params = {
            "page": random.randint(1, 5),
            "per_page": random.randint(10, 50),
            "status": random.choice(["online", "offline", "starting", "stopping"]),
        }
        self.client.get("/api/v2/servers", params=params)

    @task(2)
    def view_server_details(self):
        """View specific server details"""
        server_id = random.randint(1, 1000)
        self.client.get(f"/api/v2/servers/{server_id}")

    @task(1)
    def view_server_metrics(self):
        """View server metrics"""
        server_id = random.randint(1, 1000)
        self.client.get(f"/api/v2/servers/{server_id}/metrics")

    @task(1)
    def create_server(self):
        """Create a new server"""
        server_data = {
            "name": f"test-server-{random.randint(1000, 9999)}",
            "host": f"server{random.randint(1, 100)}.example.com",
            "port": random.randint(20000, 30000),
            "game_type": random.choice(["minecraft", "ark", "rust", "gmod"]),
            "max_players": random.randint(10, 100),
            "settings": {
                "difficulty": random.choice(["easy", "normal", "hard"]),
                "pvp": random.choice([True, False]),
                "whitelist": random.choice([True, False]),
            },
        }
        self.client.post("/api/v2/servers", json=server_data)

    @task(1)
    def update_server(self):
        """Update server configuration"""
        server_id = random.randint(1, 1000)
        update_data = {
            "max_players": random.randint(10, 100),
            "settings": {"difficulty": random.choice(["easy", "normal", "hard"])},
        }
        self.client.put(f"/api/v2/servers/{server_id}", json=update_data)

    @task(1)
    def server_action(self):
        """Perform server actions (start/stop/restart)"""
        server_id = random.randint(1, 1000)
        action = random.choice(["start", "stop", "restart"])

        self.client.post(f"/api/v2/servers/{server_id}/{action}")

    @task(1)
    def view_audit_logs(self):
        """View audit logs"""
        params = {
            "page": random.randint(1, 10),
            "per_page": 20,
            "action": random.choice(
                ["server_start", "server_stop", "user_login", "server_create"]
            ),
            "user_id": random.randint(1, 100),
        }
        self.client.get("/api/v2/audit", params=params)

    @task(1)
    def background_job_status(self):
        """Check background job status"""
        job_id = f"job_{random.randint(1000, 9999)}"
        self.client.get(f"/api/jobs/{job_id}")

    @task(1)
    def cache_info(self):
        """Check cache status"""
        self.client.get("/api/cache/info")

    @task(1)
    def system_health(self):
        """Check system health"""
        self.client.get("/health")

    @task(1)
    def api_docs(self):
        """View API documentation"""
        self.client.get("/docs")


class PanelUser(HttpUser):
    """Main user class for load testing"""

    tasks = [PanelUserBehavior]
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    # Host configuration
    host = "http://localhost:8080"  # Override with --host parameter


class AdminUser(HttpUser):
    """Administrative user with higher privileges"""

    tasks = [PanelUserBehavior]
    wait_time = between(0.5, 2)  # Faster actions for admin users

    def on_start(self):
        """Admin login"""
        self.client.post(
            "/auth/jwt/login", json={"email": "admin@panel.com", "password": "admin123"}
        )


class ReadOnlyUser(HttpUser):
    """Read-only user for testing public endpoints"""

    wait_time = between(2, 8)

    @task(5)
    def view_servers(self):
        """Only view servers"""
        self.client.get("/api/v2/servers")

    @task(2)
    def system_status(self):
        """Check system status"""
        self.client.get("/health")

    @task(1)
    def api_docs(self):
        """View documentation"""
        self.client.get("/docs")


# Load testing configuration
class LoadTestConfig:
    """Configuration for different load testing scenarios"""

    @staticmethod
    def smoke_test():
        """Quick smoke test - 1 user for 1 minute"""
        return {
            "users": 1,
            "spawn_rate": 1,
            "run_time": "1m",
            "description": "Smoke test to verify basic functionality",
        }

    @staticmethod
    def load_test():
        """Standard load test - 50 users over 5 minutes"""
        return {
            "users": 50,
            "spawn_rate": 5,
            "run_time": "5m",
            "description": "Standard load test for normal usage",
        }

    @staticmethod
    def stress_test():
        """Stress test - 200 users over 10 minutes"""
        return {
            "users": 200,
            "spawn_rate": 10,
            "run_time": "10m",
            "description": "Stress test to find breaking points",
        }

    @staticmethod
    def spike_test():
        """Spike test - sudden load increase"""
        return {
            "users": 100,
            "spawn_rate": 50,  # Fast ramp-up
            "run_time": "3m",
            "description": "Spike test for sudden traffic increases",
        }

    @staticmethod
    def endurance_test():
        """Endurance test - sustained load over time"""
        return {
            "users": 30,
            "spawn_rate": 2,
            "run_time": "30m",
            "description": "Endurance test for sustained performance",
        }


# Custom metrics and monitoring
from locust import events


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize custom metrics"""
    print(f"🚀 Starting load test: {datetime.now()}")
    print(f"Target host: {environment.host}")
    print(f"Number of users: {environment.parsed_options.num_users}")
    print("-" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate test summary"""
    print("-" * 50)
    print(f"🏁 Load test completed: {datetime.now()}")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(".2f")
    print(f"Median response time: {environment.stats.total.median_response_time}ms")
    print(
        f"95th percentile: {environment.stats.total.get_response_time_percentile(0.95)}ms"
    )
    print(
        f"99th percentile: {environment.stats.total.get_response_time_percentile(0.99)}ms"
    )

    # Check for failures
    if environment.stats.total.num_failures > 0:
        print(f"❌ Failures: {environment.stats.total.num_failures}")
        print(f"Failure rate: {environment.stats.total.fail_ratio * 100:.2f}%")

    # Performance assessment
    if environment.stats.total.median_response_time < 500:
        print("✅ Performance: EXCELLENT")
    elif environment.stats.total.median_response_time < 1000:
        print("⚠️ Performance: GOOD")
    elif environment.stats.total.median_response_time < 2000:
        print("🟡 Performance: FAIR")
    else:
        print("❌ Performance: POOR")


if __name__ == "__main__":
    # Allow running as standalone script for configuration
    import argparse

    parser = argparse.ArgumentParser(description="Panel Load Testing Configuration")
    parser.add_argument(
        "--config",
        choices=["smoke", "load", "stress", "spike", "endurance"],
        default="load",
        help="Test configuration to use",
    )
    parser.add_argument(
        "--host", default="http://localhost:8080", help="Target host URL"
    )

    args = parser.parse_args()

    config = getattr(LoadTestConfig, f"{args.config}_test")()
    print(f"📋 Test Configuration: {args.config.upper()}")
    print(f"Description: {config['description']}")
    print(f"Users: {config['users']}")
    print(f"Spawn Rate: {config['spawn_rate']} users/second")
    print(f"Run Time: {config['run_time']}")
    print(f"Host: {args.host}")
    print("\nRun with:")
    print(
        f"locust -f load_testing.py --host {args.host} --users {config['users']} --spawn-rate {config['spawn_rate']} --run-time {config['run_time']}"
    )
