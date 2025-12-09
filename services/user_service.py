"""Compatibility shim for user service."""

from src.panel.services.user_service import UserService  # noqa: F401

__all__ = ["UserService"]