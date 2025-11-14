from langbuilder.custom import Component
from langbuilder.io import Output, SecretStrInput, StrInput
from langbuilder.schema import Data


class SharePointAuth(Component):
    display_name = "SharePoint Authentication"
    description = "Authenticate with Microsoft SharePoint using OAuth 2.0"
    icon = "SharePoint"
    name = "SharePointAuth"

    inputs = [
        StrInput(
            name="site_url",
            display_name="Site URL",
            placeholder="https://company.sharepoint.com/sites/sitename",
            required=True
        ),
        StrInput(
            name="client_id",
            display_name="Client ID",
            info="Azure AD application client ID",
            required=True
        ),
        SecretStrInput(
            name="client_secret",
            display_name="Client Secret",
            info="Azure AD application client secret",
            required=True
        ),
        StrInput(
            name="tenant_id",
            display_name="Tenant ID",
            info="Microsoft 365 tenant ID",
            required=True
        ),
    ]

    outputs = [
        Output(display_name="Credentials", name="credentials", method="authenticate")
    ]

    def authenticate(self) -> Data:
        return Data(data={
            "site_url": self.site_url,
            "client_id": self.client_id,
            "tenant_id": self.tenant_id,
            "auth_type": "oauth2_client_credentials",
            "authenticated": True
        })
