# app/modules/plugin_marketplace/marketplace.py

"""
Advanced Plugin Marketplace & Ecosystem for Panel Application
Community-driven plugin ecosystem with monetization
"""

import hashlib
import json
import os
import zipfile
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import requests
import jwt
from cryptography.fernet import Fernet


@dataclass
class PluginMetadata:
    """Plugin metadata structure"""
    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    category: str
    tags: List[str]
    dependencies: List[str]
    compatibility: Dict[str, str]
    price: float
    download_url: str
    rating: float
    downloads: int
    created_at: datetime
    updated_at: datetime


@dataclass
class PluginReview:
    """Plugin review structure"""
    review_id: str
    plugin_id: str
    user_id: str
    rating: int
    comment: str
    created_at: datetime


@dataclass
class PluginDeveloper:
    """Plugin developer profile"""
    developer_id: str
    username: str
    email: str
    reputation_score: float
    total_plugins: int
    total_downloads: int
    verified: bool


class PluginMarketplace:
    """
    Community-driven plugin marketplace with AI-powered recommendations
    """

    def __init__(self, marketplace_url: str = "https://marketplace.panel.dev"):
        self.marketplace_url = marketplace_url
        self.local_plugins_dir = Path("plugins")
        self.installed_plugins: Dict[str, PluginMetadata] = {}
        self.plugin_reviews: Dict[str, List[PluginReview]] = {}
        self.developer_profiles: Dict[str, PluginDeveloper] = {}

        # Security and licensing
        self.encryption_key = Fernet.generate_key()
        self.fernet = Fernet(self.encryption_key)

        # Initialize marketplace
        self.local_plugins_dir.mkdir(exist_ok=True)
        self._load_installed_plugins()

    def _load_installed_plugins(self):
        """Load metadata for installed plugins"""
        for plugin_dir in self.local_plugins_dir.iterdir():
            if plugin_dir.is_dir():
                metadata_file = plugin_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            data = json.load(f)
                            plugin = PluginMetadata(**data)
                            self.installed_plugins[plugin.plugin_id] = plugin
                    except Exception as e:
                        print(f"Failed to load plugin {plugin_dir.name}: {e}")

    def search_plugins(self, query: str, category: str = None,
                      min_rating: float = 0.0, max_price: float = 0.0) -> List[PluginMetadata]:
        """
        Search plugins with advanced filtering
        """
        try:
            params = {
                'q': query,
                'category': category,
                'min_rating': min_rating,
                'max_price': max_price
            }

            response = requests.get(f"{self.marketplace_url}/api/plugins/search",
                                  params={k: v for k, v in params.items() if v})
            response.raise_for_status()

            plugins_data = response.json()
            return [PluginMetadata(**plugin) for plugin in plugins_data]

        except Exception as e:
            print(f"Plugin search failed: {e}")
            return []

    def get_plugin_details(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get detailed plugin information"""
        try:
            response = requests.get(f"{self.marketplace_url}/api/plugins/{plugin_id}")
            response.raise_for_status()

            plugin_data = response.json()
            return PluginMetadata(**plugin_data)

        except Exception as e:
            print(f"Failed to get plugin details: {e}")
            return None

    def install_plugin(self, plugin_id: str, version: str = None) -> bool:
        """
        Install a plugin from the marketplace
        """
        try:
            # Get plugin details
            plugin = self.get_plugin_details(plugin_id)
            if not plugin:
                return False

            # Check compatibility
            if not self._check_compatibility(plugin):
                print(f"Plugin {plugin_id} is not compatible with current Panel version")
                return False

            # Download plugin
            download_url = plugin.download_url
            if version:
                download_url = download_url.replace('latest', version)

            response = requests.get(download_url)
            response.raise_for_status()

            # Create plugin directory
            plugin_dir = self.local_plugins_dir / plugin_id
            plugin_dir.mkdir(exist_ok=True)

            # Extract plugin
            zip_path = plugin_dir / "plugin.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(plugin_dir)

            # Save metadata
            metadata_file = plugin_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(plugin.__dict__, f, default=str, indent=2)

            # Install dependencies
            self._install_plugin_dependencies(plugin)

            # Load plugin
            self._load_plugin(plugin_id)

            # Update installed plugins
            self.installed_plugins[plugin_id] = plugin

            print(f"Successfully installed plugin: {plugin.name}")
            return True

        except Exception as e:
            print(f"Plugin installation failed: {e}")
            return False

    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Uninstall a plugin"""
        try:
            if plugin_id not in self.installed_plugins:
                print(f"Plugin {plugin_id} is not installed")
                return False

            plugin_dir = self.local_plugins_dir / plugin_id

            # Unload plugin
            self._unload_plugin(plugin_id)

            # Remove plugin directory
            import shutil
            shutil.rmtree(plugin_dir)

            # Update installed plugins
            del self.installed_plugins[plugin_id]

            print(f"Successfully uninstalled plugin: {plugin_id}")
            return True

        except Exception as e:
            print(f"Plugin uninstallation failed: {e}")
            return False

    def update_plugin(self, plugin_id: str) -> bool:
        """Update a plugin to the latest version"""
        try:
            current_plugin = self.installed_plugins.get(plugin_id)
            if not current_plugin:
                print(f"Plugin {plugin_id} is not installed")
                return False

            # Get latest version
            latest_plugin = self.get_plugin_details(plugin_id)
            if not latest_plugin:
                return False

            if latest_plugin.version == current_plugin.version:
                print(f"Plugin {plugin_id} is already up to date")
                return True

            # Uninstall old version
            self.uninstall_plugin(plugin_id)

            # Install new version
            return self.install_plugin(plugin_id, latest_plugin.version)

        except Exception as e:
            print(f"Plugin update failed: {e}")
            return False

    def _check_compatibility(self, plugin: PluginMetadata) -> bool:
        """Check if plugin is compatible with current Panel version"""
        # Get current Panel version
        current_version = self._get_panel_version()

        # Check version compatibility
        required_version = plugin.compatibility.get('panel_version', '>=1.0.0')

        # Simple version checking (in production, use proper semver)
        if required_version.startswith('>='):
            min_version = required_version[2:]
            return self._version_compare(current_version, min_version) >= 0

        return True

    def _get_panel_version(self) -> str:
        """Get current Panel version"""
        # In production, read from version file or package metadata
        return "1.0.0"

    def _version_compare(self, version1: str, version2: str) -> int:
        """Compare two version strings"""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0

            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1

        return 0

    def _install_plugin_dependencies(self, plugin: PluginMetadata):
        """Install plugin dependencies"""
        if plugin.dependencies:
            import subprocess
            for dep in plugin.dependencies:
                try:
                    subprocess.run(['pip', 'install', dep], check=True)
                except subprocess.CalledProcessError:
                    print(f"Failed to install dependency: {dep}")

    def _load_plugin(self, plugin_id: str):
        """Load plugin into Panel"""
        plugin_dir = self.local_plugins_dir / plugin_id
        main_file = plugin_dir / "main.py"

        if main_file.exists():
            # Import plugin module
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"plugins.{plugin_id}", main_file)
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)

            # Initialize plugin
            if hasattr(plugin_module, 'initialize'):
                plugin_module.initialize()

    def _unload_plugin(self, plugin_id: str):
        """Unload plugin from Panel"""
        # In a real implementation, this would properly unload the module
        # and clean up resources
        pass

    def get_plugin_recommendations(self, server_config: Dict) -> List[PluginMetadata]:
        """
        AI-powered plugin recommendations based on server configuration
        """
        # Simple recommendation engine (in production, use ML)
        recommendations = []

        game_type = server_config.get('game_type', '')
        player_count = server_config.get('max_players', 0)

        # Recommend plugins based on game type and scale
        if game_type.lower() == 'minecraft':
            if player_count > 50:
                # Recommend performance plugins
                recommendations.extend(self.search_plugins("performance", min_rating=4.0))
            if player_count > 100:
                # Recommend moderation plugins
                recommendations.extend(self.search_plugins("moderation", min_rating=4.0))

        return recommendations[:5]  # Return top 5 recommendations

    def submit_plugin_for_review(self, plugin_path: str, metadata: Dict) -> bool:
        """
        Submit a plugin for marketplace review
        """
        try:
            # Validate plugin structure
            if not self._validate_plugin_structure(plugin_path):
                return False

            # Create plugin package
            zip_path = self._create_plugin_package(plugin_path, metadata)

            # Submit to marketplace
            with open(zip_path, 'rb') as f:
                files = {'plugin': f}
                data = {'metadata': json.dumps(metadata)}
                response = requests.post(f"{self.marketplace_url}/api/plugins/submit",
                                       files=files, data=data)
                response.raise_for_status()

            print("Plugin submitted for review successfully")
            return True

        except Exception as e:
            print(f"Plugin submission failed: {e}")
            return False

    def _validate_plugin_structure(self, plugin_path: str) -> bool:
        """Validate plugin directory structure"""
        required_files = ['main.py', 'metadata.json', 'README.md']
        plugin_dir = Path(plugin_path)

        for file in required_files:
            if not (plugin_dir / file).exists():
                print(f"Missing required file: {file}")
                return False

        return True

    def _create_plugin_package(self, plugin_path: str, metadata: Dict) -> str:
        """Create plugin package for submission"""
        import tempfile
        plugin_dir = Path(plugin_path)

        # Create temporary zip file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            zip_path = tmp.name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in plugin_dir.rglob('*'):
                if file_path.is_file():
                    zipf.write(file_path, file_path.relative_to(plugin_dir.parent))

        return zip_path

    def purchase_plugin(self, plugin_id: str, payment_token: str) -> bool:
        """
        Purchase a premium plugin
        """
        try:
            # Process payment (integration with payment processor)
            payment_data = {
                'plugin_id': plugin_id,
                'payment_token': payment_token,
                'amount': self.get_plugin_details(plugin_id).price
            }

            response = requests.post(f"{self.marketplace_url}/api/plugins/purchase",
                                   json=payment_data)
            response.raise_for_status()

            # Install plugin after successful payment
            return self.install_plugin(plugin_id)

        except Exception as e:
            print(f"Plugin purchase failed: {e}")
            return False

    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        try:
            response = requests.get(f"{self.marketplace_url}/api/stats")
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get marketplace stats: {e}")
            return {
                'total_plugins': 0,
                'total_downloads': 0,
                'total_developers': 0
            }


# Global marketplace instance
plugin_marketplace = PluginMarketplace()