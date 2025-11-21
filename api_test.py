#!/usr/bin/env python3
"""
Panel API Testing Script

This script helps you test the Panel REST API endpoints.
Make sure to set your API token before running.

Usage:
    python api_test.py --token YOUR_API_TOKEN --base-url http://localhost:8080

Requirements:
    pip install requests
"""

import argparse
import json
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)


class PanelAPITester:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def make_request(self, method, endpoint, data=None):
        """Make an API request."""
        url = f"{self.base_url}/api/v1{endpoint}"
        print(f"\n{method.upper()} {url}")

        try:
            if method.lower() == "get":
                response = self.session.get(url)
            elif method.lower() == "post":
                response = self.session.post(url, json=data)
            else:
                print(f"Unsupported method: {method}")
                return None

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print("Response:")
                    print(json.dumps(result, indent=2))
                    return result
                except:
                    print(f"Raw Response: {response.text}")
                    return response.text
            else:
                print(f"Error: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def test_health(self):
        """Test API health endpoint."""
        print("=== Testing API Health ===")
        return self.make_request("get", "/health")

    def test_servers_list(self):
        """Test servers list endpoint."""
        print("=== Testing Servers List ===")
        return self.make_request("get", "/servers")

    def test_server_detail(self, server_id):
        """Test server detail endpoint."""
        print(f"=== Testing Server Detail (ID: {server_id}) ===")
        return self.make_request("get", f"/servers/{server_id}")

    def test_server_command(self, server_id, command):
        """Test server command endpoint."""
        print(f"=== Testing Server Command (ID: {server_id}) ===")
        data = {"command": command}
        return self.make_request("post", f"/servers/{server_id}/command", data)

    def run_all_tests(self):
        """Run all available tests."""
        print(f"Panel API Testing - {datetime.now()}")
        print(f"Base URL: {self.base_url}")
        print("=" * 50)

        # Test health
        health = self.test_health()
        if not health:
            print("Health check failed. Stopping tests.")
            return

        # Test servers list
        servers = self.test_servers_list()
        if not servers or "servers" not in servers:
            print("Failed to get servers list.")
            return

        if not servers["servers"]:
            print("No servers available for testing.")
            return

        # Test first server
        server_id = servers["servers"][0]["id"]
        print(f"\nUsing server ID: {server_id} for further tests")

        # Test server detail
        self.test_server_detail(server_id)

        # Test server command (safe command)
        self.test_server_command(server_id, "status")

        print("\n=== Testing Complete ===")


def main():
    parser = argparse.ArgumentParser(description="Panel API Testing Script")
    parser.add_argument("--token", required=True, help="API token")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080",
        help="Base URL of the panel (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--test",
        choices=["health", "servers", "command", "all"],
        default="all",
        help="Specific test to run",
    )

    args = parser.parse_args()

    tester = PanelAPITester(args.base_url, args.token)

    if args.test == "health":
        tester.test_health()
    elif args.test == "servers":
        servers = tester.test_servers_list()
        if servers and servers.get("servers"):
            tester.test_server_detail(servers["servers"][0]["id"])
    elif args.test == "command":
        servers = tester.test_servers_list()
        if servers and servers.get("servers"):
            tester.test_server_command(servers["servers"][0]["id"], "status")
    else:
        tester.run_all_tests()


if __name__ == "__main__":
    main()
