"""
Aurora RDS Store Component for LangBuilder

Stores data to AWS Aurora RDS (MySQL or PostgreSQL compatible) for persistence,
analytics, and session management capabilities.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

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


# AWS region options for dropdown
AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-north-1", "ap-south-1", "ap-northeast-1",
    "ap-northeast-2", "ap-northeast-3", "ap-southeast-1",
    "ap-southeast-2", "sa-east-1"
]

# Database engine options
DB_ENGINES = ["mysql", "postgresql"]


class AuroraRDSStoreComponent(LCToolComponent):
    """
    Store data to AWS Aurora RDS database.

    This component saves structured data to Aurora RDS (MySQL or PostgreSQL).
    It accepts Data input from upstream components and dynamically stores
    all fields to the specified table.

    **Authentication:**
    - Provide database credentials directly, OR
    - Use AWS Secrets Manager (set secret_arn), OR
    - Use IAM database authentication (requires IAM role)

    **Usage as Flow Component:**
    - Connect Data from upstream component
    - Configure database connection
    - Data is inserted/upserted to specified table

    **Usage as Agent Tool:**
    - Connect 'Tool' output to Agent's 'tools' input
    - Agent can store conversation state and metadata
    """

    display_name = "Aurora RDS Store"
    description = (
        "Store data to AWS Aurora RDS (MySQL/PostgreSQL). "
        "Accepts Data from upstream components for flexible storage."
    )
    documentation = "https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html"
    icon = "Amazon"
    name = "AuroraRDSStore"

    inputs = [
        # Data input from upstream component
        DataInput(
            name="structured_data",
            display_name="Structured Data",
            info="Data to store in the database. All fields will be stored as JSON or individual columns.",
            required=True,
            tool_mode=True,
        ),

        # Primary key for upsert operations
        MessageTextInput(
            name="record_id",
            display_name="Record ID",
            info="Primary key value. Auto-generates UUID if empty.",
            required=False,
            tool_mode=True,
        ),

        # Database engine selection
        DropdownInput(
            name="db_engine",
            display_name="Database Engine",
            info="Aurora database engine type",
            options=DB_ENGINES,
            value="postgresql",
            required=True,
        ),

        # Connection configuration
        StrInput(
            name="host",
            display_name="Host",
            info="Aurora cluster endpoint (e.g., mydb.cluster-xxxxx.us-east-1.rds.amazonaws.com)",
            placeholder="mydb.cluster-xxxxx.us-east-1.rds.amazonaws.com",
            required=True,
        ),

        IntInput(
            name="port",
            display_name="Port",
            info="Database port (default: 5432 for PostgreSQL, 3306 for MySQL)",
            value=5432,
            required=True,
        ),

        StrInput(
            name="database",
            display_name="Database Name",
            info="Name of the database to connect to",
            placeholder="myappdb",
            required=True,
        ),

        StrInput(
            name="table_name",
            display_name="Table Name",
            info="Table to store data in",
            value="langbuilder_records",
            required=True,
        ),

        # Credentials (no default values per best practices)
        SecretStrInput(
            name="username",
            display_name="Username",
            info="Database username",
            required=False,
        ),

        SecretStrInput(
            name="password",
            display_name="Password",
            info="Database password. Leave empty if using IAM auth or Secrets Manager.",
            required=False,
        ),

        # AWS Secrets Manager integration
        StrInput(
            name="secret_arn",
            display_name="Secrets Manager ARN",
            info="ARN of AWS Secrets Manager secret containing credentials (optional)",
            required=False,
            advanced=True,
        ),

        DropdownInput(
            name="region_name",
            display_name="AWS Region",
            info="AWS region (for Secrets Manager and IAM auth)",
            options=AWS_REGIONS,
            value="us-east-1",
            required=False,
            advanced=True,
        ),

        # SSL configuration
        BoolInput(
            name="use_ssl",
            display_name="Use SSL",
            info="Enable SSL/TLS connection (recommended for production)",
            value=True,
            advanced=True,
        ),

        # Storage mode
        DropdownInput(
            name="storage_mode",
            display_name="Storage Mode",
            info="How to store data: 'json_column' stores all data as JSON, 'dynamic_columns' creates columns per field",
            options=["json_column", "dynamic_columns"],
            value="json_column",
            advanced=True,
        ),

        # Upsert configuration
        BoolInput(
            name="upsert",
            display_name="Upsert Mode",
            info="Update existing record if ID exists, otherwise insert",
            value=True,
            advanced=True,
        ),

        # Auto-create table option
        BoolInput(
            name="auto_create_table",
            display_name="Auto Create Table",
            info="Automatically create the table if it doesn't exist",
            value=True,
            advanced=True,
        ),
    ]

    # Uses default LCToolComponent outputs (api_run_model + component_as_tool)

    def _get_credentials(self) -> dict[str, str]:
        """
        Get database credentials from configured source.

        Priority:
        1. AWS Secrets Manager (if secret_arn provided)
        2. Direct credentials (username/password)

        Returns:
            dict with 'username' and 'password' keys
        """
        # Try Secrets Manager first
        if self.secret_arn:
            try:
                import boto3
            except ImportError as e:
                msg = "boto3 is required for Secrets Manager. Install with: pip install boto3"
                raise ImportError(msg) from e

            self.log("Fetching credentials from Secrets Manager")
            client = boto3.client("secretsmanager", region_name=self.region_name)
            response = client.get_secret_value(SecretId=self.secret_arn)

            secret = json.loads(response["SecretString"])
            return {
                "username": secret.get("username", ""),
                "password": secret.get("password", ""),
            }

        # Use direct credentials
        username = self.username
        if hasattr(username, "get_secret_value"):
            username = username.get_secret_value()

        password = self.password
        if hasattr(password, "get_secret_value"):
            password = password.get_secret_value()

        return {
            "username": username or "",
            "password": password or "",
        }

    def _get_connection(self):
        """
        Create database connection based on engine type.

        Returns:
            Database connection object
        """
        creds = self._get_credentials()

        if self.db_engine == "postgresql":
            try:
                import psycopg2
            except ImportError as e:
                msg = "psycopg2 is not installed. Install with: pip install psycopg2-binary"
                raise ImportError(msg) from e

            connect_kwargs = {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": creds["username"],
                "password": creds["password"],
            }

            if self.use_ssl:
                connect_kwargs["sslmode"] = "require"

            self.log(f"Connecting to PostgreSQL: {self.host}:{self.port}/{self.database}")
            return psycopg2.connect(**connect_kwargs)

        elif self.db_engine == "mysql":
            try:
                import pymysql
            except ImportError as e:
                msg = "pymysql is not installed. Install with: pip install pymysql"
                raise ImportError(msg) from e

            connect_kwargs = {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": creds["username"],
                "password": creds["password"],
            }

            if self.use_ssl:
                connect_kwargs["ssl"] = {"ssl": True}

            self.log(f"Connecting to MySQL: {self.host}:{self.port}/{self.database}")
            return pymysql.connect(**connect_kwargs)

        else:
            raise ValueError(f"Unsupported database engine: {self.db_engine}")

    def _ensure_table_exists(self, conn) -> None:
        """
        Create table if it doesn't exist.

        Args:
            conn: Database connection
        """
        cursor = conn.cursor()

        if self.storage_mode == "json_column":
            if self.db_engine == "postgresql":
                create_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id VARCHAR(255) PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            else:  # mysql
                create_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id VARCHAR(255) PRIMARY KEY,
                    data JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """
        else:  # dynamic_columns - create basic structure
            if self.db_engine == "postgresql":
                create_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id VARCHAR(255) PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            else:  # mysql
                create_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id VARCHAR(255) PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """

        cursor.execute(create_sql)
        conn.commit()
        cursor.close()
        self.log(f"Table {self.table_name} ensured to exist")

    def _add_column_if_not_exists(self, conn, column_name: str, value: Any) -> None:
        """
        Add a column to the table if it doesn't exist (for dynamic_columns mode).

        Args:
            conn: Database connection
            column_name: Column name to add
            value: Sample value to determine column type
        """
        cursor = conn.cursor()

        # Determine column type based on value
        if isinstance(value, bool):
            col_type = "BOOLEAN"
        elif isinstance(value, int):
            col_type = "BIGINT"
        elif isinstance(value, float):
            col_type = "DOUBLE PRECISION" if self.db_engine == "postgresql" else "DOUBLE"
        elif isinstance(value, dict) or isinstance(value, list):
            col_type = "JSONB" if self.db_engine == "postgresql" else "JSON"
        else:
            col_type = "TEXT"

        try:
            if self.db_engine == "postgresql":
                cursor.execute(f"""
                    ALTER TABLE {self.table_name}
                    ADD COLUMN IF NOT EXISTS {column_name} {col_type}
                """)
            else:  # mysql
                # MySQL doesn't have IF NOT EXISTS for columns, so check first
                cursor.execute(f"""
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                """, (self.table_name, column_name))
                if cursor.fetchone()[0] == 0:
                    cursor.execute(f"""
                        ALTER TABLE {self.table_name}
                        ADD COLUMN {column_name} {col_type}
                    """)
            conn.commit()
        except Exception as e:
            self.log(f"Warning: Could not add column {column_name}: {e}")
            conn.rollback()
        finally:
            cursor.close()

    def run_model(self) -> Data:
        """
        Store data to Aurora RDS.

        Returns:
            Data object with confirmation and stored record info
        """
        # Extract data from structured_data input
        data = self.structured_data
        if isinstance(data, list):
            data = data[0] if data else {}

        if hasattr(data, "data"):
            output_data = data.data
        elif isinstance(data, dict):
            output_data = data
        else:
            output_data = {}

        if not output_data:
            self.status = "No data to store"
            return Data(data={"stored": False, "error": "No data provided", "id": None})

        # Get or generate record ID
        record_id = self.record_id
        if hasattr(record_id, "text"):
            record_id = record_id.text
        record_id = str(record_id).strip() if record_id else ""

        if not record_id:
            record_id = str(uuid.uuid4())
            self.log(f"Generated record ID: {record_id}")

        # Connect to database
        try:
            conn = self._get_connection()
        except Exception as e:
            self.status = f"Connection failed: {e}"
            return Data(data={"stored": False, "error": str(e), "id": None})

        try:
            # Ensure table exists
            if self.auto_create_table:
                self._ensure_table_exists(conn)

            cursor = conn.cursor()
            now = datetime.utcnow()

            if self.storage_mode == "json_column":
                # Store all data as JSON
                data_json = json.dumps(output_data)

                if self.upsert:
                    if self.db_engine == "postgresql":
                        sql = f"""
                        INSERT INTO {self.table_name} (id, data, created_at, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            data = EXCLUDED.data,
                            updated_at = EXCLUDED.updated_at
                        """
                    else:  # mysql
                        sql = f"""
                        INSERT INTO {self.table_name} (id, data, created_at, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            data = VALUES(data),
                            updated_at = VALUES(updated_at)
                        """
                    cursor.execute(sql, (record_id, data_json, now, now))
                else:
                    sql = f"""
                    INSERT INTO {self.table_name} (id, data, created_at, updated_at)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(sql, (record_id, data_json, now, now))

            else:  # dynamic_columns mode
                # Add columns for each field
                for key, value in output_data.items():
                    if key not in ["id", "created_at", "updated_at"]:
                        self._add_column_if_not_exists(conn, key, value)

                # Build dynamic INSERT/UPDATE
                columns = ["id", "created_at", "updated_at"]
                values = [record_id, now, now]

                for key, value in output_data.items():
                    if key not in columns:
                        columns.append(key)
                        # Serialize complex types
                        if isinstance(value, (dict, list)):
                            values.append(json.dumps(value))
                        else:
                            values.append(value)

                placeholders = ", ".join(["%s"] * len(values))
                columns_str = ", ".join(columns)

                if self.upsert:
                    if self.db_engine == "postgresql":
                        update_cols = ", ".join([
                            f"{col} = EXCLUDED.{col}"
                            for col in columns if col not in ["id", "created_at"]
                        ])
                        sql = f"""
                        INSERT INTO {self.table_name} ({columns_str})
                        VALUES ({placeholders})
                        ON CONFLICT (id) DO UPDATE SET {update_cols}
                        """
                    else:  # mysql
                        update_cols = ", ".join([
                            f"{col} = VALUES({col})"
                            for col in columns if col not in ["id", "created_at"]
                        ])
                        sql = f"""
                        INSERT INTO {self.table_name} ({columns_str})
                        VALUES ({placeholders})
                        ON DUPLICATE KEY UPDATE {update_cols}
                        """
                    cursor.execute(sql, values)
                else:
                    sql = f"""
                    INSERT INTO {self.table_name} ({columns_str})
                    VALUES ({placeholders})
                    """
                    cursor.execute(sql, values)

            conn.commit()
            cursor.close()
            conn.close()

            self.status = f"Stored record {record_id}"
            self.log(f"Record {record_id} stored to {self.table_name}")

            return Data(data={
                "stored": True,
                "id": record_id,
                "table": self.table_name,
                "fields": list(output_data.keys()),
                "timestamp": now.isoformat(),
                "error": None,
            })

        except Exception as e:
            self.status = f"Error: {e}"
            self.log(f"Store error: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return Data(data={"stored": False, "error": str(e), "id": record_id})

    async def _get_tools(self):
        """Override to return the named tool from build_tool() instead of generic outputs."""
        tool = self.build_tool()
        if tool and not tool.tags:
            tool.tags = [tool.name]
        return [tool] if tool else []

    def build_tool(self) -> Tool:
        """
        Build a LangChain tool for storing data to Aurora RDS.

        Returns:
            StructuredTool: A tool that can be used by an Agent to store data.
        """
        class StoreDataInput(BaseModel):
            data_json: str = Field(
                default="{}",
                description="JSON string of data to store, e.g. '{\"name\": \"John\", \"score\": 95}'"
            )
            record_id: str = Field(
                default="",
                description="Optional record ID. Leave empty to auto-generate UUID."
            )

        def _store_data(data_json: str = "{}", record_id: str = "") -> str:
            """Tool function that stores data to Aurora RDS."""
            # Parse JSON data
            try:
                data_dict = json.loads(data_json) if data_json else {}
            except json.JSONDecodeError:
                return f"Error: Invalid JSON data: {data_json}"

            # Set component attributes
            self.structured_data = Data(data=data_dict)
            self.record_id = record_id

            # Call run_model to store
            result = self.run_model()
            if hasattr(result, "data"):
                if result.data.get("stored"):
                    return f"Data stored successfully. ID: {result.data.get('id')}, Table: {result.data.get('table')}"
                else:
                    return f"Failed to store data: {result.data.get('error')}"
            return "Data storage completed"

        tool = StructuredTool.from_function(
            name="aurora_rds_store",
            description=(
                "Store data to AWS Aurora RDS database. Pass data as a JSON string. "
                "Use this to persist conversation state, user data, or any structured information. "
                "Optionally provide a record_id for updates, or leave empty to auto-generate."
            ),
            args_schema=StoreDataInput,
            func=_store_data,
            return_direct=False,
            tags=["aurora_rds_store"],
        )

        self.status = "Aurora RDS Store Tool created"
        return tool
