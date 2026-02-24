from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from jose import jwt, JWTError
from .config import get_settings

settings = get_settings()
security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify bearer token and return auth payload."""
    token = credentials.credentials

    # Support JWT tokens if the auth server is configured to issue them.
    try:
        payload = jwt.decode(
            token,
            settings.better_auth_secret,
            algorithms=["HS256"],
        )
        return payload
    except JWTError:
        pass

    # Default Better Auth sessions use opaque tokens, not JWTs.
    # Validate them via the auth server using the bearer plugin.
    auth_url = settings.better_auth_url.rstrip("/") + "/api/auth/get-session"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                auth_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth server validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        data = response.json()
    except ValueError:
        data = None

    if not data or not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = data.get("user") or {}
    session = data.get("session") or {}
    user_id = user.get("id") or session.get("userId")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Normalize to the shape expected by get_current_user_id().
    return {"id": str(user_id), "user": user, "session": session}


async def get_current_user_id(token_data: dict = Depends(verify_token)) -> str:
    """Extract user ID from verified token."""
    user_id = token_data.get("sub") or token_data.get("userId") or token_data.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
        )
    return str(user_id)
