"""
Authentication endpoints for the High School Management System API
"""

from datetime import datetime, timedelta, timezone
import secrets
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Header

from ..database import teachers_collection, sessions_collection, verify_password

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


def parse_bearer_token(authorization: Optional[str]) -> str:
    """Extract bearer token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")

    token = authorization[len(prefix):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    return token


def validate_session_token(authorization: Optional[str]) -> Dict[str, Any]:
    """Validate session token and return teacher profile."""
    token = parse_bearer_token(authorization)
    session = sessions_collection.find_one({"_id": token})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session.get("expires_at")
    now = datetime.now(timezone.utc)
    if not isinstance(expires_at, datetime) or expires_at.astimezone(timezone.utc) < now:
        sessions_collection.delete_one({"_id": token})
        raise HTTPException(status_code=401, detail="Session expired")

    teacher = teachers_collection.find_one({"_id": session.get("username")})
    if not teacher:
        sessions_collection.delete_one({"_id": token})
        raise HTTPException(status_code=401, detail="Invalid session")

    return {
        "username": teacher["username"],
        "display_name": teacher["display_name"],
        "role": teacher["role"],
        "session_token": token,
    }


@router.post("/login")
def login(username: str, password: str) -> Dict[str, Any]:
    """Login a teacher account"""
    # Find the teacher in the database
    teacher = teachers_collection.find_one({"_id": username})

    # Verify password using Argon2 verifier from database.py
    if not teacher or not verify_password(teacher.get("password", ""), password):
        raise HTTPException(
            status_code=401, detail="Invalid username or password")

    # Create a short-lived server-side session token.
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    sessions_collection.insert_one(
        {
            "_id": token,
            "username": teacher["username"],
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
        }
    )

    # Return teacher information with session token.
    return {
        "username": teacher["username"],
        "display_name": teacher["display_name"],
        "role": teacher["role"],
        "session_token": token,
    }


@router.get("/check-session")
def check_session(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Check whether an Authorization bearer session is valid."""
    return validate_session_token(authorization)


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Invalidate the current bearer session token."""
    token = parse_bearer_token(authorization)
    sessions_collection.delete_one({"_id": token})
    return {"message": "Logged out"}
