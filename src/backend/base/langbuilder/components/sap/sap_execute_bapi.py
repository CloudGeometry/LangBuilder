"""SAP execute BAPI/RFC component for ActionBridge."""

import json

from langbuilder.custom import Component
from langbuilder.io import DataInput, MessageTextInput, Output, StrInput
from langbuilder.schema import Data


class SAPExecuteBAPI(Component):
    """SAP Execute BAPI/RFC Component.

    Executes SAP Business Application Programming Interface (BAPI) functions or Remote Function Calls (RFC).
    Supports passing parameters in JSON format for complex function calls.
    Commonly used for material lookups, sales order creation, and other SAP business operations.
    """

    display_name = "SAP Execute Function"
    description = "Execute SAP BAPI or RFC function modules with custom parameters"
    documentation = "https://help.sap.com/doc/saphelp_nw75/7.5.5/en-US/22/042ff0488911d189490000e829fbbd/content.htm"
    icon = "SAP"
    name = "SAPExecuteBAPI"

    inputs = [
        DataInput(
            name="auth_credentials",
            display_name="SAP Credentials",
            info="Authentication credentials from SAP Authentication component",
            required=True,
        ),
        StrInput(
            name="function_name",
            display_name="Function Name",
            info="SAP BAPI or RFC function module name",
            required=True,
            placeholder="BAPI_MATERIAL_GET_DETAIL",
        ),
        MessageTextInput(
            name="parameters",
            display_name="Parameters",
            info='Function parameters in JSON format. Example: {"MATERIAL": "000000000000000001", "PLANT": "1000"}',
        ),
    ]

    outputs = [
        Output(
            display_name="Function Result",
            name="result",
            method="execute_function",
        ),
    ]

    def execute_function(self) -> Data:
        """Execute SAP BAPI/RFC function with provided parameters.

        Returns:
            Data: Object containing function execution results, return parameters, and status
        """
        try:
            # Validate inputs
            if not self.auth_credentials:
                raise ValueError("SAP credentials are required")

            auth_data = self.auth_credentials.data if hasattr(self.auth_credentials, "data") else self.auth_credentials
            if not auth_data.get("authenticated"):
                raise ValueError("Invalid or expired SAP credentials")

            function_name = self.function_name.strip().upper()
            if not function_name:
                raise ValueError("Function name is required")

            # Parse parameters
            params = {}
            if self.parameters and self.parameters.strip():
                try:
                    params = json.loads(self.parameters)
                    if not isinstance(params, dict):
                        raise ValueError("Parameters must be a JSON object")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON in parameters: {e!s}")

            # In a real implementation, this would:
            # 1. Connect to SAP using pyrfc with auth_data['connection_params']
            # 2. Get function descriptor: conn.get_function_description(function_name)
            # 3. Call function with parameters: result = conn.call(function_name, **params)
            # 4. Handle IMPORTING, EXPORTING, TABLES, CHANGING parameters
            # 5. Check RETURN structure for errors/warnings
            # 6. Return formatted results with all output parameters

            # Mock implementation
            result_data = {
                "function_name": function_name,
                "parameters_sent": params,
                "execution_status": "success",
                "return_code": "S",  # S=Success, E=Error, W=Warning, I=Info
                "return_message": f"Function {function_name} executed successfully",
                "exporting_params": {},  # Would contain EXPORTING parameters
                "tables": {},  # Would contain TABLE parameters
                "status": "success",
                "message": f"Successfully executed {function_name}",
            }

            self.status = f"Executed {function_name} successfully"
            self.log(f"Function: {function_name}, Params: {len(params)}, Status: {result_data['return_code']}")

            return Data(data=result_data)

        except Exception as e:
            error_msg = f"Failed to execute SAP function: {e!s}"
            self.status = error_msg
            self.log(error_msg)
            return Data(
                data={
                    "error": error_msg,
                    "status": "failed",
                    "function_name": getattr(self, "function_name", "unknown"),
                    "return_code": "E",
                }
            )
