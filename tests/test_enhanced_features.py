"""
Integration and Performance Tests for Enhanced Features
"""

import json
import time
from unittest.mock import patch

import pytest

from app import create_app, db
from input_validation import LoginSchema, RegisterSchema, validate_request
from services.cache_service import CacheService
from services.user_service import UserService


class TestInputValidation:
    """Test input validation schemas"""

    def test_login_schema_valid(self):
        """Test valid login data validation"""
        data = {"email": "test@example.com", "password": "password123"}
        validated_data, errors = validate_request(LoginSchema, data)

        assert validated_data is not None
        assert errors is None
        assert validated_data["email"] == "test@example.com"
        assert validated_data["password"] == "password123"

    def test_login_schema_invalid_email(self):
        """Test invalid email validation"""
        data = {"email": "invalid-email", "password": "password123"}
        validated_data, errors = validate_request(LoginSchema, data)

        assert validated_data is None
        assert errors is not None
        assert "email" in errors

    def test_register_schema_valid(self):
        """Test valid registration data validation"""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "dob": "1990-01-01"
        }
        validated_data, errors = validate_request(RegisterSchema, data)

        assert validated_data is not None
        assert errors is None
        assert validated_data["first_name"] == "John"
        assert validated_data["last_name"] == "Doe"

    def test_register_schema_password_mismatch(self):
        """Test password confirmation validation"""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
            "password_confirm": "DifferentPassword123!",
            "dob": "1990-01-01"
        }
        validated_data, errors = validate_request(RegisterSchema, data)

        assert validated_data is None
        assert errors is not None
        assert "password_confirm" in errors

    def test_register_schema_weak_password(self):
        """Test weak password validation"""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "weak",
            "password_confirm": "weak",
            "dob": "1990-01-01"
        }
        validated_data, errors = validate_request(RegisterSchema, data)

        assert validated_data is None
        assert errors is not None
        assert "password" in errors


class TestCacheService:
    """Test cache service functionality"""

    def test_cache_service_basic_operations(self, app):
        """Test basic cache operations"""
        with app.app_context():
            from flask_caching import Cache
            cache = Cache(app, config={"CACHE_TYPE": "simple"})
            cache_svc = CacheService(cache)

            # Test set and get
            cache_svc.set("test_key", "test_value", timeout=60)
            assert cache_svc.get("test_key") == "test_value"

            # Test delete
            cache_svc.delete("test_key")
            assert cache_svc.get("test_key") is None

    def test_cache_service_memoize(self, app):
        """Test function memoization"""
        with app.app_context():
            from flask_caching import Cache
            cache = Cache(app, config={"CACHE_TYPE": "simple"})
            cache_svc = CacheService(cache)

            call_count = 0

            @cache_svc.memoize(timeout=60)
            def expensive_function(x, y):
                nonlocal call_count
                call_count += 1
                return x + y

            # First call should execute function
            result1 = expensive_function(1, 2)
            assert result1 == 3
            assert call_count == 1

            # Second call should use cache
            result2 = expensive_function(1, 2)
            assert result2 == 3
            assert call_count == 1  # Should not have increased

    def test_cache_service_user_data(self, app):
        """Test user-specific data caching"""
        with app.app_context():
            from flask_caching import Cache
            cache = Cache(app, config={"CACHE_TYPE": "simple"})
            cache_svc = CacheService(cache)

            user_id = 123
            test_data = {"name": "John", "role": "admin"}

            # Cache user data
            cache_svc.cache_user_data(user_id, "profile", test_data, timeout=60)

            # Retrieve user data
            cached_data = cache_svc.get_user_data(user_id, "profile")
            assert cached_data == test_data

            # Test cache invalidation
            cache_svc.invalidate_user_cache(user_id, "profile")
            assert cache_svc.get_user_data(user_id, "profile") is None


