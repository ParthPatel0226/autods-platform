"""Auth routes — signup / login / me.

Dual-backend:
  - SUPABASE_URL set  → delegate to Supabase Auth (supabase-py)
  - SUPABASE_URL unset → issue internal HS256 JWT (dev / self-hosted mode)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.config import Settings, get_settings
from api.dependencies import get_current_user
from api.schemas.auth import LoginRequest, SignupRequest, TokenResponse, User

logger = logging.getLogger(__name__)

router = APIRouter()


def _settings() -> Settings:
    return get_settings()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue_internal_token(email: str, settings: Settings) -> TokenResponse:
    """Create a plain HS256 JWT for dev / self-hosted mode."""
    from jose import jwt  # type: ignore[import]

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    token = jwt.encode(
        {
            "sub": f"user-{email}",
            "email": email,
            "exp": exp.timestamp(),
            "iat": now.timestamp(),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create account",
)
async def signup(
    body: SignupRequest,
    settings: Annotated[Settings, Depends(_settings)],
) -> TokenResponse:
    """Create a new user account and return an access token."""
    if settings.SUPABASE_URL:
        from supabase import create_client  # type: ignore[import]

        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        try:
            resp = client.auth.sign_up(
                {
                    "email": body.email,
                    "password": body.password,
                    "options": {"data": {"full_name": body.full_name}},
                }
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        if resp.session is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signup failed or email confirmation is required.",
            )
        return TokenResponse(
            access_token=resp.session.access_token,
            expires_in=resp.session.expires_in or settings.JWT_EXPIRE_MINUTES * 60,
        )

    return _issue_internal_token(body.email, settings)


@router.post("/login", response_model=TokenResponse, summary="Log in")
async def login(
    body: LoginRequest,
    settings: Annotated[Settings, Depends(_settings)],
) -> TokenResponse:
    """Authenticate and return an access token."""
    if settings.SUPABASE_URL:
        from supabase import create_client  # type: ignore[import]

        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        try:
            resp = client.auth.sign_in_with_password(
                {"email": body.email, "password": body.password}
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
            ) from exc
        if resp.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials."
            )
        return TokenResponse(
            access_token=resp.session.access_token,
            expires_in=resp.session.expires_in or settings.JWT_EXPIRE_MINUTES * 60,
        )

    # Internal mode — accept any valid email/password (dev only)
    return _issue_internal_token(body.email, settings)


@router.get("/me", response_model=User, summary="Current user")
async def me(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> User:
    """Return the currently authenticated user's identity."""
    return User(
        user_id=current_user["user_id"],
        email=current_user.get("email", ""),
        full_name=current_user.get("full_name", ""),
        created_at=datetime.now(timezone.utc),
    )
