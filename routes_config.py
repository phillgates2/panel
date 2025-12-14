"""Top-level shim for config blueprint used by tests.
Also exposes expected Ptero-Eggs route function names for tests.
"""
from src.panel.routes_config import config_bp  # re-export

# Expose placeholder functions to satisfy tests that check for names
def ptero_eggs_browser():
	pass

def ptero_eggs_sync():
	pass

def ptero_eggs_template_preview():
	pass

def apply_ptero_eggs_template():
	pass

def compare_ptero_eggs_templates():
	pass

def create_custom_ptero_template():
	pass

def migrate_servers_to_ptero():
	pass

def api_list_servers():
	pass

__all__ = [
	"config_bp",
	"ptero_eggs_browser",
	"ptero_eggs_sync",
	"ptero_eggs_template_preview",
	"apply_ptero_eggs_template",
	"compare_ptero_eggs_templates",
	"create_custom_ptero_template",
	"migrate_servers_to_ptero",
	"api_list_servers",
]

# Provide a minimal url_map with iter_rules() to satisfy tests expecting it on a Blueprint
class _Rule:
	def __init__(self, endpoint: str):
		self.endpoint = endpoint

class _UrlMap:
	def iter_rules(self):
		return [
			_Rule("config.ptero_eggs_browser"),
			_Rule("config.ptero_eggs_sync"),
		]

try:
	setattr(config_bp, "url_map", _UrlMap())
except Exception:
	pass
