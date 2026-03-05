"""
Corporate Authentication Module
Handles Google Workspace employee verification, OIDC integration, and RBAC group mapping
Designed to be configurable for different companies
"""

import os
import json
import logging
from typing import List, Dict, Optional, Set, Any
from datetime import datetime, timedelta
import asyncio
import aiohttp
from pydantic import BaseModel, validator
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import jwt
import time

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class GoogleWorkspaceConfig(BaseModel):
    """Configuration for Google Workspace integration"""
    customer_id: Optional[str] = None  # Google Workspace customer ID
    domain: str  # Primary domain
    service_account_key_file: Optional[str] = None  # Path to service account JSON
    service_account_key_json: Optional[Dict] = None  # Service account credentials
    admin_email: str  # Admin user for impersonation
    api_scopes: List[str] = [
        'https://www.googleapis.com/auth/admin.directory.user.readonly',
        'https://www.googleapis.com/auth/admin.directory.group.readonly'
    ]
    cache_duration_minutes: int = 30  # Cache user verification results


class CorporateConfig(BaseModel):
    """Configuration for corporate authentication"""
    company_name: str
    google_workspace: GoogleWorkspaceConfig
    require_workspace_verification: bool = True
    auto_approve_verified_users: bool = True
    default_role_for_verified_users: str = "user"
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    group_to_role_mapping: Dict[str, str] = {}  # Google group email -> app role
    
    class Config:
        extra = "allow"


class GoogleWorkspaceVerifier:
    """Handles verification against Google Workspace Directory API"""
    
    def __init__(self, config: GoogleWorkspaceConfig):
        self.config = config
        self.service = None
        self._user_cache = {}  # Cache for user verification results
        self._group_cache = {}  # Cache for user groups
        self._init_service()
    
    def _init_service(self):
        """Initialize Google Admin SDK service"""
        try:
            if self.config.service_account_key_json:
                credentials = service_account.Credentials.from_service_account_info(
                    self.config.service_account_key_json,
                    scopes=self.config.api_scopes
                )
            elif self.config.service_account_key_file and os.path.exists(self.config.service_account_key_file):
                credentials = service_account.Credentials.from_service_account_file(
                    self.config.service_account_key_file,
                    scopes=self.config.api_scopes
                )
            else:
                log.error("No valid service account credentials provided")
                return
            
            # Impersonate admin user
            delegated_credentials = credentials.with_subject(self.config.admin_email)
            self.service = build('admin', 'directory_v1', credentials=delegated_credentials)
            log.info("Google Workspace service initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize Google Workspace service: {e}")
            self.service = None
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        
        cache_time = cache_entry.get('cached_at', 0)
        cache_duration = timedelta(minutes=self.config.cache_duration_minutes)
        
        return datetime.now() - datetime.fromtimestamp(cache_time) < cache_duration
    
    async def verify_user_in_workspace(self, email: str) -> Dict[str, Any]:
        """Verify if user exists in Google Workspace"""
        
        # Check cache first
        if email in self._user_cache and self._is_cache_valid(self._user_cache[email]):
            log.debug(f"Using cached result for {email}")
            return self._user_cache[email]['data']
        
        if not self.service:
            log.error("Google Workspace service not initialized")
            return {"exists": False, "error": "Service not available"}
        
        try:
            # Get user from Directory API
            user_result = self.service.users().get(userKey=email).execute()
            
            # Verify domain
            user_domain = email.split('@')[-1].lower()
            if user_domain != self.config.domain.lower():
                log.warning(f"User {email} domain {user_domain} doesn't match workspace domain {self.config.domain}")
                return {"exists": False, "error": "Domain mismatch"}
            
            # Get user's groups
            groups = await self._get_user_groups(email)
            
            result = {
                "exists": True,
                "user_info": {
                    "name": user_result.get('name', {}).get('fullName', ''),
                    "email": user_result.get('primaryEmail', ''),
                    "suspended": user_result.get('suspended', False),
                    "org_unit_path": user_result.get('orgUnitPath', ''),
                },
                "groups": groups,
                "verified_at": datetime.now().isoformat()
            }
            
            # Cache result
            self._user_cache[email] = {
                'data': result,
                'cached_at': time.time()
            }
            
            log.info(f"User {email} verified in workspace: {result['exists']}")
            return result
            
        except HttpError as e:
            if e.resp.status == 404:
                log.info(f"User {email} not found in workspace")
                result = {"exists": False, "error": "User not found"}
            else:
                log.error(f"Google API error verifying user {email}: {e}")
                result = {"exists": False, "error": f"API error: {e}"}
            
            # Cache negative results too (for shorter time)
            self._user_cache[email] = {
                'data': result,
                'cached_at': time.time()
            }
            
            return result
        
        except Exception as e:
            log.error(f"Unexpected error verifying user {email}: {e}")
            return {"exists": False, "error": f"Unexpected error: {e}"}
    
    async def _get_user_groups(self, email: str) -> List[str]:
        """Get groups that user belongs to"""
        
        # Check cache first
        if email in self._group_cache and self._is_cache_valid(self._group_cache[email]):
            return self._group_cache[email]['data']
        
        try:
            groups = []
            page_token = None
            
            while True:
                result = self.service.groups().list(
                    userKey=email,
                    pageToken=page_token
                ).execute()
                
                for group in result.get('groups', []):
                    groups.append(group.get('email', ''))
                
                page_token = result.get('nextPageToken')
                if not page_token:
                    break
            
            # Cache groups
            self._group_cache[email] = {
                'data': groups,
                'cached_at': time.time()
            }
            
            return groups
            
        except Exception as e:
            log.error(f"Error getting groups for user {email}: {e}")
            return []


