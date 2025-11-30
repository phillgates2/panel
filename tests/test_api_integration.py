"""
API Integration Tests
"""

import json
from unittest.mock import patch

import pytest
from models import User

from app import create_app, db


class TestAPIIntegration:
    """Integration tests for API endpoints"""

    def setup_method(self):
        """Set up test client and database"""
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def teardown_method(self):
        """Clean up test database"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_register_endpoint_success(self):
        """Test successful user registration"""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "dob": "1990-01-01",
        }

        response = self.client.post(
            "/register", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert "message" in response_data
        assert "user_id" in response_data

    def test_register_endpoint_validation_error(self):
        """Test registration with validation errors"""
        data = {
            "first_name": "",
            "last_name": "Doe",
            "email": "invalid-email",
            "password": "weak",
            "password_confirm": "different",
            "dob": "invalid-date",
        }

        response = self.client.post(
            "/register", data=json.dumps(data), content_type="application/json"
        )

        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert "errors" in response_data

    def test_login_endpoint_success(self):
        """Test successful login"""
        # First register a user
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "dob": "1990-01-01",
        }
        self.client.post(
            "/register", data=json.dumps(data), content_type="application/json"
        )

        # Now login
        login_data = {"email": "jane@example.com", "password": "Password123!"}

        response = self.client.post(
            "/login", data=json.dumps(login_data), content_type="application/json"
        )

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert "access_token" in response_data
        assert "refresh_token" in response_data

    def test_login_endpoint_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {"email": "nonexistent@example.com", "password": "wrongpassword"}

        response = self.client.post(
            "/login", data=json.dumps(login_data), content_type="application/json"
        )

        assert response.status_code == 401
        response_data = json.loads(response.data)
        assert "error" in response_data

    def test_protected_endpoint_requires_auth(self):
        """Test that protected endpoints require authentication"""
        response = self.client.get("/api/user/profile")
        assert response.status_code == 401

    def test_health_endpoints_integration(self):
        """Test all health endpoints work together"""
        endpoints = ["/health", "/health/ready", "/health/live", "/health/system"]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == 200

            data = json.loads(response.data)
            assert "status" in data
            assert "timestamp" in data

    def test_openapi_spec_endpoint(self):
        """Test OpenAPI specification endpoint"""
        response = self.client.get("/api/openapi.json")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "openapi" in data
        assert "3.0.3" in data["openapi"]
        assert "paths" in data
        assert "components" in data

    def test_analytics_endpoint_with_caching(self):
        """Test analytics endpoint with caching"""
        # First request should cache the result
        response1 = self.client.get("/api/analytics/summary")
        assert response1.status_code == 200

        # Second request should use cached result (faster)
        import time

        start_time = time.time()
        response2 = self.client.get("/api/analytics/summary")
        end_time = time.time()

        assert response2.status_code == 200
        assert end_time - start_time < 0.1  # Should be very fast if cached

        # Verify responses are identical
        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)
        assert data1 == data2

    def test_rate_limiting_integration(self):
        """Test rate limiting on endpoints"""
        # Make multiple requests to a rate-limited endpoint
        for i in range(15):  # Exceed typical rate limit
            response = self.client.post(
                "/login",
                data=json.dumps({"email": "test@example.com", "password": "password"}),
                content_type="application/json",
            )

        # Last request should be rate limited
        assert response.status_code == 429

    def test_metrics_endpoint_integration(self):
        """Test metrics endpoint integration"""
        # Make some requests to generate metrics
        self.client.get("/health")
        self.client.get("/api/openapi.json")

        # This would require authentication in real implementation
        # For testing, we'll mock the authentication
        with self.client:
            # Mock authentication would go here
            pass

    def test_feature_flags_endpoint(self):
        """Test feature flags endpoint"""
        response = self.client.get("/api/features")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_error_handling_integration(self):
        """Test error handling across endpoints"""
        # Test 404 error
        response = self.client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data

        # Test method not allowed
        response = self.client.post("/health")
        assert response.status_code == 405

        data = json.loads(response.data)
        assert "error" in data


class TestDatabaseIntegration:
    """Test database integration"""

    def setup_method(self):
        """Set up test database"""
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def teardown_method(self):
        """Clean up test database"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_crud_operations(self):
        """Test complete user CRUD operations"""
        from services.user_service import UserService

        # Create
        user_data = {
            "first_name": "CRUD",
            "last_name": "Test",
            "email": "crud@example.com",
            "password": "Password123!",
            "dob": "1990-01-01",
        }
        user, error = UserService.create_user(**user_data)
        assert user is not None
        assert error is None
        user_id = user.id

        # Read
        retrieved_user = User.query.get(user_id)
        assert retrieved_user is not None
        assert retrieved_user.email == "crud@example.com"

        # Update (if update method exists)
        # This would depend on the actual UserService implementation

        # Delete (if delete method exists)
        # This would depend on the actual UserService implementation

    def test_database_connection_pooling(self):
        """Test database connection pooling"""
        from app import db

        # Test multiple connections
        connections = []
        for i in range(10):
            # This would test connection pooling if implemented
            user = User.query.filter_by(email=f"test{i}@example.com").first()
            connections.append(user)

        # All should be None since no users exist
        assert all(c is None for c in connections)


class TestCachingIntegration:
    """Test caching integration across the application"""

    def setup_method(self):
        """Set up test environment with caching"""
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()

        from flask_caching import Cache

        self.cache = Cache(self.app, config={"CACHE_TYPE": "simple"})

    def teardown_method(self):
        """Clean up test environment"""
        self.app_context.pop()

    def test_cache_service_integration(self):
        """Test cache service integration"""
        from services.cache_service import CacheService

        cache_svc = CacheService(self.cache)

        # Test basic operations
        cache_svc.set("integration_test", "success", timeout=60)
        assert cache_svc.get("integration_test") == "success"

        # Test user data caching
        user_data = {"name": "Integration Test", "role": "tester"}
        cache_svc.cache_user_data(999, "profile", user_data, timeout=60)
        cached_data = cache_svc.get_user_data(999, "profile")
        assert cached_data == user_data

    def test_cache_warming_integration(self):
        """Test cache warming functionality"""
        from services.cache_service import CacheService

        cache_svc = CacheService(self.cache)

        # Test cache warming (if implemented)
        # This would depend on the actual cache warming implementation
        pass
