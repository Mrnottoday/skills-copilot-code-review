"""
Announcement endpoints for the High School Management System API
"""

from datetime import date
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, field_validator

from .auth import validate_session_token
from ..database import announcements_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementPayload(BaseModel):
    title: str
    message: str
    expiration_date: str
    start_date: Optional[str] = None

    @field_validator("title", "message")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Value is required")
        return text

    @field_validator("expiration_date")
    @classmethod
    def validate_expiration_date(cls, value: str) -> str:
        normalized = value.strip()
        parse_iso_date(normalized)
        return normalized

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if normalized == "":
            return None
        parse_iso_date(normalized)
        return normalized


def parse_iso_date(value: str) -> date:
    """Validate date in YYYY-MM-DD format."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD format") from exc


def ensure_date_range(start_date: Optional[str], expiration_date: str) -> None:
    """Ensure expiration is not before start date when a start date exists."""
    expiration = parse_iso_date(expiration_date)
    if start_date:
        start = parse_iso_date(start_date)
        if expiration < start:
            raise ValueError("Expiration must be after start date")


def require_signed_in_user(authorization: Optional[str]) -> Dict[str, Any]:
    """Require a valid bearer session and return user profile."""
    return validate_session_token(authorization)


def serialize_announcement(announcement: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize MongoDB announcement documents for JSON responses."""
    return {
        "id": str(announcement["_id"]),
        "title": announcement.get("title", ""),
        "message": announcement.get("message", ""),
        "start_date": announcement.get("start_date"),
        "expiration_date": announcement.get("expiration_date", ""),
        "created_at": announcement.get("created_at"),
        "updated_at": announcement.get("updated_at"),
    }


@router.get("", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get currently active announcements for all users."""
    today_iso = date.today().isoformat()

    query = {
        "expiration_date": {"$gte": today_iso},
        "$or": [
            {"start_date": None},
            {"start_date": {"$exists": False}},
            {"start_date": ""},
            {"start_date": {"$lte": today_iso}},
        ],
    }

    announcements = announcements_collection.find(query).sort("expiration_date", 1)
    return [serialize_announcement(doc) for doc in announcements]


@router.get("/manage", response_model=List[Dict[str, Any]])
def get_all_announcements(authorization: Optional[str] = Header(None)) -> List[Dict[str, Any]]:
    """Get all announcements for management views (requires auth)."""
    require_signed_in_user(authorization)

    announcements = announcements_collection.find({}).sort("expiration_date", 1)
    return [serialize_announcement(doc) for doc in announcements]


@router.post("", response_model=Dict[str, Any])
def create_announcement(payload: AnnouncementPayload, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Create a new announcement (requires auth)."""
    require_signed_in_user(authorization)

    try:
        ensure_date_range(payload.start_date, payload.expiration_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    now_iso = date.today().isoformat()
    document = {
        "title": payload.title,
        "message": payload.message,
        "start_date": payload.start_date,
        "expiration_date": payload.expiration_date,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    result = announcements_collection.insert_one(document)
    created = announcements_collection.find_one({"_id": result.inserted_id})
    return serialize_announcement(created)


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    payload: AnnouncementPayload,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Update an existing announcement (requires auth)."""
    require_signed_in_user(authorization)

    try:
        ensure_date_range(payload.start_date, payload.expiration_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        object_id = ObjectId(announcement_id)
    except InvalidId as exc:
        raise HTTPException(status_code=404, detail="Announcement not found") from exc

    update_result = announcements_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "title": payload.title,
                "message": payload.message,
                "start_date": payload.start_date,
                "expiration_date": payload.expiration_date,
                "updated_at": date.today().isoformat(),
            }
        }
    )

    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    updated = announcements_collection.find_one({"_id": object_id})
    return serialize_announcement(updated)


@router.delete("/{announcement_id}", response_model=Dict[str, str])
def delete_announcement(announcement_id: str, authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Delete an announcement (requires auth)."""
    require_signed_in_user(authorization)

    try:
        object_id = ObjectId(announcement_id)
    except InvalidId as exc:
        raise HTTPException(status_code=404, detail="Announcement not found") from exc

    delete_result = announcements_collection.delete_one({"_id": object_id})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted"}
