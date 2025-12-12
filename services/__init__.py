"""Compatibility package for legacy imports.

Provides a simple shim so that `from services.cache_service import CacheService`
continues to work by delegating to `src.panel.services.cache_service`.
"""