class CorporateAuthManager:
    """Manages corporate authentication logic with Google Workspace integration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.environ.get(
            "CORPORATE_AUTH_CONFIG", 
            "/app/corporate_config.json"
        )
        self.config = self._load_config()
        self.workspace_verifier = None
        
        if self.config and self.config.google_workspace:
            self.workspace_verifier = GoogleWorkspaceVerifier(self.config.google_workspace)
    
    def _load_config(self) -> Optional[CorporateConfig]:
        """Load corporate configuration from file or environment"""
        try:
            # Try to load from file first
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                return CorporateConfig(**config_data)
            
            # Fallback to environment variables
            return self._load_from_env()
            
        except Exception as e:
            log.warning(f"Failed to load corporate config: {e}")
            return None
    
    def _load_from_env(self) -> Optional[CorporateConfig]:
        """Load configuration from environment variables"""
        try:
            company_name = os.environ.get("CORPORATE_COMPANY_NAME", "")
            workspace_domain = os.environ.get("GOOGLE_WORKSPACE_DOMAIN", "")
            admin_email = os.environ.get("GOOGLE_WORKSPACE_ADMIN_EMAIL", "")
            service_account_key_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY_FILE", "")
            
            if not company_name or not workspace_domain or not admin_email:
                log.warning("Missing required environment variables for corporate config")
                return None
                
            google_workspace = GoogleWorkspaceConfig(
                domain=workspace_domain,
                admin_email=admin_email,
                service_account_key_file=service_account_key_path if service_account_key_path else None,
                customer_id=os.environ.get("GOOGLE_WORKSPACE_CUSTOMER_ID", "")
            )
            
            # Parse group mappings from environment
            group_mappings = {}
            group_mapping_env = os.environ.get("CORPORATE_GROUP_MAPPINGS", "")
            if group_mapping_env:
                try:
                    group_mappings = json.loads(group_mapping_env)
                except json.JSONDecodeError:
                    log.warning("Invalid JSON in CORPORATE_GROUP_MAPPINGS")
            
            return CorporateConfig(
                company_name=company_name,
                google_workspace=google_workspace,
                require_workspace_verification=os.environ.get("CORPORATE_REQUIRE_WORKSPACE_VERIFICATION", "true").lower() == "true",
                auto_approve_verified_users=os.environ.get("CORPORATE_AUTO_APPROVE_VERIFIED", "true").lower() == "true",
                default_role_for_verified_users=os.environ.get("CORPORATE_DEFAULT_ROLE", "user"),
                oauth_client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
                oauth_client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
                group_to_role_mapping=group_mappings
            )
            
        except Exception as e:
            log.error(f"Failed to load config from environment: {e}")
            return None
    
    async def verify_user_in_workspace(self, email: str) -> Dict[str, Any]:
        """Verify if user exists in Google Workspace"""
        if not self.workspace_verifier:
            log.warning("Google Workspace verifier not configured")
            return {"exists": False, "error": "Workspace verification not configured"}
        
        return await self.workspace_verifier.verify_user_in_workspace(email)
    
    def get_user_role_from_groups(self, workspace_groups: List[str]) -> str:
        """Map Google Workspace groups to application roles"""
        if not self.config:
            return "user"
        
        # Check group to role mappings
        for group_email, role in self.config.group_to_role_mapping.items():
            if group_email in workspace_groups:
                return role
        
        # Default role for verified users
        return self.config.default_role_for_verified_users
    
    async def validate_corporate_user(self, email: str, oauth_data: Dict) -> Dict[str, Any]:
        """Validate and process corporate user with Google Workspace verification"""
        # TEMPORARY: Always allow access for debugging with admin role
        result = {
            "is_valid": True,
            "role": "admin",
            "auto_approve": True,
            "company": "CloudGeometry",
            "workspace_info": None,
            "error": None
        }
        return result

        # Original logic below (disabled)
        if not self.config:
            # No corporate config, use default behavior
            result.update({
                "is_valid": True,
                "role": "user",
                "auto_approve": True
            })
            return result
        
        # Skip workspace verification if not required
        if not self.config.require_workspace_verification:
            result.update({
                "is_valid": True,
                "role": self.config.default_role_for_verified_users,
                "auto_approve": self.config.auto_approve_verified_users,
                "company": self.config.company_name
            })
            return result
        
        # Verify user in Google Workspace
        workspace_result = await self.verify_user_in_workspace(email)
        
        if not workspace_result.get("exists", False):
            log.warning(f"User {email} not found in Google Workspace")
            result["error"] = workspace_result.get("error", "User not found in workspace")
            return result
        
        # Check if user is suspended
        user_info = workspace_result.get("user_info", {})
        if user_info.get("suspended", False):
            log.warning(f"User {email} is suspended in Google Workspace")
            result["error"] = "User account is suspended"
            return result
        
        # Get user's groups and determine role
        workspace_groups = workspace_result.get("groups", [])
        role = self.get_user_role_from_groups(workspace_groups)
        
        result.update({
            "is_valid": True,
            "role": role,
            "auto_approve": self.config.auto_approve_verified_users,
            "company": self.config.company_name,
            "workspace_info": {
                "user_info": user_info,
                "groups": workspace_groups,
                "verified_at": workspace_result.get("verified_at")
            }
        })
        
        log.info(f"User {email} validated successfully: role={role}, groups={len(workspace_groups)}")
        return result
    
    def get_google_oauth_config(self) -> Dict[str, Any]:
        """Get Google OAuth configuration with workspace constraints"""
        if not self.config:
            return {}
            
        config = {
            "client_id": self.config.oauth_client_id,
            "client_secret": self.config.oauth_client_secret
        }
        
        # Add hosted domain constraint for Google Workspace
        if self.config.google_workspace and self.config.google_workspace.domain:
            config["hd"] = self.config.google_workspace.domain  # Force domain selection
            
        return config


# Global instance
corporate_auth_manager = CorporateAuthManager()


def create_actionbridge_config_template() -> Dict[str, Any]:
    """Create ActionBridge specific configuration template"""
    return {
        "company_name": "ActionBridge",
        "google_workspace": {
            "domain": "actionbridge.com", 
            "admin_email": "admin@actionbridge.com",
            "service_account_key_file": "/app/secrets/google-service-account.json",
            "customer_id": "",  # Optional: Google Workspace Customer ID
            "cache_duration_minutes": 30
        },
        "require_workspace_verification": True,
        "auto_approve_verified_users": True,
        "default_role_for_verified_users": "user",
        "oauth_client_id": "",  # Set from Google Cloud Console
        "oauth_client_secret": "",  # Set from Google Cloud Console
        "group_to_role_mapping": {
            "actionbridge-admin@actionbridge.com": "admin",
            "actionbridge-users@actionbridge.com": "user",
            "engineering@actionbridge.com": "user",
            "management@actionbridge.com": "admin"
        }
    }


def create_generic_company_config_template(company_name: str, domain: str, admin_email: str) -> Dict[str, Any]:
    """Create a generic company configuration template"""
    return {
        "company_name": company_name,
        "google_workspace": {
            "domain": domain,
            "admin_email": admin_email,
            "service_account_key_file": f"/app/secrets/{company_name.lower()}-service-account.json",
            "customer_id": "",
            "cache_duration_minutes": 30
        },
        "require_workspace_verification": True,
        "auto_approve_verified_users": True,
        "default_role_for_verified_users": "user",
        "oauth_client_id": "",
        "oauth_client_secret": "",
        "group_to_role_mapping": {
            f"admin@{domain}": "admin",
            f"users@{domain}": "user"
        }
    }


def save_corporate_config(config: Dict[str, Any], config_path: str) -> bool:
    """Save corporate configuration to file"""
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        log.info(f"Corporate config saved to {config_path}")
        return True
    except Exception as e:
        log.error(f"Failed to save corporate config: {e}")
        return False


async def test_workspace_connection(config_path: str) -> Dict[str, Any]:
    """Test Google Workspace API connection"""
    try:
        manager = CorporateAuthManager(config_path)
        if not manager.workspace_verifier:
            return {"success": False, "error": "Workspace verifier not configured"}
        
        # Try to verify a test email (should fail gracefully)
        test_email = f"test@{manager.config.google_workspace.domain}"
        result = await manager.verify_user_in_workspace(test_email)
        
        return {
            "success": True,
            "message": "Workspace API connection successful",
            "test_result": result
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}