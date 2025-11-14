"""
OAuth Service Configuration Module
Handles OAuth 2.0 configuration for external services integration
"""

import os
from typing import Dict, Optional, List
from enum import Enum


class ServiceType(str, Enum):
    GOOGLE_DRIVE = "google_drive"
    ZOHO = "zoho"
    JIRA = "jira"
    HUBSPOT = "hubspot"


class OAuthConfig:
    """Base OAuth configuration for a service"""

    def __init__(
        self,
        service_id: str,
        name: str,
        client_id: str,
        client_secret: str,
        auth_url: str,
        token_url: str,
        scopes: List[str],
        revoke_url: Optional[str] = None,
        userinfo_url: Optional[str] = None,
        api_base_url: Optional[str] = None
    ):
        self.service_id = service_id
        self.name = name
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.token_url = token_url
        self.scopes = scopes
        self.revoke_url = revoke_url
        self.userinfo_url = userinfo_url
        self.api_base_url = api_base_url

    def is_configured(self) -> bool:
        """Check if the service has required credentials configured"""
        return bool(self.client_id and self.client_secret)

    def get_scope_string(self) -> str:
        """Get scope string for OAuth request (space-separated for most services)"""
        return " ".join(self.scopes)

    def get_scope_string_comma_separated(self) -> str:
        """Get comma-separated scope string for services that require it (like Zoho)"""
        return ",".join(self.scopes)


# Google Drive OAuth Configuration - Can also use external config
def _create_google_drive_config():
    """Create Google Drive configuration, with optional external config support"""
    from open_webui.utils.oauth_config_loader import oauth_config

    # Try to get scopes from external config, fallback to hardcoded
    try:
        scopes = oauth_config.get_service_scopes("google_drive")
        if not scopes:  # If empty or not found, use defaults
            raise KeyError("No scopes found")
    except:
        scopes = [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]

    return OAuthConfig(
        service_id=ServiceType.GOOGLE_DRIVE,
        name="Google Drive",
        client_id=os.getenv("GOOGLE_DRIVE_CLIENT_ID", ""),
        client_secret=os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", ""),
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        revoke_url="https://oauth2.googleapis.com/revoke",
        userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
        api_base_url="https://www.googleapis.com/drive/v3",
        scopes=scopes
    )

GOOGLE_DRIVE_CONFIG = _create_google_drive_config()

# Zoho OAuth Configuration - Dynamic based on external config
def _create_zoho_config():
    """Create Zoho configuration from external config file"""
    from open_webui.utils.oauth_config_loader import oauth_config

    zoho_config = oauth_config.get_zoho_config()
    urls = zoho_config.get("urls", {})

    return OAuthConfig(
        service_id=ServiceType.ZOHO,
        name="Zoho",
        client_id=os.getenv("ZOHO_CLIENT_ID", ""),
        client_secret=os.getenv("ZOHO_CLIENT_SECRET", ""),
        auth_url=urls.get("auth_url", "https://accounts.zoho.com/oauth/v2/auth"),
        token_url=urls.get("token_url", "https://accounts.zoho.com/oauth/v2/token"),
        revoke_url=urls.get("revoke_url", "https://accounts.zoho.com/oauth/v2/token/revoke"),
        userinfo_url=urls.get("userinfo_url", "https://accounts.zoho.com/oauth/user/info"),
        api_base_url=urls.get("api_base_url", "https://people.zoho.com"),
        scopes=zoho_config.get("scopes", [
            "ZohoPeople.employee.ALL",
            "ZohoPeople.forms.READ",
            "ZohoPeople.attendance.ALL",
            "ZohoPeople.leave.READ",
            "ZohoPeople.timetracker.ALL",
            "AaaServer.profile.READ",
            "email"
        ])
    )

ZOHO_CONFIG = _create_zoho_config()

# Jira OAuth Configuration
JIRA_CONFIG = OAuthConfig(
    service_id=ServiceType.JIRA,
    name="Jira",
    client_id=os.getenv("JIRA_CLIENT_ID", ""),
    client_secret=os.getenv("JIRA_CLIENT_SECRET", ""),
    auth_url="https://auth.atlassian.com/authorize",
    token_url="https://auth.atlassian.com/oauth/token",
    userinfo_url="https://api.atlassian.com/me",
    api_base_url="https://api.atlassian.com",
    scopes=[
        "read:jira-work",
        "read:jira-user",
        "offline_access",  # For refresh tokens
        "read:me"  # User info
    ]
)

# HubSpot OAuth Configuration
HUBSPOT_CONFIG = OAuthConfig(
    service_id=ServiceType.HUBSPOT,
    name="HubSpot",
    client_id=os.getenv("HUBSPOT_CLIENT_ID", ""),
    client_secret=os.getenv("HUBSPOT_CLIENT_SECRET", ""),
    auth_url="https://app.hubspot.com/oauth/authorize",
    token_url="https://api.hubapi.com/oauth/v1/token",
    api_base_url="https://api.hubapi.com",
    scopes=[
        "contacts",
        "content",
        "forms",
        "tickets",
        "crm.objects.contacts.read",
        "crm.objects.companies.read",
        "crm.objects.deals.read"
    ]
)

# Service configuration registry
SERVICE_CONFIGS: Dict[str, OAuthConfig] = {
    ServiceType.GOOGLE_DRIVE: GOOGLE_DRIVE_CONFIG,
    ServiceType.ZOHO: ZOHO_CONFIG,
    ServiceType.JIRA: JIRA_CONFIG,
    ServiceType.HUBSPOT: HUBSPOT_CONFIG
}


def reload_oauth_configs():
    """Reload OAuth configurations from external config file"""
    global GOOGLE_DRIVE_CONFIG, ZOHO_CONFIG, SERVICE_CONFIGS

    # Reload the external config
    from open_webui.utils.oauth_config_loader import oauth_config
    oauth_config.reload_config()

    # Recreate configurations
    GOOGLE_DRIVE_CONFIG = _create_google_drive_config()
    ZOHO_CONFIG = _create_zoho_config()

    # Update registry
    SERVICE_CONFIGS[ServiceType.GOOGLE_DRIVE] = GOOGLE_DRIVE_CONFIG
    SERVICE_CONFIGS[ServiceType.ZOHO] = ZOHO_CONFIG

    print("[OAUTH SERVICES] Configurations reloaded from external config")


def get_service_config(service_id: str) -> Optional[OAuthConfig]:
    """Get OAuth configuration for a specific service"""
    return SERVICE_CONFIGS.get(service_id)


def get_configured_services() -> List[str]:
    """Get list of services that have credentials configured"""
    return [
        service_id
        for service_id, config in SERVICE_CONFIGS.items()
        if config.is_configured()
    ]