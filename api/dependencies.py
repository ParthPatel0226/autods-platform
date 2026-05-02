"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)

_DEV_SECRET = "dev-secret-change-me"


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> dict:
    """Verify Bearer token and return {user_id, email}.

    Priority:
    1. SUPABASE_JWT_SECRET set → verify as Supabase JWT (audience="authenticated")
    2. JWT_SECRET is dev default → accept any token, return dev-user placeholder
    3. Otherwise → verify as our own JWT (HS256)
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    token = credentials.credentials

    # --- Supabase JWT path ---
    if settings.SUPABASE_JWT_SECRET:
        try:
            from jose import JWTError, jwt

            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return {
                "user_id": payload.get("sub"),
                "email": payload.get("email", ""),
            }
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    # --- Dev bypass path ---
    if settings.JWT_SECRET == _DEV_SECRET:
        return {"user_id": "dev-user", "email": "dev@local"}

    # --- Internal JWT path ---
    try:
        from jose import JWTError, jwt

        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email", ""),
        }
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


async def get_db():
    """Return Supabase client, or None if not configured.

    Full impl lives in api/storage/supabase_client.py (Phase 2).
    """
    try:
        from api.storage.supabase_client import get_client  # type: ignore[import]

        return get_client()
    except ImportError:
        return None


async def get_current_project(
    project_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Load project by ID and verify ownership.

    TODO: implement after Phase 3.5 (state_service.load_state).
    """
    # Stub — real implementation wires to api.services.state_service
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="get_current_project not yet implemented (Phase 3.5)",
    )
