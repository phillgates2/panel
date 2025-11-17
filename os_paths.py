"""
OS-aware path configuration for cross-platform support.
Automatically detects the operating system and provides appropriate paths.
"""
import os
import sys
import platform
from pathlib import Path


class OSPaths:
    """Cross-platform path configuration"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.is_linux = self.system == 'linux'
        self.is_macos = self.system == 'darwin'
        self.is_windows = self.system == 'windows'
        self.is_bsd = 'bsd' in self.system
        
        # Detect Linux distribution
        self.distro = self._detect_distro()
        
    def _detect_distro(self):
        """Detect Linux distribution"""
        if not self.is_linux:
            return None
            
        try:
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release') as f:
                    for line in f:
                        if line.startswith('ID='):
                            return line.split('=')[1].strip().strip('"')
        except:
            pass
        return 'unknown'
    
    @property
    def log_dir(self):
        """Get appropriate log directory for the OS"""
        if self.is_linux:
            # Try system log dir first, fall back to user space
            if os.access('/var/log', os.W_OK):
                return '/var/log/panel'
            else:
                return str(Path.home() / '.local' / 'share' / 'panel' / 'logs')
        elif self.is_macos:
            return str(Path.home() / 'Library' / 'Logs' / 'Panel')
        elif self.is_windows:
            return str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Panel' / 'Logs')
        else:
            return 'instance/logs'
    
    @property
    def data_dir(self):
        """Get appropriate data directory for the OS"""
        if self.is_linux:
            if os.access('/opt', os.W_OK):
                return '/opt/panel'
            else:
                return str(Path.home() / '.local' / 'share' / 'panel')
        elif self.is_macos:
            return str(Path.home() / 'Library' / 'Application Support' / 'Panel')
        elif self.is_windows:
            return str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Panel')
        else:
            return str(Path.home() / 'panel')
    
    @property
    def config_dir(self):
        """Get appropriate config directory for the OS"""
        if self.is_linux:
            if os.access('/etc', os.W_OK):
                return '/etc/panel'
            else:
                return str(Path.home() / '.config' / 'panel')
        elif self.is_macos:
            return str(Path.home() / 'Library' / 'Application Support' / 'Panel' / 'Config')
        elif self.is_windows:
            return str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Panel' / 'Config')
        else:
            return 'instance'
    
    @property
    def run_dir(self):
        """Get appropriate runtime directory for PID files"""
        if self.is_linux:
            # Try XDG_RUNTIME_DIR first
            xdg_runtime = os.environ.get('XDG_RUNTIME_DIR')
            if xdg_runtime and os.access(xdg_runtime, os.W_OK):
                return xdg_runtime
            elif os.access('/var/run', os.W_OK):
                return '/var/run/panel'
            else:
                return str(Path.home() / '.local' / 'run' / 'panel')
        elif self.is_macos:
            return str(Path.home() / 'Library' / 'Application Support' / 'Panel' / 'Run')
        elif self.is_windows:
            return str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Panel' / 'Run')
        else:
            return 'instance/run'
    
    @property
    def backup_dir(self):
        """Get appropriate backup directory for the OS"""
        if self.is_linux:
            if os.access('/var/backups', os.W_OK):
                return '/var/backups/panel'
            else:
                return str(Path.home() / '.local' / 'share' / 'panel' / 'backups')
        elif self.is_macos:
            return str(Path.home() / 'Library' / 'Application Support' / 'Panel' / 'Backups')
        elif self.is_windows:
            return str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Panel' / 'Backups')
        else:
            return 'instance/backups'
    
    @property
    def etlegacy_dir(self):
        """Get ET:Legacy installation directory"""
        if self.is_linux:
            # Check common installation paths
            if os.path.exists('/opt/etlegacy'):
                return '/opt/etlegacy'
            elif os.path.exists(str(Path.home() / 'etlegacy')):
                return str(Path.home() / 'etlegacy')
            else:
                return '/opt/etlegacy'  # Default even if doesn't exist
        elif self.is_macos:
            return str(Path.home() / 'Library' / 'Application Support' / 'etlegacy')
        elif self.is_windows:
            return str(Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'ETLegacy')
        else:
            return str(Path.home() / 'etlegacy')
    
    @property
    def nginx_config_dir(self):
        """Get Nginx configuration directory"""
        if self.is_linux:
            if self.distro in ['ubuntu', 'debian', 'linuxmint', 'pop', 'zorin']:
                return '/etc/nginx/sites-available'
            else:
                return '/etc/nginx/conf.d'
        elif self.is_macos:
            # Homebrew nginx
            return '/usr/local/etc/nginx/servers'
        else:
            return '/etc/nginx/conf.d'
    
    @property
    def service_dir(self):
        """Get systemd service directory"""
        if self.is_linux:
            if os.access('/etc/systemd/system', os.W_OK):
                return '/etc/systemd/system'
            else:
                return str(Path.home() / '.config' / 'systemd' / 'user')
        elif self.is_macos:
            return str(Path.home() / 'Library' / 'LaunchAgents')
        else:
            return None
    
    def ensure_dirs(self):
        """Create all necessary directories"""
        dirs = [
            self.log_dir,
            self.data_dir,
            self.config_dir,
            self.run_dir,
            self.backup_dir,
        ]
        
        for directory in dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_path_info(self):
        """Get path configuration summary"""
        return {
            'system': self.system,
            'distro': self.distro,
            'log_dir': self.log_dir,
            'data_dir': self.data_dir,
            'config_dir': self.config_dir,
            'run_dir': self.run_dir,
            'backup_dir': self.backup_dir,
            'etlegacy_dir': self.etlegacy_dir,
            'nginx_config_dir': self.nginx_config_dir,
            'service_dir': self.service_dir,
        }


# Global instance
os_paths = OSPaths()
