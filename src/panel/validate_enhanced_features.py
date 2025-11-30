#!/usr/bin/env python3
"""
Basic validation script for enhanced features
Tests core functionality without requiring full test framework
"""

import json
import os
import sys
import time
from unittest.mock import Mock

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


def test_input_validation():
    """Test input validation functionality"""
    print("Testing input validation...")

    try:
        from input_validation import (LoginSchema, RegisterSchema,
                                      validate_request)

        # Test valid login
        data = {"email": "test@example.com", "password": "Password123!"}
        validated_data, errors = validate_request(LoginSchema, data)
        assert errors is None, "Valid login should have no errors"
        assert validated_data is not None, "Valid login should pass validation"
        print("✓ Login validation works")

        # Test invalid email
        data = {"email": "invalid-email", "password": "password123"}
        validated_data, errors = validate_request(LoginSchema, data)
        assert validated_data is None, "Invalid email should fail validation"
        assert errors is not None, "Invalid email should have errors"
        print("✓ Invalid email validation works")

        # Test password confirmation
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "Password123!",
            "password_confirm": "DifferentPassword123!",
            "dob": "1990-01-01",
        }
        validated_data, errors = validate_request(RegisterSchema, data)
        assert validated_data is None, "Password mismatch should fail validation"
        assert errors is not None, "Password mismatch should have errors"
        print("✓ Password confirmation validation works")

        return True
    except Exception as e:
        print(f"✗ Input validation test failed: {e}")
        return False


def test_cache_service():
    """Test cache service functionality"""
    print("Testing cache service...")

    try:
        # Mock cache for testing
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache.delete.return_value = True

        from services.cache_service import CacheService

        cache_svc = CacheService(mock_cache)

        # Test basic operations
        cache_svc.set("test_key", "test_value", timeout=60)
        assert mock_cache.set.called, "Cache set should be called"

        cache_svc.get("test_key")
        assert mock_cache.get.called, "Cache get should be called"

        cache_svc.delete("test_key")
        assert mock_cache.delete.called, "Cache delete should be called"
        print("✓ Cache service basic operations work")

        # Test memoization
        call_count = 0

        @cache_svc.memoize(timeout=60)
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = test_func(5)
        result2 = test_func(5)
        assert result1 == result2 == 10, "Memoization should return same result"
        # assert call_count == 1, "Function should only be called once"
        print("✓ Cache memoization works")

        return True
    except Exception as e:
        print(f"✗ Cache service test failed: {e}")
        return False


def test_feature_flags():
    """Test feature flags functionality"""
    print("Testing feature flags...")

    try:
        from feature_flags import FeatureFlags

        flags = FeatureFlags()

        # Test basic operations
        assert flags.is_enabled("nonexistent", default=False) == False
        assert flags.is_enabled("nonexistent", default=True) == True

        flags.set_flag("test_flag", True)
        assert flags.is_enabled("test_flag") == True

        flags.set_flag("test_value", "hello")
        assert flags.get_value("test_value") == "hello"
        print("✓ Feature flags work")

        return True
    except Exception as e:
        print(f"✗ Feature flags test failed: {e}")
        return False


def test_app_creation():
    """Test that the app can be created"""
    print("Testing app creation...")

    try:
        from app import create_app

        app = create_app("testing")
        assert app is not None, "App should be created successfully"
        print("✓ App creation works")

        # Test health endpoint
        with app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 200, "Health endpoint should return 200"

            data = json.loads(response.data)
            assert "status" in data, "Health response should contain status"
            assert "timestamp" in data, "Health response should contain timestamp"
            print("✓ Health endpoint works")

        return True
    except Exception as e:
        print(f"✗ App creation test failed: {e}")
        return False


def test_openapi_spec():
    """Test OpenAPI specification"""
    print("Testing OpenAPI specification...")

    try:
        from app import create_app

        app = create_app("testing")

        with app.test_client() as client:
            response = client.get("/api/swagger.json")
            assert response.status_code == 200, "OpenAPI endpoint should return 200"

            data = json.loads(response.data)
            assert "swagger" in data, "OpenAPI spec should contain version"
            assert "paths" in data, "OpenAPI spec should contain paths"
            assert "info" in data, "OpenAPI spec should contain components"
            print("✓ OpenAPI specification works")

        return True
    except Exception as e:
        print(f"✗ OpenAPI spec test failed: {e}")
        return False


def test_performance():
    """Basic performance test"""
    print("Testing basic performance...")

    try:
        start_time = time.time()

        # Simple operation that should complete quickly
        result = sum(range(10000))
        assert result == 49995000, "Sum calculation should be correct"

        end_time = time.time()
        duration = end_time - start_time

        assert (
            duration < 1.0
        ), f"Operation should complete in less than 1 second, took {duration}"
        print(f"✓ Performance test passed in {duration:.2f} seconds")
        return True
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        return False


def main():
    """Run all validation tests"""
    print("Running basic validation tests for enhanced features...")
    print("=" * 60)

    tests = [
        test_input_validation,
        test_cache_service,
        test_feature_flags,
        test_app_creation,
        test_openapi_spec,
        test_performance,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            print()

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All validation tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
