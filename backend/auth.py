"""
Firebase Authentication middleware for FastAPI.

Handles:
- JWT token verification via Firebase Admin SDK
- User context extraction
- Auth dependency injection
"""

from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin.auth as firebase_auth
from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """Authenticated user context."""
    uid: str
    email: Optional[str] = None
    email_verified: bool = False
    display_name: Optional[str] = None
    token: Optional[str] = None  # Raw token for passing to MCP (defense in depth)


# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> AuthenticatedUser:
    """
    Verify Firebase ID token and extract user info.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        AuthenticatedUser with uid, email, etc.

    Raises:
        HTTPException: 401 if token invalid/missing
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # Verify the Firebase ID token
        decoded_token = firebase_auth.verify_id_token(credentials.credentials)

        return AuthenticatedUser(
            uid=decoded_token["uid"],
            email=decoded_token.get("email"),
            email_verified=decoded_token.get("email_verified", False),
            display_name=decoded_token.get("name"),
            token=credentials.credentials  # Include raw token for MCP
        )
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Authentication token has expired"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Optional[AuthenticatedUser]:
    """
    Optional authentication - returns None if no token provided.
    Useful for endpoints that work with or without auth during migration.
    """
    if not credentials:
        return None
    return await get_current_user(credentials)
