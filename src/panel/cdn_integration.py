"""
Content Delivery Network (CDN) Integration
Provides global asset delivery and performance optimization
"""

import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from flask import Flask, request, url_for


class CDNManager:
    """Manages CDN integration and asset delivery"""

    def __init__(self, app: Flask):
        self.app = app
        self.cdn_url = app.config.get("CDN_URL", "")
        self.cdn_enabled = bool(self.cdn_url) and app.config.get("CDN_ENABLED", True)
        self.asset_versions = {}
        self.cache_manifest = {}

        # Asset categories for different CDN strategies
        self.asset_categories = {
            "static": ["css", "js", "images", "fonts"],
            "media": ["uploads", "avatars", "attachments"],
            "dynamic": ["generated", "temp"],
        }

    def get_asset_url(self, asset_path: str, category: str = "static") -> str:
        """Get CDN URL for asset"""
        if not self.cdn_enabled:
            return url_for("static", filename=asset_path)

        # Clean asset path
        asset_path = asset_path.lstrip("/")

        # Add version query parameter for cache busting
        version = self.get_asset_version(asset_path)
        if version:
            if "?" in asset_path:
                asset_path += f"&v={version}"
            else:
                asset_path += f"?v={version}"

        # Construct CDN URL
        cdn_asset_url = urljoin(self.cdn_url, asset_path)

        # Ensure HTTPS
        if not cdn_asset_url.startswith("https://"):
            cdn_asset_url = cdn_asset_url.replace("http://", "https://")

        return cdn_asset_url

    def get_asset_version(self, asset_path: str) -> Optional[str]:
        """Get version string for asset cache busting"""
        if asset_path in self.asset_versions:
            return self.asset_versions[asset_path]

        # Generate version based on file modification time
        try:
            static_dir = os.path.join(self.app.root_path, "static")
            file_path = os.path.join(static_dir, asset_path)

            if os.path.exists(file_path):
                mtime = os.path.getmtime(file_path)
                version = str(int(mtime))
                self.asset_versions[asset_path] = version
                return version
        except Exception:
            pass

        return None

    def preload_assets(self, asset_list: List[str]):
        """Preload assets to CDN"""
        if not self.cdn_enabled:
            return

        # In a real implementation, this would upload assets to CDN
        # For now, just mark them as available
        for asset in asset_list:
            self.cache_manifest[asset] = {
                "cdn_url": self.get_asset_url(asset),
                "last_updated": datetime.utcnow().isoformat(),
            }

    def invalidate_asset(self, asset_path: str):
        """Invalidate CDN cache for asset"""
        if not self.cdn_enabled:
            return

        # Remove from local cache manifest
        self.cache_manifest.pop(asset_path, None)
        self.asset_versions.pop(asset_path, None)

        # In production, this would call CDN API to invalidate cache
        print(f"CDN cache invalidated for: {asset_path}")

    def get_cache_manifest(self) -> Dict[str, Any]:
        """Get current cache manifest"""
        return {
            "cdn_enabled": self.cdn_enabled,
            "cdn_url": self.cdn_url,
            "assets": self.cache_manifest,
            "versions": self.asset_versions,
        }


class CloudflareCDN(CDNManager):
    """Cloudflare CDN integration"""

    def __init__(self, app: Flask):
        super().__init__(app)
        self.api_token = app.config.get("CLOUDFLARE_API_TOKEN")
        self.zone_id = app.config.get("CLOUDFLARE_ZONE_ID")

    def purge_cache(self, files: List[str] = None):
        """Purge Cloudflare cache"""
        if not self.api_token or not self.zone_id:
            print("Cloudflare credentials not configured")
            return False

        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            if files:
                # Purge specific files
                data = {"files": [urljoin(self.cdn_url, f) for f in files]}
            else:
                # Purge everything
                data = {"purge_everything": True}

            response = requests.post(
                f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/purge_cache",
                headers=headers,
                json=data,
            )

            if response.status_code == 200:
                print("Cloudflare cache purged successfully")
                return True
            else:
                print(f"Cloudflare API error: {response.text}")
                return False

        except Exception as e:
            print(f"Cloudflare purge failed: {e}")
            return False

    def get_zone_analytics(self) -> Dict[str, Any]:
        """Get Cloudflare zone analytics"""
        if not self.api_token or not self.zone_id:
            return {}

        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/analytics/dashboard",
                headers=headers,
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Cloudflare analytics error: {response.text}")
                return {}

        except Exception as e:
            print(f"Cloudflare analytics failed: {e}")
            return {}


