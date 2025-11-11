"""
OAuth Configuration Loader
Handles loading OAuth settings from external JSON configuration file
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path

from open_webui.config import DATA_DIR

# Default path for OAuth configuration file
DEFAULT_OAUTH_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "oauth_config.json"
OAUTH_CONFIG_PATH = os.getenv("OAUTH_CONFIG_PATH", DEFAULT_OAUTH_CONFIG_PATH)


class OAuthConfigLoader:
    """Loads and manages OAuth configuration from external JSON file"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or OAUTH_CONFIG_PATH
        self._config = None
        self.load_config()

    def load_config(self) -> Dict:
        """Load OAuth configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)
            print(f"[OAUTH CONFIG] Loaded configuration from {self.config_path}")
            return self._config
        except FileNotFoundError:
            print(f"[OAUTH CONFIG] Configuration file not found at {self.config_path}")
            print(f"[OAUTH CONFIG] Using default hardcoded configuration")
            self._config = self._get_default_config()
            return self._config
        except json.JSONDecodeError as e:
            print(f"[OAUTH CONFIG] Invalid JSON in configuration file: {e}")
            print(f"[OAUTH CONFIG] Using default hardcoded configuration")
            self._config = self._get_default_config()
            return self._config

    def _get_default_config(self) -> Dict:
        """Return default OAuth configuration as fallback"""
        return {
            "zoho": {
                "region": "eu",
                "scopes": [
                    "ZohoPeople.employee.ALL",
                    "ZohoPeople.forms.READ",
                    "ZohoPeople.attendance.ALL",
                    "ZohoPeople.leave.READ",
                    "ZohoPeople.timetracker.ALL",
                    "AaaServer.profile.READ",
                    "email"
                ],
                "regions": {
                    "eu": {
                        "auth_url": "https://accounts.zoho.eu/oauth/v2/auth",
                        "token_url": "https://accounts.zoho.eu/oauth/v2/token",
                        "revoke_url": "https://accounts.zoho.eu/oauth/v2/token/revoke",
                        "userinfo_url": "https://accounts.zoho.eu/oauth/user/info",
                        "api_base_url": "https://people.zoho.eu"
                    }
                }
            }
        }

    def get_zoho_config(self) -> Dict:
        """Get Zoho-specific configuration"""
        if not self._config:
            self.load_config()

        zoho_config = self._config.get("zoho", {})
        region = zoho_config.get("region", "eu")
        region_config = zoho_config.get("regions", {}).get(region, {})

        return {
            "region": region,
            "scopes": zoho_config.get("scopes", []),
            "urls": region_config
        }

    def get_zoho_scopes(self) -> List[str]:
        """Get Zoho OAuth scopes"""
        return self.get_zoho_config().get("scopes", [])

    def get_zoho_region(self) -> str:
        """Get Zoho region"""
        return self.get_zoho_config().get("region", "eu")

    def get_zoho_urls(self) -> Dict[str, str]:
        """Get Zoho URLs for current region"""
        return self.get_zoho_config().get("urls", {})

    def get_service_scopes(self, service: str) -> List[str]:
        """Get scopes for any service"""
        if not self._config:
            self.load_config()

        return self._config.get(service, {}).get("scopes", [])

    def reload_config(self) -> Dict:
        """Reload configuration from file"""
        return self.load_config()

    def get_config_path(self) -> str:
        """Get current configuration file path"""
        return str(self.config_path)


# Global instance
oauth_config = OAuthConfigLoader()