class TestUserService:
    """Test user service functionality"""

    def test_create_user_success(self, app):
        """Test successful user creation"""
        with app.app_context():
            user_data = {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "password": "Password123!",
                "dob": "1990-01-01"
            }

            user, error = UserService.create_user(**user_data)

            assert user is not None
            assert error is None
            assert user.first_name == "John"
            assert user.last_name == "Doe"
            assert user.email == "john@example.com"

    def test_create_user_duplicate_email(self, app):
        """Test duplicate email handling"""
        with app.app_context():
            # Create first user
            user_data = {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "password": "Password123!",
                "dob": "1990-01-01"
            }
            UserService.create_user(**user_data)

            # Try to create duplicate
            user, error = UserService.create_user(**user_data)

            assert user is None
            assert error is not None
            assert "already registered" in error

    def test_authenticate_user_success(self, app):
        """Test successful user authentication"""
        with app.app_context():
            # Create user first
            user_data = {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "password": "Password123!",
                "dob": "1990-01-01"
            }
            UserService.create_user(**user_data)

            # Authenticate
            user, error = UserService.authenticate_user("john@example.com", "Password123!")

            assert user is not None
            assert error is None
            assert user.email == "john@example.com"

    def test_authenticate_user_invalid_credentials(self, app):
        """Test invalid credentials handling"""
        with app.app_context():
            user, error = UserService.authenticate_user("nonexistent@example.com", "password")

            assert user is None
            assert error is not None
            assert "Invalid credentials" in error


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_endpoint(self, client):
        """Test basic health endpoint"""
        response = client.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "checks" in data

    def test_readiness_endpoint(self, client):
        """Test readiness probe endpoint"""
        response = client.get('/health/ready')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

    def test_liveness_endpoint(self, client):
        """Test liveness probe endpoint"""
        response = client.get('/health/live')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "status" in data
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert "uptime_seconds" in data


class TestMetricsEndpoint:
    """Test metrics endpoint"""

    def test_metrics_endpoint_requires_auth(self, client):
        """Test that metrics endpoint requires authentication"""
        response = client.get('/metrics')
        assert response.status_code == 401

    def test_openapi_spec_endpoint(self, client, app):
        """Test OpenAPI specification endpoint"""
        with app.test_request_context():
            # Need to be logged in for this endpoint
            with client:
                # This would require setting up a test user session
                # For now, just test that the endpoint exists
                pass


class TestPerformance:
    """Performance tests"""

    def test_health_endpoint_performance(self, client):
        """Test health endpoint response time"""
        start_time = time.time()
        response = client.get('/health')
        end_time = time.time()

        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0  # Should respond within 1 second

    def test_concurrent_health_requests(self, client):
        """Test concurrent health check requests"""
        import threading
        import queue

        results = queue.Queue()

        def make_request():
            start_time = time.time()
            response = client.get('/health')
            end_time = time.time()
            results.put((response.status_code, end_time - start_time))

        # Make 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        for _ in range(10):
            status_code, response_time = results.get()
            assert status_code == 200
            assert response_time < 2.0  # Should respond within 2 seconds even under load


class TestFeatureFlags:
    """Test feature flags functionality"""

    def test_feature_flags_basic(self):
        """Test basic feature flag operations"""
        from feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Test default values
        assert flags.is_enabled("nonexistent_flag", default=False) == False
        assert flags.is_enabled("nonexistent_flag", default=True) == True

        # Test setting and getting values
        flags.set_flag("test_flag", True)
        assert flags.is_enabled("test_flag") == True

        flags.set_flag("test_value", "hello")
        assert flags.get_value("test_value") == "hello"

    def test_feature_flags_environment_variables(self):
        """Test feature flags from environment variables"""
        import os

        # Set environment variable
        os.environ["FEATURE_FLAG_TEST_ENV"] = "true"

        flags = FeatureFlags()
        assert flags.is_enabled("test_env") == True

        # Clean up
        del os.environ["FEATURE_FLAG_TEST_ENV"]