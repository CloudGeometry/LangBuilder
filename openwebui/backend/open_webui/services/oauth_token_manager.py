"""
OAuth Token Management Module
Handles secure storage, retrieval, and refresh of OAuth tokens
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
import base64
import hashlib

from open_webui.config import DATA_DIR
from open_webui.utils.oauth_services import get_service_config, OAuthConfig
import httpx


class TokenData:
    """Token data structure"""

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        service_id: str = "",
        scope: Optional[str] = None
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at
        self.user_email = user_email
        self.user_name = user_name
        self.service_id = service_id
        self.scope = scope

    def is_expired(self) -> bool:
        """Check if the access token is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

    def expires_soon(self, minutes: int = 5) -> bool:
        """Check if token expires within specified minutes"""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= (self.expires_at - timedelta(minutes=minutes))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "service_id": self.service_id,
            "scope": self.scope
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenData":
        """Create TokenData from dictionary"""
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])

        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            user_email=data.get("user_email"),
            user_name=data.get("user_name"),
            service_id=data.get("service_id", ""),
            scope=data.get("scope")
        )


class OAuthTokenManager:
    """Manages OAuth tokens with encryption and database storage"""

    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, "oauth_tokens.db")
        self._ensure_database()
        self._encryption_key = self._get_or_create_encryption_key()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for token storage"""
        key_file = os.path.join(DATA_DIR, ".oauth_key")

        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()

        # Generate new key
        key = Fernet.generate_key()
        os.makedirs(DATA_DIR, exist_ok=True)

        with open(key_file, 'wb') as f:
            f.write(key)

        # Set secure file permissions
        os.chmod(key_file, 0o600)
        return key

    def _ensure_database(self):
        """Create database table if it doesn't exist"""
        os.makedirs(DATA_DIR, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    user_id TEXT,
                    service_id TEXT,
                    encrypted_token_data BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, service_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_service
                ON oauth_tokens(user_id, service_id)
            """)

    def _encrypt_token_data(self, token_data: TokenData) -> bytes:
        """Encrypt token data for secure storage"""
        fernet = Fernet(self._encryption_key)
        data_json = json.dumps(token_data.to_dict())
        return fernet.encrypt(data_json.encode())

    def _decrypt_token_data(self, encrypted_data: bytes) -> TokenData:
        """Decrypt token data from storage"""
        fernet = Fernet(self._encryption_key)
        decrypted_json = fernet.decrypt(encrypted_data).decode()
        data_dict = json.loads(decrypted_json)
        return TokenData.from_dict(data_dict)

    def store_token(self, user_id: str, service_id: str, token_data: TokenData):
        """Store encrypted token data in database"""
        print(f"\n[TOKEN MANAGER] Storing token for user {user_id}, service {service_id}")
        print(f"[TOKEN MANAGER] Token data to store:")
        print(f"  - Email: {token_data.user_email}")
        print(f"  - Name: {token_data.user_name}")
        print(f"  - Scope: {token_data.scope}")
        print(f"  - Expires at: {token_data.expires_at}")

        encrypted_data = self._encrypt_token_data(token_data)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO oauth_tokens
                (user_id, service_id, encrypted_token_data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, service_id, encrypted_data))

        print(f"[TOKEN MANAGER] Token stored successfully\n")

    def get_token(self, user_id: str, service_id: str) -> Optional[TokenData]:
        """Retrieve and decrypt token data from database"""
        print(f"Getting token for user {user_id}, service {service_id}")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT encrypted_token_data FROM oauth_tokens
                WHERE user_id = ? AND service_id = ?
            """, (user_id, service_id))

            row = cursor.fetchone()
            if not row:
                print(f"No token found for user {user_id}, service {service_id}")
                return None

            print(f"Found token for user {user_id}, service {service_id}")

            try:
                return self._decrypt_token_data(row[0])
            except Exception as e:
                print(f"Error decrypting token data: {e}")
                return None

    def delete_token(self, user_id: str, service_id: str) -> bool:
        """Delete token data from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM oauth_tokens
                WHERE user_id = ? AND service_id = ?
            """, (user_id, service_id))
            return cursor.rowcount > 0

    def get_user_services(self, user_id: str) -> Dict[str, TokenData]:
        """Get all services with tokens for a user"""
        services = {}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT service_id, encrypted_token_data FROM oauth_tokens
                WHERE user_id = ?
            """, (user_id,))

            for service_id, encrypted_data in cursor.fetchall():
                try:
                    token_data = self._decrypt_token_data(encrypted_data)
                    services[service_id] = token_data
                except Exception as e:
                    print(f"Error decrypting token for service {service_id}: {e}")

        return services

    async def refresh_token_if_needed(self, user_id: str, service_id: str) -> Optional[TokenData]:
        """Refresh token if it's expired or expires soon"""
        token_data = self.get_token(user_id, service_id)
        if not token_data:
            return None

        if not token_data.expires_soon():
            return token_data

        if not token_data.refresh_token:
            print(f"No refresh token available for {service_id}")
            return token_data

        # Get service config for refresh
        config = get_service_config(service_id)
        if not config:
            print(f"No config found for service {service_id}")
            return token_data

        try:
            # Refresh the token
            new_token_data = await self._refresh_access_token(config, token_data)
            if new_token_data:
                # Store updated token
                self.store_token(user_id, service_id, new_token_data)
                return new_token_data
        except Exception as e:
            print(f"Error refreshing token for {service_id}: {e}")

        return token_data

    async def _refresh_access_token(self, config: OAuthConfig, token_data: TokenData) -> Optional[TokenData]:
        """Refresh access token using refresh token"""
        if not token_data.refresh_token:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.post(
                config.token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token_data.refresh_token,
                    "client_id": config.client_id,
                    "client_secret": config.client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                print(f"Failed to refresh token: {response.status_code} - {response.text}")
                return None

            refresh_response = response.json()

            # Create new token data
            new_token_data = TokenData(
                access_token=refresh_response["access_token"],
                refresh_token=refresh_response.get("refresh_token", token_data.refresh_token),
                expires_at=datetime.utcnow() + timedelta(seconds=refresh_response.get("expires_in", 3600)),
                user_email=token_data.user_email,
                user_name=token_data.user_name,
                service_id=token_data.service_id,
                scope=refresh_response.get("scope", token_data.scope)
            )

            return new_token_data

    async def get_valid_token(self, user_id: str, service_id: str) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        token_data = await self.refresh_token_if_needed(user_id, service_id)
        return token_data.access_token if token_data else None

    def cleanup_expired_tokens(self):
        """Remove tokens that are expired and have no refresh token"""
        services = {}
        to_delete = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT user_id, service_id, encrypted_token_data FROM oauth_tokens
            """)

            for user_id, service_id, encrypted_data in cursor.fetchall():
                try:
                    token_data = self._decrypt_token_data(encrypted_data)
                    if token_data.is_expired() and not token_data.refresh_token:
                        to_delete.append((user_id, service_id))
                except Exception as e:
                    print(f"Error checking token {user_id}:{service_id}: {e}")
                    to_delete.append((user_id, service_id))

            # Delete expired tokens
            for user_id, service_id in to_delete:
                conn.execute("""
                    DELETE FROM oauth_tokens
                    WHERE user_id = ? AND service_id = ?
                """, (user_id, service_id))

        print(f"Cleaned up {len(to_delete)} expired tokens")


# Global instance
token_manager = OAuthTokenManager()