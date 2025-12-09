"""Compatibility shim for cache service.

Historically tests imported `CacheService` from `services.cache_service`.
The implementation now lives in `src.panel.services.cache_service`, so this
module re-exports it to avoid breaking those imports.
"""

from src.panel.services.cache_service import CacheService  # noqa: F401

__all__ = ["CacheService"]
