"""
Updated Services Router with proper OAuth 2.0 implementation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime, timedelta
import secrets
import urllib.parse
import httpx

from open_webui.utils.auth import get_verified_user
from open_webui.utils.oauth_services import get_service_config, get_configured_services, ServiceType, reload_oauth_configs
from open_webui.services.oauth_token_manager import token_manager, TokenData

router = APIRouter()

# In-memory state storage for OAuth flows (in production, use Redis or similar)
oauth_states = {}


class ServiceStatus(BaseModel):
    authorized: bool
    email: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[str] = None


class AuthResponse(BaseModel):
    auth_url: str
    state: str


@router.get("/status")
async def get_services_status(user=Depends(get_verified_user)):
    """Get the authorization status of all services for the current user"""
    user_services = token_manager.get_user_services(user.id)

    statuses = {}
    for service_id in [ServiceType.GOOGLE_DRIVE, ServiceType.ZOHO, ServiceType.JIRA, ServiceType.HUBSPOT]:
        if service_id in user_services:
            token_data = user_services[service_id]
            statuses[service_id] = ServiceStatus(
                authorized=True,
                email=token_data.user_email or f"{service_id}_user@example.com",
                expires_at=token_data.expires_at,
                scopes=token_data.scope
            )
        else:
            statuses[service_id] = ServiceStatus(authorized=False)

    return statuses


@router.get("/{service_id}/auth")
async def initiate_service_auth(service_id: str, request: Request, user=Depends(get_verified_user)):
    """Initiate OAuth 2.0 authentication for a service"""
    config = get_service_config(service_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )

    if not config.is_configured():
        # Get the appropriate environment variable names for the service
        env_var_names = {
            "google_drive": "GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET",
            "zoho": "ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET",
            "onedrive": "ONEDRIVE_CLIENT_ID and ONEDRIVE_CLIENT_SECRET"
        }
        env_vars = env_var_names.get(service_id, f"{service_id.upper()}_CLIENT_ID and {service_id.upper()}_CLIENT_SECRET")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {service_id} is not configured. Please set environment variables {env_vars}."
        )

    # Generate secure state parameter
    state = secrets.token_urlsafe(32)

    # Store state with user info for validation
    oauth_states[state] = {
        "user_id": user.id,
        "service_id": service_id,
        "timestamp": datetime.utcnow().timestamp()
    }

    # Build redirect URI
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/v1/services/{service_id}/callback"

    # Build authorization URL
    auth_params = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "access_type": "offline",  # For refresh tokens
        "prompt": "consent"  # Force consent to get refresh token
    }

    # Service-specific parameters
    if service_id == ServiceType.GOOGLE_DRIVE:
        auth_params["include_granted_scopes"] = "true"
        auth_params["scope"] = config.get_scope_string()  # Space-separated for Google
    elif service_id == ServiceType.ZOHO:
        # Zoho requires comma-separated scopes and access_type=offline for refresh tokens
        auth_params["scope"] = config.get_scope_string_comma_separated()
        auth_params["access_type"] = "offline"
    else:
        # Default to space-separated scopes for other services
        auth_params["scope"] = config.get_scope_string()

    auth_url = f"{config.auth_url}?{urllib.parse.urlencode(auth_params)}"

    return AuthResponse(auth_url=auth_url, state=state)


@router.get("/{service_id}/callback")
async def service_auth_callback(
    service_id: str,
    code: str,
    state: str,
    request: Request,
    error: Optional[str] = None
):
    """Handle OAuth callback and save tokens"""
    # Check for OAuth errors
    if error:
        return HTMLResponse(f"""
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #d32f2f;">Authorization Error</h1>
                    <p>Error: {error}</p>
                    <p>You can close this window and try again.</p>
                    <script>
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
            </html>
        """)

    # Validate state parameter
    if state not in oauth_states:
        return HTMLResponse("""
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #d32f2f;">Invalid State</h1>
                    <p>OAuth state validation failed. Please try again.</p>
                    <script>
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
            </html>
        """)

    state_data = oauth_states[state]
    user_id = state_data["user_id"]
    stored_service_id = state_data["service_id"]

    # Validate service ID matches
    if service_id != stored_service_id:
        return HTMLResponse("""
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #d32f2f;">Service Mismatch</h1>
                    <p>Service ID validation failed. Please try again.</p>
                    <script>
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
            </html>
        """)

    # Clean up state
    del oauth_states[state]

    config = get_service_config(service_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )

    # Build redirect URI
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/v1/services/{service_id}/callback"

    try:
        # Exchange authorization code for tokens
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": config.client_id,
            "client_secret": config.client_secret
        }

        # For Zoho, add scope to token exchange request
        if service_id == "zoho" and config.scopes:
            token_data["scope"] = " ".join(config.scopes)

        print(f"Token exchange request for {service_id}:")
        print(f"  URL: {config.token_url}")
        print(f"  redirect_uri: {redirect_uri}")
        print(f"  client_id: {config.client_id}")
        print(f"  code: {code[:10]}...{code[-10:] if len(code) > 20 else code}")

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                config.token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )

            if token_response.status_code != 200:
                print(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
                return HTMLResponse(f"""
                    <html>
                        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                            <h1 style="color: #d32f2f;">Token Exchange Failed</h1>
                            <p>Failed to exchange authorization code for tokens.</p>
                            <p>Status: {token_response.status_code}</p>
                            <script>
                                setTimeout(() => window.close(), 5000);
                            </script>
                        </body>
                    </html>
                """)

            token_data_raw = token_response.json()
            print(f"Token response data: {token_data_raw}")

            # Check if access_token is present
            if "access_token" not in token_data_raw:
                error_description = token_data_raw.get("error_description", "Unknown error")
                error_code = token_data_raw.get("error", "token_error")
                print(f"Token response missing access_token: {token_data_raw}")
                return HTMLResponse(f"""
                    <html>
                        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                            <h1 style="color: #d32f2f;">Authorization Error</h1>
                            <p>An error occurred during authorization: '{error_code}'</p>
                            <p>Description: {error_description}</p>
                            <p>You can close this window and try again.</p>
                            <script>
                                // Send error message to parent window
                                try {{
                                    if (window.opener && !window.opener.closed) {{
                                        window.opener.postMessage({{
                                            type: 'oauth_error',
                                            service_id: '{service_id}',
                                            error: '{error_code}',
                                            description: '{error_description}'
                                        }}, window.opener.origin);
                                    }}
                                }} catch (e) {{
                                    console.error('Failed to send message to parent:', e);
                                }}

                                // Close window immediately
                                setTimeout(() => {{
                                    try {{
                                        window.close();
                                    }} catch (e) {{
                                        console.error('Failed to close window:', e);
                                    }}
                                }}, 1000);
                            </script>
                        </body>
                    </html>
                """)

        # Get user info if available (skip for Zoho as it has different auth format)
        user_email = None
        user_name = None

        if config.userinfo_url and token_data_raw.get("access_token") and service_id != ServiceType.ZOHO:
            try:
                async with httpx.AsyncClient() as client:
                    userinfo_response = await client.get(
                        config.userinfo_url,
                        headers={
                            "Authorization": f"Bearer {token_data_raw['access_token']}"
                        },
                        timeout=30.0
                    )
                    if userinfo_response.status_code == 200:
                        user_info = userinfo_response.json()
                        user_email = user_info.get("email")
                        user_name = user_info.get("name") or user_info.get("given_name", "")
            except Exception as e:
                print(f"Failed to get user info: {e}")
        elif service_id == ServiceType.ZOHO:
            # Try to get user info from Zoho
            print("\n" + "="*60)
            print("ZOHO USER INFO RETRIEVAL DEBUG")
            print("="*60)

            try:
                print(f"1. Access token received: {token_data_raw.get('access_token', 'NO TOKEN')[:20]}...")
                print(f"2. Token scope: {token_data_raw.get('scope', 'NO SCOPE')}")

                userinfo_headers = {"Authorization": f"Bearer {token_data_raw['access_token']}"}

                # Get the correct Zoho datacenter URL from config
                zoho_config = get_service_config(ServiceType.ZOHO)
                userinfo_url = zoho_config.userinfo_url or "https://accounts.zoho.eu/oauth/user/info"

                print(f"3. Using userinfo URL: {userinfo_url}")
                print(f"4. Request headers: {userinfo_headers}")

                # Use httpx for the request (already imported)
                with httpx.Client() as client:
                    userinfo_response = client.get(
                        userinfo_url,
                        headers=userinfo_headers,
                        timeout=10
                    )

                print(f"5. Response status: {userinfo_response.status_code}")
                print(f"6. Response headers: {dict(userinfo_response.headers)}")
                print(f"7. Response body: {userinfo_response.text}")

                if userinfo_response.status_code == 200:
                    user_info = userinfo_response.json()
                    print(f"8. Parsed JSON response: {user_info}")
                    print(f"9. Available keys in response: {list(user_info.keys())}")

                    # Try all possible field names for email
                    email_fields = ["Email", "EMAIL", "email", "USEREMAIL", "user_email",
                                   "UserEmail", "emailAddress", "EmailAddress", "mail", "Mail"]
                    user_email = None

                    for field in email_fields:
                        if field in user_info:
                            user_email = user_info[field]
                            print(f"10. Found email in field '{field}': {user_email}")
                            break

                    if not user_email:
                        print(f"11. No email found in any of the fields: {email_fields}")
                        user_email = "zoho_user@example.com"

                    # Try all possible field names for name
                    name_fields = ["Display_Name", "DISPLAY_NAME", "display_name", "DisplayName",
                                  "First_Name", "FIRST_NAME", "first_name", "FirstName",
                                  "name", "Name", "NAME", "full_name", "FullName", "fullName"]
                    user_name = None

                    for field in name_fields:
                        if field in user_info:
                            user_name = user_info[field]
                            print(f"12. Found name in field '{field}': {user_name}")
                            break

                    if not user_name:
                        print(f"13. No name found in any of the fields: {name_fields}")
                        user_name = "Zoho User"

                    print(f"14. Final extracted - Email: {user_email}, Name: {user_name}")
                else:
                    # Fallback to placeholder
                    print(f"ERROR: Failed to get Zoho user info - Status: {userinfo_response.status_code}")
                    print(f"ERROR: Response body: {userinfo_response.text}")
                    user_email = "zoho_user@example.com"
                    user_name = "Zoho User"

            except Exception as e:
                print(f"EXCEPTION: Failed to get Zoho user info: {e}")
                import traceback
                traceback.print_exc()
                user_email = "zoho_user@example.com"
                user_name = "Zoho User"

            print("="*60)
            print("END ZOHO DEBUG")
            print("="*60 + "\n")

        # Create token data object
        expires_at = None
        if token_data_raw.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(seconds=int(token_data_raw["expires_in"]))

        token_data = TokenData(
            access_token=token_data_raw["access_token"],
            refresh_token=token_data_raw.get("refresh_token"),
            expires_at=expires_at,
            user_email=user_email,
            user_name=user_name,
            service_id=service_id,
            scope=token_data_raw.get("scope")
        )

        # Store encrypted token data
        token_manager.store_token(user_id, service_id, token_data)

        return HTMLResponse(f"""
            <html>
                <head>
                    <title>Authorization Successful</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            text-align: center;
                            padding: 50px;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            margin: 0;
                        }}
                        .container {{
                            background: rgba(255, 255, 255, 0.1);
                            border-radius: 15px;
                            padding: 40px;
                            max-width: 500px;
                            margin: 0 auto;
                            backdrop-filter: blur(10px);
                        }}
                        .success-icon {{
                            font-size: 64px;
                            color: #4caf50;
                            margin-bottom: 20px;
                        }}
                        h1 {{
                            color: white;
                            margin-bottom: 20px;
                        }}
                        .service-info {{
                            background: rgba(255, 255, 255, 0.2);
                            border-radius: 10px;
                            padding: 20px;
                            margin: 20px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="success-icon">✅</div>
                        <h1>Authorization Successful!</h1>
                        <div class="service-info">
                            <p><strong>Service:</strong> {config.name}</p>
                            {f'<p><strong>Account:</strong> {user_email}</p>' if user_email else ''}
                        </div>
                        <p>You can close this window now. The service has been connected successfully!</p>
                    </div>
                    <script>
                        // Notify parent window and close
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'oauth_success',
                                service_id: '{service_id}',
                                user_email: '{user_email or ''}'
                            }}, '*');
                        }}
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
            </html>
        """)

    except Exception as e:
        print(f"Error during OAuth callback: {e}")
        return HTMLResponse(f"""
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #d32f2f;">Authorization Error</h1>
                    <p>An error occurred during authorization: {str(e)}</p>
                    <p>You can close this window and try again.</p>
                    <script>
                        setTimeout(() => window.close(), 5000);
                    </script>
                </body>
            </html>
        """)


@router.post("/{service_id}/disconnect")
async def disconnect_service(service_id: str, user=Depends(get_verified_user)):
    """Disconnect a service by removing its tokens"""
    config = get_service_config(service_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )

    # Get token before deletion for revocation
    token_data = token_manager.get_token(user.id, service_id)

    # Delete from our storage
    deleted = token_manager.delete_token(user.id, service_id)

    # Try to revoke token at the provider
    if token_data and config.revoke_url:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    config.revoke_url,
                    data={"token": token_data.access_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0
                )
        except Exception as e:
            print(f"Failed to revoke token at provider: {e}")
            # Continue anyway - local deletion is more important

    if deleted:
        return {"message": f"Successfully disconnected from {config.name}"}
    else:
        return {"message": f"Service {config.name} was not connected"}


@router.get("/{service_id}/token")
async def get_service_token(service_id: str, user=Depends(get_verified_user)):
    """Get a valid access token for a specific service (for internal use)"""
    config = get_service_config(service_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )

    # Get token and refresh if needed
    access_token = await token_manager.get_valid_token(user.id, service_id)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Service {config.name} is not authorized or token is invalid"
        )

    return {"access_token": access_token, "service": config.name}


@router.get("/configured")
async def get_configured_services_endpoint():
    """Get list of services that have OAuth credentials configured"""
    configured = get_configured_services()

    services_info = {}
    for service_id in configured:
        config = get_service_config(service_id)
        if config:
            services_info[service_id] = {
                "name": config.name,
                "scopes": config.scopes
            }

    return services_info


# Cleanup task - run periodically to remove expired tokens
@router.post("/cleanup")
async def cleanup_expired_tokens():
    """Admin endpoint to cleanup expired tokens"""
    token_manager.cleanup_expired_tokens()
    return {"message": "Cleanup completed"}


@router.post("/reload-config")
async def reload_oauth_config(user=Depends(get_verified_user)):
    """Reload OAuth configuration from external config file"""
    # Note: In production, you might want to restrict this to admin users only
    try:
        reload_oauth_configs()
        return {
            "success": True,
            "message": "OAuth configuration reloaded successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload configuration: {str(e)}"
        )