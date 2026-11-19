"""Clerk session authentication for the GreenRoute API."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from clerk_backend_api import AuthenticateRequestOptions, authenticate_request
from fastapi import HTTPException, Request


@dataclass(frozen=True)
class ClerkIdentity:
    clerk_user_id: str
    claims: dict[str, Any]


def _authorized_parties() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "")
    parties = [value.strip().rstrip("/") for value in configured.split(",") if value.strip()]
    if "*" in parties:
        raise RuntimeError("Wildcard authorized parties are not permitted.")
    return parties or [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]


def require_clerk_user(request: Request) -> ClerkIdentity:
    """Verify a Clerk session token and return its immutable subject identifier."""
    secret_key = os.getenv("CLERK_SECRET_KEY", "").strip()
    if not secret_key:
        raise HTTPException(
            status_code=503,
            detail="Clerk authentication is not configured on this API.",
        )

    jwt_key = os.getenv("CLERK_JWT_KEY", "").strip() or None
    try:
        state = authenticate_request(
            request,
            AuthenticateRequestOptions(
                secret_key=secret_key,
                jwt_key=jwt_key,
                authorized_parties=_authorized_parties(),
                accepts_token=["session_token"],
            ),
        )
    except Exception:
        # Do not leak token, key, or provider error details to the caller.
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")

    if not state.is_signed_in or not isinstance(state.payload, dict):
        raise HTTPException(status_code=401, detail="Authentication is required.")

    subject = state.payload.get("sub")
    if not isinstance(subject, str) or not subject.startswith("user_"):
        raise HTTPException(status_code=401, detail="Invalid authenticated user identity.")

    return ClerkIdentity(clerk_user_id=subject, claims=state.payload)
