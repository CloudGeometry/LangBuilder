"""
Zoho Recruit Auth Component - LangBuilder Custom Component

OAuth 2.0 authentication for Zoho Recruit API with automatic token refresh.

Author: CloudGeometry
Project: AI Recruitment Command Center
"""

from lfx.custom import Component
from lfx.io import SecretStrInput, DropdownInput, Output
from lfx.schema import Data
import httpx
import time
from typing import Optional


class ZohoRecruitAuthComponent(Component):
    """
    OAuth 2.0 authentication for Zoho Recruit API.

    This component handles token refresh and provides auth configuration
    to downstream Zoho Recruit components. Tokens are cached and refreshed
    automatically 5 minutes before expiry.

    Setup:
    1. Create a Self-Client in Zoho API Console
    2. Generate a refresh token with required scopes
    3. Use the client_id, client_secret, and refresh_token here

    Required OAuth Scopes:
    - ZohoRecruit.modules.ALL
    - ZohoRecruit.modules.attachments.ALL
    - ZohoRecruit.modules.notes.ALL
    - ZohoRecruit.settings.ALL
    """

    display_name = "Recruit Auth (Zoho)"
    description = "OAuth 2.0 authentication for Zoho Recruit API"
    documentation = "https://www.zoho.com/recruit/developer-guide/apiv2/oauth-overview.html"
    icon = "Zoho"
    name = "ZohoRecruitAuth"

    # Region to base URL mapping
    REGION_URLS = {
        "US": {"api": "https://recruit.zoho.com/recruit/v2", "accounts": "https://accounts.zoho.com"},
        "EU": {"api": "https://recruit.zoho.eu/recruit/v2", "accounts": "https://accounts.zoho.eu"},
        "IN": {"api": "https://recruit.zoho.in/recruit/v2", "accounts": "https://accounts.zoho.in"},
        "AU": {"api": "https://recruit.zoho.com.au/recruit/v2", "accounts": "https://accounts.zoho.com.au"},
        "CN": {"api": "https://recruit.zoho.com.cn/recruit/v2", "accounts": "https://accounts.zoho.com.cn"},
        "JP": {"api": "https://recruit.zoho.jp/recruit/v2", "accounts": "https://accounts.zoho.jp"},
    }

    inputs = [
        SecretStrInput(
            name="client_id",
            display_name="Client ID",
            required=True,
            info="OAuth Client ID from Zoho API Console"
        ),
        SecretStrInput(
            name="client_secret",
            display_name="Client Secret",
            required=True,
            info="OAuth Client Secret from Zoho API Console"
        ),
        SecretStrInput(
            name="refresh_token",
            display_name="Refresh Token",
            required=True,
            info="Long-lived refresh token obtained via Self-Client grant"
        ),
        DropdownInput(
            name="region",
            display_name="Region",
            options=["US", "EU", "IN", "AU", "CN", "JP"],
            value="US",
            info="Zoho data center region"
        ),
    ]

    outputs = [
        Output(name="auth_config", display_name="Auth Config", method="get_auth_config"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    async def _refresh_access_token(self) -> str:
        """Refresh the access token using the refresh token."""
        urls = self.REGION_URLS.get(self.region, self.REGION_URLS["US"])
        token_url = f"{urls['accounts']}/oauth/v2/token"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                }
            )
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            raise ValueError(f"Token refresh failed: {data.get('error')}")

        self._access_token = data["access_token"]
        # Token expires in 1 hour, refresh 5 minutes early
        self._token_expiry = time.time() + data.get("expires_in", 3600) - 300

        return self._access_token

    async def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if not self._access_token or time.time() >= self._token_expiry:
            return await self._refresh_access_token()
        return self._access_token

    async def get_auth_config(self) -> Data:
        """Return auth configuration for downstream components."""
        urls = self.REGION_URLS.get(self.region, self.REGION_URLS["US"])

        try:
            # Validate credentials by fetching a token
            access_token = await self.get_access_token()

            self.status = f"Authenticated ({self.region})"

            return Data(data={
                "access_token": access_token,
                "api_base_url": urls["api"],
                "accounts_url": urls["accounts"],
                "region": self.region,
                "_auth_component": self,  # Pass self for token refresh
            })

        except httpx.HTTPStatusError as e:
            self.status = f"Auth failed: {e.response.status_code}"
            return Data(data={
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "success": False,
            })

        except Exception as e:
            self.status = f"Auth failed: {str(e)[:30]}"
            return Data(data={
                "error": str(e),
                "success": False,
            })
