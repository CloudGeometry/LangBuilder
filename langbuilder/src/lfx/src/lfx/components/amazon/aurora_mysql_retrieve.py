"""
Aurora MySQL Retrieve Component for LangBuilder

Executes SQL queries on Aurora MySQL databases with flexible query support.
Supports:
  - IAM Database Authentication (token) + direct MySQL connection (PyMySQL)
  - Direct password auth (PyMySQL)
  - Aurora Data API mode (resourceArn/secretArn) (no MySQL driver needed)

Includes a built-in DEBUG PRECHECK so you can see:
  - whether AWS creds are visible to boto3
  - sts:GetCallerIdentity result (or error)
  - Data API permissions test (optional)
  - IAM token generation test (optional)

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

import json
from typing import Any, Dict, List, Tuple, Union

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from lfx.base.langchain_utilities.model import LCToolComponent
from langflow.field_typing import Tool
from langflow.io import (
    BoolInput,
    DataInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    SecretStrInput,
    StrInput,
)
from langflow.schema.data import Data
from langflow.schema.message import Message


# -----------------------------
# Hardcoded defaults (as requested)
# -----------------------------
RESOURCE_ARN = "arn:aws:rds:us-east-1:728538925474:cluster:ai-recruit-db"
SECRET_ARN = "arn:aws:secretsmanager:us-east-1:728538925474:secret:rds!cluster-4a77d185-10f5-400a-bdd6-9262cd94b300-MJZhbq"
DATABASE_NAME = "ai-recruit"
REGION = "us-east-1"


AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-north-1", "ap-south-1", "ap-northeast-1",
    "ap-northeast-2", "ap-northeast-3", "ap-southeast-1",
    "ap-southeast-2", "sa-east-1",
]


def _unwrap_secret(v):
    return getattr(v, "get_secret_value", lambda: v)()


def _mask_arn(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if len(s) <= 24:
        return s
    return f"{s[:12]}...{s[-12:]}"


class AuroraMySQLRetrieveComponent(LCToolComponent):
    display_name = "Aurora MySQL Retrieve"
    description = (
        "Execute SQL queries on Aurora MySQL. Supports IAM token or password for direct MySQL, "
        "and Aurora Data API mode."
    )
    documentation = "https://docs.langbuilder.org/components-amazon#aurora-mysql-retrieve"
    icon = "database"
    name = "AuroraMySQLRetrieve"
    metadata = {"keywords": ["aurora", "mysql", "database", "query", "aws", "rds", "retrieve", "iam", "data api"]}

    inputs = [
        # Connection settings (Direct MySQL mode)
        StrInput(
            name="host",
            display_name="Host",
            required=False,
            info="Aurora cluster endpoint. Needed for direct MySQL mode.",
        ),
        StrInput(
            name="port",
            display_name="Port",
            value="3306",
            required=False,
            info="Database port (default: 3306). Needed for direct MySQL mode.",
        ),
        StrInput(
            name="database",
            display_name="Database",
            value=DATABASE_NAME,
            required=True,
            info="Database/schema name. Used in both modes.",
        ),
        StrInput(
            name="username",
            display_name="Username",
            required=False,
            info="DB username (IAM-enabled user for IAM auth, or normal user for password auth). Direct MySQL mode.",
        ),

        # Mode switches
        BoolInput(
            name="use_data_api",
            display_name="Use Aurora Data API",
            value=True,
            info="If True, uses boto3 rds-data (no MySQL driver needed). Uses hardcoded ARNs if fields are empty.",
        ),
        BoolInput(
            name="use_iam_auth",
            display_name="Use IAM Authentication",
            value=True,
            info="Direct MySQL mode only: generate an IAM auth token (boto3) instead of using a DB password.",
        ),

        # Password (only used if direct MySQL mode + IAM disabled)
        SecretStrInput(
            name="password",
            display_name="Password",
            required=False,
            info="DB password (only required if IAM Authentication is disabled and Data API is off)",
            advanced=True,
        ),

        # AWS region + optional explicit credentials (normally leave blank if using IAM role)
        DropdownInput(
            name="region_name",
            display_name="AWS Region",
            options=AWS_REGIONS,
            value=REGION,
            required=True,
            info="AWS region where Aurora cluster is located",
        ),
        SecretStrInput(
            name="aws_access_key_id",
            display_name="AWS Access Key ID",
            required=False,
            info="Leave empty to use IAM role or environment credentials",
            advanced=True,
        ),
        SecretStrInput(
            name="aws_secret_access_key",
            display_name="AWS Secret Access Key",
            required=False,
            info="Leave empty to use IAM role or environment credentials",
            advanced=True,
        ),
        SecretStrInput(
            name="aws_session_token",
            display_name="AWS Session Token",
            required=False,
            info="For temporary credentials (optional)",
            advanced=True,
        ),

        # Data API identifiers (optional: will fallback to hardcoded values above)
        StrInput(
            name="resource_arn",
            display_name="Data API Cluster ARN (resourceArn)",
            required=False,
            advanced=True,
            info="Optional override. If empty, uses the hardcoded RESOURCE_ARN in this file.",
        ),
        SecretStrInput(
            name="secret_arn",
            display_name="Data API Secret ARN (secretArn)",
            required=False,
            advanced=True,
            info="Optional override. If empty, uses the hardcoded SECRET_ARN in this file.",
        ),

        # Query configuration
        MessageTextInput(
            name="query",
            display_name="SQL Query",
            required=True,
            tool_mode=True,
            info=(
                "SQL query to execute.\n"
                "- Direct MySQL mode uses `%s` placeholders for parameters.\n"
                "- Data API mode supports named params like `:candidate_id`.\n"
                "Tip: don't prepend `USE db;` — set Database field instead."
            ),
        ),
        DataInput(
            name="query_params",
            display_name="Query Parameters",
            required=False,
            tool_mode=True,
            info=(
                "Params as Data.\n"
                "Direct MySQL (positional): {'params': ['v1','v2']}\n"
                "Data API (named): {'candidate_id': '123'}"
            ),
        ),

        # Result options
        IntInput(
            name="limit",
            display_name="Result Limit",
            value=100,
            required=False,
            advanced=True,
            info="Maximum number of rows to return (0 for unlimited).",
        ),
        BoolInput(
            name="return_single",
            display_name="Return Single Result",
            value=False,
            advanced=True,
            info="If True, returns only the first row",
        ),
        BoolInput(
            name="include_metadata",
            display_name="Include Metadata",
            value=True,
            advanced=True,
            info="Include metadata in result",
        ),

        # Connection options (direct MySQL mode)
        IntInput(
            name="connect_timeout",
            display_name="Connection Timeout",
            value=10,
            advanced=True,
            info="Connection timeout in seconds",
        ),

        # DEBUG options
        BoolInput(
            name="debug_mode",
            display_name="Debug Mode",
            value=True,
            advanced=True,
            info="If True, adds AWS credential + permission precheck info to outputs and errors.",
        ),
        BoolInput(
            name="debug_only",
            display_name="Debug Only (do not run SQL)",
            value=False,
            advanced=True,
            info="If True, runs only the AWS precheck and returns it (no SQL executed).",
        ),
        BoolInput(
            name="soft_fail",
            display_name="Soft Fail (return errors as output)",
            value=True,
            advanced=True,
            info="If True, returns errors inside Message instead of raising (easier debugging).",
        ),
        BoolInput(
            name="debug_test_data_api",
            display_name="Debug: Test Data API with SELECT 1",
            value=True,
            advanced=True,
            info="If True and Data API is enabled, tries a harmless SELECT 1 to confirm permissions.",
        ),
    ]

    # ---------- Effective defaults (use hardcoded values if inputs are empty) ----------

    def _effective_data_api_config(self) -> Tuple[str, str, str]:
        resource_arn = (str(getattr(self, "resource_arn", "") or "").strip() or RESOURCE_ARN)
        secret_arn = (str(_unwrap_secret(getattr(self, "secret_arn", "")) or "").strip() or SECRET_ARN)
        database = (str(getattr(self, "database", "") or "").strip() or DATABASE_NAME)
        return resource_arn, secret_arn, database

    # ---------- AWS helpers ----------

    def _get_boto3_client(self, service_name: str):
        import boto3

        access_key = str(_unwrap_secret(getattr(self, "aws_access_key_id", "")) or "").strip()
        secret_key = str(_unwrap_secret(getattr(self, "aws_secret_access_key", "")) or "").strip()
        session_token = str(_unwrap_secret(getattr(self, "aws_session_token", "")) or "").strip()

        kwargs = {"region_name": self.region_name}
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
            if session_token:
                kwargs["aws_session_token"] = session_token

        return boto3.client(service_name, **kwargs)


    def _aws_preflight(self) -> Dict[str, Any]:
        """
        Returns a debug dictionary. Never raises.
        """
        resource_arn_eff, secret_arn_eff, database_eff = self._effective_data_api_config()

        info: Dict[str, Any] = {
            "region": self.region_name,
            "mode": "data_api" if self.use_data_api else ("iam_mysql" if self.use_iam_auth else "password_mysql"),
            "database_effective": database_eff,
            "data_api_resource_arn_effective": _mask_arn(resource_arn_eff),
            "data_api_secret_arn_effective": _mask_arn(secret_arn_eff),
        }

        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

            session = boto3.session.Session()
            creds = session.get_credentials()
            if creds is None:
                info["credentials_found"] = False
                info["credentials_method"] = None
            else:
                frozen = creds.get_frozen_credentials()
                info["credentials_found"] = True
                info["credentials_method"] = getattr(creds, "method", None)
                ak = getattr(frozen, "access_key", None) or ""
                info["access_key_last4"] = ak[-4:] if ak else None

            # STS identity
            try:
                sts = self._get_boto3_client("sts")
                ident = sts.get_caller_identity()
                info["sts_ok"] = True
                info["caller_account"] = ident.get("Account")
                info["caller_arn"] = ident.get("Arn")
            except (NoCredentialsError, PartialCredentialsError) as e:
                info["sts_ok"] = False
                info["sts_error"] = f"NoCredentials: {e}"
            except ClientError as e:
                info["sts_ok"] = False
                info["sts_error"] = f"ClientError: {e}"
            except Exception as e:
                info["sts_ok"] = False
                info["sts_error"] = f"Error: {e}"

            # Mode-specific quick tests
            if self.use_data_api and self.debug_test_data_api:
                try:
                    rds_data = self._get_boto3_client("rds-data")
                    resp = rds_data.execute_statement(
                        resourceArn=resource_arn_eff,
                        secretArn=secret_arn_eff,
                        database=database_eff,
                        sql="SELECT 1 AS ok",
                        includeResultMetadata=True,
                    )
                    info["data_api_test_ok"] = True
                    info["data_api_test_records"] = resp.get("records", [])
                except (NoCredentialsError, PartialCredentialsError) as e:
                    info["data_api_test_ok"] = False
                    info["data_api_test_error"] = f"NoCredentials: {e}"
                except ClientError as e:
                    info["data_api_test_ok"] = False
                    info["data_api_test_error"] = f"ClientError: {e}"
                except Exception as e:
                    info["data_api_test_ok"] = False
                    info["data_api_test_error"] = f"Error: {e}"

            if (not self.use_data_api) and self.use_iam_auth:
                try:
                    if not self.host or not self.username:
                        info["iam_token_test_ok"] = False
                        info["iam_token_test_error"] = "Missing host or username"
                    else:
                        rds = self._get_boto3_client("rds")
                        token = rds.generate_db_auth_token(
                            DBHostname=self.host,
                            Port=int(self.port or 3306),
                            DBUsername=self.username,
                            Region=self.region_name,
                        )
                    info["iam_token_test_ok"] = True
                    info["iam_token_length"] = len(token or "")
                    info["iam_token_prefix"] = (token[:10] + "...") if token else None
                except (NoCredentialsError, PartialCredentialsError) as e:
                    info["iam_token_test_ok"] = False
                    info["iam_token_test_error"] = f"NoCredentials: {e}"
                except ClientError as e:
                    info["iam_token_test_ok"] = False
                    info["iam_token_test_error"] = f"ClientError: {e}"
                except Exception as e:
                    info["iam_token_test_ok"] = False
                    info["iam_token_test_error"] = f"Error: {e}"

        except Exception as e:
            info["preflight_error"] = f"Unexpected preflight error: {e}"

        return info

    # ---------- Params extraction ----------

    def _extract_params(self, input_data: Any) -> Union[Tuple, Dict]:
        if input_data is None:
            return ()

        if hasattr(input_data, "data"):
            data = input_data.data
            if isinstance(data, dict):
                if "params" in data:
                    params = data["params"]
                    return tuple(params) if isinstance(params, (list, tuple)) else (params,)
                return data
            if isinstance(data, (list, tuple)):
                return tuple(data)
            return (data,)

        if hasattr(input_data, "text"):
            text = str(input_data.text).strip()
            return (text,) if text else ()

        if isinstance(input_data, dict):
            return input_data
        if isinstance(input_data, (list, tuple)):
            return tuple(input_data)
        if input_data:
            return (str(input_data),)
        return ()

    # ---------- Data API mode ----------

    def _data_api_execute(self) -> Tuple[List[Dict[str, Any]], List[str]]:
        resource_arn_eff, secret_arn_eff, database_eff = self._effective_data_api_config()

        params = self._extract_params(self.query_params) if hasattr(self, "query_params") else ()
        q = str(self.query)

        # Build Data API parameters (named preferred)
        rds_params = []
        if isinstance(params, dict):
            for k, v in params.items():
                if v is None:
                    rds_params.append({"name": str(k), "value": {"isNull": True}})
                else:
                    rds_params.append({"name": str(k), "value": {"stringValue": str(v)}})
        else:
            # positional -> map to :p1, :p2 if query uses %s
            if "%s" in q and params:
                for i in range(len(params)):
                    q = q.replace("%s", f":p{i+1}", 1)
            for i, v in enumerate(params, 1):
                if v is None:
                    rds_params.append({"name": f"p{i}", "value": {"isNull": True}})
                else:
                    rds_params.append({"name": f"p{i}", "value": {"stringValue": str(v)}})

        client = self._get_boto3_client("rds-data")
        response = client.execute_statement(
            resourceArn=resource_arn_eff,
            secretArn=secret_arn_eff,
            database=database_eff,
            sql=q,
            parameters=rds_params,
            includeResultMetadata=True,
        )

        records = response.get("records", []) or []
        col_meta = response.get("columnMetadata", []) or []
        columns = [c.get("name") for c in col_meta] if col_meta else []

        results: List[Dict[str, Any]] = []
        for row in records:
            out = {}
            for idx, field in enumerate(row):
                col = columns[idx] if idx < len(columns) and columns[idx] else f"col_{idx}"
                if field.get("isNull"):
                    out[col] = None
                else:
                    k = next(iter(field.keys())) if field else None
                    out[col] = field.get(k) if k else None
            results.append(out)

        return results, columns

    # ---------- Direct MySQL mode (with robust auto-install) ----------

    def _ensure_pymysql(self):
        """
        Robustly ensure PyMySQL is importable in the *current worker runtime*.

        Why this exists:
          - In some LangBuilder deployments, module import happens in a different process
            than tool execution (or a different venv/container).
          - Installing at top-of-file often installs in the wrong place or is blocked.
          - This installs into a known-writable target (/tmp/...) and adds it to sys.path.

        If install fails, raises ImportError with pip stdout/stderr included.
        """
        import importlib
        import os
        import sys
        import subprocess
        import tempfile

        try:
            pymysql = importlib.import_module("pymysql")
            DictCursor = importlib.import_module("pymysql.cursors").DictCursor
            return pymysql, DictCursor
        except Exception as first:
            target = os.path.join(tempfile.gettempdir(), "langbuilder_pip")
            os.makedirs(target, exist_ok=True)

            if target not in sys.path:
                sys.path.insert(0, target)

            cmd = [
                sys.executable, "-m", "pip", "install",
                "--upgrade",
                "--no-input",
                "--disable-pip-version-check",
                "--target", target,
                "pymysql",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)

            if proc.returncode != 0:
                raise ImportError(
                    "No MySQL driver found, and automatic install failed.\n"
                    f"python: {sys.executable}\n"
                    f"cmd: {' '.join(cmd)}\n"
                    f"stdout:\n{proc.stdout}\n"
                    f"stderr:\n{proc.stderr}"
                ) from first

            pymysql = importlib.import_module("pymysql")
            DictCursor = importlib.import_module("pymysql.cursors").DictCursor
            return pymysql, DictCursor

    def _get_connection(self):
        pymysql, DictCursor = self._ensure_pymysql()

        if not self.host or not self.username:
            raise ValueError("Direct MySQL mode requires host and username.")

        if self.use_iam_auth:
            rds = self._get_boto3_client("rds")
            password = rds.generate_db_auth_token(
                DBHostname=self.host,
                Port=int(self.port or 3306),
                DBUsername=self.username,
                Region=self.region_name,
            )
        else:
            pw = _unwrap_secret(self.password)
            if not pw:
                raise ValueError("Password is required when IAM Authentication is disabled (direct MySQL mode).")
            password = pw

        return pymysql.connect(
            host=self.host,
            port=int(self.port or 3306),
            database=self.database,
            user=self.username,
            password=password,
            connect_timeout=int(self.connect_timeout or 10),
            ssl={"ssl": True},
            cursorclass=DictCursor,
        )

    # ---------- Main execution ----------

    def run_model(self) -> Message:
        debug = self._aws_preflight() if self.debug_mode else None

        if self.debug_only:
            self.status = "Debug-only preflight returned"
            return Message(
                text=json.dumps({"debug": debug}, indent=2, default=str),
                data={"debug": debug}
            )

        try:
            if self.use_data_api:
                results, columns = self._data_api_execute()
            else:
                params = self._extract_params(self.query_params) if hasattr(self, "query_params") else ()
                if isinstance(params, dict):
                    raise ValueError(
                        "Direct MySQL mode expects positional params. "
                        "Use query_params as Data({'params': [...]}) or enable Data API mode for named params."
                    )

                connection = None
                try:
                    connection = self._get_connection()
                    with connection.cursor() as cursor:
                        cursor.execute(self.query, params if params else None)
                        columns = [desc[0] for desc in cursor.description] if cursor.description else []

                        if self.return_single:
                            row = cursor.fetchone()
                            results = [] if row is None else [row]
                        else:
                            if self.limit and int(self.limit) > 0:
                                results = list(cursor.fetchmany(int(self.limit)))
                            else:
                                results = list(cursor.fetchall())
                finally:
                    if connection:
                        connection.close()

            if self.return_single:
                results = results[:1]
            if self.limit and int(self.limit) > 0:
                results = results[: int(self.limit)]

            payload: Dict[str, Any] = {"results": results, "row_count": len(results)}
            if self.include_metadata:
                payload["metadata"] = {
                    "columns": columns,
                    "query": str(self.query),
                    "database": self.database,
                    "mode": "data_api" if self.use_data_api else ("iam_mysql" if self.use_iam_auth else "password_mysql"),
                    "host": self.host,
                    "port": self.port,
                    "region_name": self.region_name,
                }

            if self.debug_mode:
                payload["debug"] = debug

            self.status = f"Retrieved {len(results)} rows"

            # Build text with actual data for Message
            if len(results) == 0:
                text = "Query returned no results."
            else:
                text = json.dumps(results, indent=2, default=str)

            return Message(text=text, data=payload)

        except Exception as e:
            if self.soft_fail:
                self.status = f"Error: {e}"
                out = {"error": str(e)}
                if self.debug_mode:
                    out["debug"] = debug
                return Message(text=f"Error: {e}", data=out)
            raise

    async def _get_tools(self):
        tool = self.build_tool()
        if tool and not tool.tags:
            tool.tags = [tool.name]
        return [tool] if tool else []

    def build_tool(self) -> Tool:
        class AuroraMySQLQueryInput(BaseModel):
            query: str = Field(description="SQL query to execute.")
            params: str = Field(
                default="",
                description=(
                    "Parameters.\n"
                    "- Direct MySQL mode: comma-separated positional values.\n"
                    "- Data API mode: key=value pairs (named), e.g. 'candidate_id=123'."
                ),
            )
            debug_only: bool = Field(
                default=False,
                description="If true, returns AWS preflight debug info without executing SQL.",
            )

        def _execute_query(query: str, params: str = "", debug_only: bool = False) -> str:
            self.query = query
            self.debug_only = bool(debug_only)

            p = (params or "").strip()
            if not p:
                self.query_params = None
            else:
                if "=" in p:
                    d = {}
                    for part in p.split(","):
                        part = part.strip()
                        if not part or "=" not in part:
                            continue
                        k, v = part.split("=", 1)
                        d[k.strip()] = v.strip()
                    self.query_params = Data(data=d) if d else None
                else:
                    plist = [x.strip() for x in p.split(",") if x.strip() != ""]
                    self.query_params = Data(data={"params": plist}) if plist else None

            result = self.run_model()

            # Extract text from Message
            if hasattr(result, "text"):
                return result.text

            # Fallback for data extraction
            data = result.data if hasattr(result, "data") else result

            if "error" in data:
                return f"ERROR: {data['error']}\n\nDEBUG:\n{data.get('debug')}"

            if self.debug_only:
                return f"DEBUG:\n{data.get('debug')}"

            results = data.get("results", [])
            row_count = data.get("row_count", 0)
            if row_count == 0:
                return "Query returned no results."

            lines = [f"Query returned {row_count} rows:"]
            for i, row in enumerate(results[:10], 1):
                if isinstance(row, dict):
                    row_str = ", ".join(f"{k}={v}" for k, v in row.items())
                else:
                    row_str = str(row)
                lines.append(f"  {i}. {row_str}")

            if row_count > 10:
                lines.append(f"  ... and {row_count - 10} more rows")

            return "\n".join(lines)

        tool = StructuredTool.from_function(
            name="aurora_mysql_retrieve",
            description="Execute SQL queries on Aurora MySQL (direct connection or Data API) with built-in debug preflight.",
            args_schema=AuroraMySQLQueryInput,
            func=_execute_query,
            return_direct=False,
            tags=["aurora_mysql_retrieve"],
        )
        self.status = "Tool created"
        return tool
