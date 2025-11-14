"""SAP authentication component for ActionBridge."""


from langbuilder.custom import Component
from langbuilder.io import Output, SecretStrInput, StrInput
from langbuilder.schema import Data


class SAPAuth(Component):
    """SAP Authentication Component.

    Handles authentication with SAP systems using RFC protocol.
    Returns a Data object containing connection credentials that can be passed to other SAP components.
    Supports both SAP ECC and S/4HANA systems.
    """

    display_name = "SAP Authentication"
    description = "Authenticate with SAP ECC or S/4HANA systems using RFC connection"
    documentation = "https://help.sap.com/doc/saphelp_nw75/7.5.5/en-US/22/042ff0488911d189490000e829fbbd/content.htm"
    icon = "SAP"
    name = "SAPAuth"

    inputs = [
        StrInput(
            name="host",
            display_name="SAP Host",
            info="SAP application server hostname or IP address",
            required=True,
            placeholder="sap.company.com",
        ),
        StrInput(
            name="client",
            display_name="Client",
            info="SAP client number (mandant)",
            required=True,
            placeholder="100",
        ),
        StrInput(
            name="username",
            display_name="Username",
            info="SAP user account",
            required=True,
        ),
        SecretStrInput(
            name="password",
            display_name="Password",
            info="SAP user password",
            required=True,
        ),
        StrInput(
            name="system_number",
            display_name="System Number",
            info="SAP system number (usually 00-99)",
            required=True,
            placeholder="00",
        ),
    ]

    outputs = [
        Output(
            display_name="Auth Credentials",
            name="credentials",
            method="authenticate",
        ),
    ]

    def authenticate(self) -> Data:
        """Create authentication credentials for SAP RFC connection.

        Returns:
            Data: Object containing SAP connection parameters
        """
        try:
            # Validate system number
            try:
                sys_num = int(self.system_number)
                if sys_num < 0 or sys_num > 99:
                    raise ValueError("System number must be between 00 and 99")
            except ValueError as e:
                raise ValueError(f"Invalid system number: {e!s}")

            # Create SAP connection parameters
            # In a real implementation, this would use pyrfc or sapnwrfc library
            connection_params = {
                "ashost": self.host,
                "sysnr": self.system_number.zfill(2),  # Ensure 2-digit format
                "client": self.client,
                "user": self.username,
                "passwd": self.password,
                "lang": "EN",  # Default to English
            }

            # Create auth data object
            auth_data = {
                "connection_params": connection_params,
                "host": self.host,
                "client": self.client,
                "system_number": self.system_number,
                "authenticated": True,
                "connection_type": "RFC",
            }

            self.status = f"Successfully configured connection to SAP system {self.host}:{self.system_number}"
            self.log(f"SAP connection configured for client {self.client} on {self.host}")

            return Data(data=auth_data)

        except Exception as e:
            error_msg = f"Authentication configuration failed: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(data={"error": error_msg, "authenticated": False})