class AWSCloudFrontCDN(CDNManager):
    """AWS CloudFront CDN integration"""

    def __init__(self, app: Flask):
        super().__init__(app)
        self.distribution_id = app.config.get("AWS_CLOUDFRONT_DISTRIBUTION_ID")
        self.access_key = app.config.get("AWS_ACCESS_KEY_ID")
        self.secret_key = app.config.get("AWS_SECRET_ACCESS_KEY")
        self.region = app.config.get("AWS_REGION", "us-east-1")

    def invalidate_cache(self, paths: List[str] = None):
        """Invalidate CloudFront cache"""
        if not self.distribution_id:
            print("CloudFront distribution ID not configured")
            return False

        try:
            import boto3

            client = boto3.client(
                "cloudfront",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )

            if paths:
                # Invalidate specific paths
                invalidation_items = [f"/{path}" for path in paths]
            else:
                # Invalidate all
                invalidation_items = ["/*"]

            response = client.create_invalidation(
                DistributionId=self.distribution_id,
                InvalidationBatch={
                    "CallerReference": str(datetime.utcnow().timestamp()),
                    "Paths": {
                        "Quantity": len(invalidation_items),
                        "Items": invalidation_items,
                    },
                },
            )

            print(f"CloudFront invalidation created: {response['Invalidation']['Id']}")
            return True

        except Exception as e:
            print(f"CloudFront invalidation failed: {e}")
            return False


class TemplateFilters:
    """Jinja2 template filters for CDN"""

    def __init__(self, cdn_manager: CDNManager):
        self.cdn_manager = cdn_manager

    def cdn_url(self, asset_path: str) -> str:
        """Template filter for CDN URLs"""
        return self.cdn_manager.get_asset_url(asset_path)

    def cdn_static(self, filename: str) -> str:
        """Template filter for static files"""
        return self.cdn_manager.get_asset_url(filename, "static")

    def cdn_media(self, filename: str) -> str:
        """Template filter for media files"""
        return self.cdn_manager.get_asset_url(filename, "media")


def create_cdn_manager(app: Flask) -> CDNManager:
    """Create appropriate CDN manager based on configuration"""
    cdn_provider = app.config.get("CDN_PROVIDER", "cloudflare").lower()

    if cdn_provider == "cloudflare":
        return CloudflareCDN(app)
    elif cdn_provider == "cloudfront":
        return AWSCloudFrontCDN(app)
    else:
        return CDNManager(app)


# Global CDN manager
cdn_manager = None
template_filters = None


def init_cdn_integration(app: Flask):
    """Initialize CDN integration"""
    global cdn_manager, template_filters

    cdn_manager = create_cdn_manager(app)
    template_filters = TemplateFilters(cdn_manager)

    # Register template filters
    app.jinja_env.filters["cdn_url"] = template_filters.cdn_url
    app.jinja_env.filters["cdn_static"] = template_filters.cdn_static
    app.jinja_env.filters["cdn_media"] = template_filters.cdn_media

    # Preload critical assets
    critical_assets = [
        "css/style.css",
        "js/app.js",
        "manifest.json",
        "icons/icon-192.png",
        "icons/icon-512.png",
    ]
    cdn_manager.preload_assets(critical_assets)

    app.logger.info(f"CDN integration initialized: {cdn_manager.cdn_url}")


def get_cdn_manager() -> Optional[CDNManager]:
    """Get the global CDN manager instance"""
    return cdn_manager


# Template helper functions
def cdn_url_for(asset_path: str) -> str:
    """Helper function for CDN URLs in templates"""
    if cdn_manager:
        return cdn_manager.get_asset_url(asset_path)
    return url_for("static", filename=asset_path)


def invalidate_cdn_cache(asset_path: str = None):
    """Invalidate CDN cache for asset or all assets"""
    if cdn_manager:
        if asset_path:
            cdn_manager.invalidate_asset(asset_path)
        else:
            # Invalidate all - implementation depends on CDN provider
            print("Full CDN cache invalidation requested")


# Performance monitoring
def get_cdn_stats() -> Dict[str, Any]:
    """Get CDN performance statistics"""
    if not cdn_manager:
        return {}

    return {
        "cdn_enabled": cdn_manager.cdn_enabled,
        "cdn_url": cdn_manager.cdn_url,
        "assets_cached": len(cdn_manager.cache_manifest),
        "asset_versions": len(cdn_manager.asset_versions),
        "cache_manifest": cdn_manager.get_cache_manifest(),
    }
