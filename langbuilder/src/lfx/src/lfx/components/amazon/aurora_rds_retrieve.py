"""
Aurora RDS Retrieve Component for LangBuilder

Retrieves data from AWS Aurora RDS (MySQL or PostgreSQL compatible) for
session resumption, analytics, and data lookups.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

import json

from langflow.custom.custom_component.component import Component
from langflow.io import (
    BoolInput,
    DropdownInput,
    IntInput,
    MessageTextInput,
    Output,
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


class AuroraRDSRetrieveComponent(Component):
    """
    Retrieve data from AWS Aurora RDS database.

    This component fetches data from Aurora RDS by record ID or custom query.
    Supports both PostgreSQL and MySQL compatible Aurora databases.

    **Authentication:**
    - Provide database credentials directly, OR
    - Use AWS Secrets Manager (set secret_arn)

    **Query Modes:**
    - By ID: Fetch a single record by primary key
    - Custom SQL: Execute a custom SELECT query
    """

    display_name = "Aurora RDS Retrieve"
    description = (
        "Retrieve data from AWS Aurora RDS (MySQL/PostgreSQL) by ID or custom query."
    )
    documentation = "https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html"
    icon = "Amazon"
    name = "AuroraRDSRetrieve"

    inputs = [
        # Query mode selection
        DropdownInput(
            name="query_mode",
            display_name="Query Mode",
            info="How to query data: by ID or custom SQL",
            options=["by_id", "custom_sql"],
            value="by_id",
            required=True,
        ),

        # Record ID for by_id mode
        MessageTextInput(
            name="record_id",
            display_name="Record ID",
            info="Primary key value to retrieve (for 'by_id' mode)",
            required=False,
            tool_mode=True,
        ),

        # Custom SQL for custom_sql mode
        StrInput(
            name="custom_sql",
            display_name="Custom SQL",
            info="Custom SELECT query (for 'custom_sql' mode). Use %s for parameters.",
            placeholder="SELECT * FROM users WHERE status = %s",
            required=False,
        ),

        # SQL parameters
        StrInput(
            name="sql_params",
            display_name="SQL Parameters (JSON)",
            info="JSON array of parameters for custom SQL, e.g. [\"active\", 100]",
            value="[]",
            required=False,
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
            info="Table to query (for 'by_id' mode)",
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
            info="Database password. Leave empty if using Secrets Manager.",
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
            info="AWS region (for Secrets Manager)",
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

        # Result limit
        IntInput(
            name="limit",
            display_name="Result Limit",
            info="Maximum number of records to return (0 = no limit)",
            value=100,
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="records",
            display_name="Records",
            method="retrieve_data",
        ),
    ]

    def _get_credentials(self) -> dict[str, str]:
        """
        Get database credentials from configured source.

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
                import psycopg2.extras
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
                "cursorclass": pymysql.cursors.DictCursor,
            }

            if self.use_ssl:
                connect_kwargs["ssl"] = {"ssl": True}

            self.log(f"Connecting to MySQL: {self.host}:{self.port}/{self.database}")
            return pymysql.connect(**connect_kwargs)

        else:
            raise ValueError(f"Unsupported database engine: {self.db_engine}")

    def retrieve_data(self) -> Data:
        """
        Retrieve data from Aurora RDS.

        Returns:
            Data object with query results
        """
        # Connect to database
        try:
            conn = self._get_connection()
        except Exception as e:
            self.status = f"Connection failed: {e}"
            return Data(data={
                "found": False,
                "error": str(e),
                "records": [],
                "count": 0,
            })

        try:
            if self.db_engine == "postgresql":
                import psycopg2.extras
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            if self.query_mode == "by_id":
                # Query by primary key
                record_id = self.record_id
                if hasattr(record_id, "text"):
                    record_id = record_id.text
                record_id = str(record_id).strip() if record_id else ""

                if not record_id:
                    self.status = "No record ID provided"
                    return Data(data={
                        "found": False,
                        "error": "No record ID provided",
                        "records": [],
                        "count": 0,
                    })

                self.log(f"Retrieving record {record_id} from {self.table_name}")

                sql = f"SELECT * FROM {self.table_name} WHERE id = %s"
                cursor.execute(sql, (record_id,))

            else:  # custom_sql mode
                if not self.custom_sql:
                    self.status = "No custom SQL provided"
                    return Data(data={
                        "found": False,
                        "error": "No custom SQL provided",
                        "records": [],
                        "count": 0,
                    })

                # Parse SQL parameters
                params = []
                if self.sql_params:
                    try:
                        params = json.loads(self.sql_params)
                        if not isinstance(params, list):
                            params = [params]
                    except json.JSONDecodeError:
                        self.log(f"Warning: Could not parse sql_params: {self.sql_params}")

                self.log(f"Executing custom SQL: {self.custom_sql[:100]}...")
                cursor.execute(self.custom_sql, params if params else None)

            # Fetch results
            if self.limit and self.limit > 0:
                rows = cursor.fetchmany(self.limit)
            else:
                rows = cursor.fetchall()

            # Get column names BEFORE closing cursor (needed for tuple rows)
            column_names = [desc[0] for desc in cursor.description] if cursor.description else []

            # Convert rows to list of dicts BEFORE closing cursor
            records = []
            for row in rows:
                if isinstance(row, dict):
                    record = dict(row)
                else:
                    # Use pre-fetched column names for tuple rows
                    record = dict(zip(column_names, row))

                # Parse JSON columns if present (for json_column storage mode)
                if "data" in record and isinstance(record["data"], str):
                    try:
                        record["data"] = json.loads(record["data"])
                    except json.JSONDecodeError:
                        pass

                records.append(record)

            cursor.close()
            conn.close()

            found = len(records) > 0

            if self.query_mode == "by_id":
                self.status = f"Found record {self.record_id}" if found else f"Record {self.record_id} not found"
            else:
                self.status = f"Found {len(records)} records"

            self.log(f"Query returned {len(records)} records")

            return Data(data={
                "found": found,
                "records": records,
                "count": len(records),
                "table": self.table_name,
                "error": None,
            })

        except Exception as e:
            self.status = f"Query error: {e}"
            self.log(f"Retrieve error: {e}")
            try:
                conn.close()
            except:
                pass
            return Data(data={
                "found": False,
                "error": str(e),
                "records": [],
                "count": 0,
            })
