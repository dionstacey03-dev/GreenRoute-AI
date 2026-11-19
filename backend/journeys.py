"""Authenticated, owner-scoped saved journey endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from auth import ClerkIdentity, require_clerk_user
from database import database_is_configured, get_session_factory
from models import SavedJourney, User

router = APIRouter(prefix="/api", tags=["authenticated"])


def get_db():
    if not database_is_configured():
        raise HTTPException(status_code=503, detail="Database is not configured.")
    try:
        factory = get_session_factory()
    except (RuntimeError, SQLAlchemyError):
        raise HTTPException(status_code=503, detail="Database is unavailable.")
    session = factory()
    try:
        yield session
    finally:
        session.close()


class SavedJourneyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str = Field(min_length=2, max_length=150)
    destination: str = Field(min_length=2, max_length=150)
    route_name: str = Field(min_length=1, max_length=100)
    preference: Literal["fastest", "cheapest", "greenest", "balanced"]
    distance_km: float = Field(ge=0, le=100000)
    duration_minutes: int = Field(ge=0, le=1000000)
    estimated_cost_lkr: float = Field(ge=0, le=100000000)
    estimated_co2_kg: float = Field(ge=0, le=1000000)
    green_score: float = Field(ge=0, le=100)
    ranking_score: float = Field(ge=0, le=100)
    estimated_cost_difference_lkr: float = Field(default=0, ge=0, le=100000000)
    estimated_co2_difference_kg: float = Field(default=0, ge=0, le=1000000)


def _local_user(db: Session, identity: ClerkIdentity) -> User:
    user = db.scalar(select(User).where(User.clerk_user_id == identity.clerk_user_id))
    if user is not None:
        return user

    # Clerk is the identity source. Do not copy passwords or trust client email fields.
    user = User(clerk_user_id=identity.clerk_user_id, email=None, password_hash=None)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        # Concurrent first requests can race on the unique Clerk subject index.
        db.rollback()
        existing = db.scalar(select(User).where(User.clerk_user_id == identity.clerk_user_id))
        if existing is not None:
            return existing
        raise HTTPException(status_code=503, detail="Could not provision the application user.")


def _journey_payload(journey: SavedJourney) -> dict:
    return {
        "id": str(journey.id),
        "origin": journey.origin,
        "destination": journey.destination,
        "route_name": journey.route_name,
        "preference": journey.preference,
        "distance_km": journey.distance_km,
        "duration_minutes": journey.duration_minutes,
        "estimated_cost_lkr": journey.estimated_cost_lkr,
        "estimated_co2_kg": journey.estimated_co2_kg,
        "green_score": journey.green_score,
        "ranking_score": journey.ranking_score,
        "estimated_cost_difference_lkr": journey.estimated_cost_difference_lkr,
        "estimated_co2_difference_kg": journey.estimated_co2_difference_kg,
        "created_at": journey.created_at.isoformat() if isinstance(journey.created_at, datetime) else None,
    }


@router.get("/me")
def get_current_profile(
    identity: ClerkIdentity = Depends(require_clerk_user),
    db: Session = Depends(get_db),
):
    user = _local_user(db, identity)
    return {"clerk_user_id": identity.clerk_user_id, "application_user_id": str(user.id)}


@router.get("/journeys")
def list_saved_journeys(
    identity: ClerkIdentity = Depends(require_clerk_user),
    db: Session = Depends(get_db),
):
    user = _local_user(db, identity)
    journeys = db.scalars(
        select(SavedJourney)
        .where(SavedJourney.user_id == user.id)
        .order_by(SavedJourney.created_at.desc(), SavedJourney.id.desc())
    ).all()
    return {"items": [_journey_payload(item) for item in journeys], "count": len(journeys)}


@router.post("/journeys", status_code=status.HTTP_201_CREATED)
def create_saved_journey(
    payload: SavedJourneyCreate,
    identity: ClerkIdentity = Depends(require_clerk_user),
    db: Session = Depends(get_db),
):
    user = _local_user(db, identity)
    journey = SavedJourney(user_id=user.id, **payload.model_dump())
    db.add(journey)
    try:
        db.commit()
        db.refresh(journey)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Could not save the journey.")
    return _journey_payload(journey)


@router.delete("/journeys/{journey_id}")
def delete_saved_journey(
    journey_id: uuid.UUID,
    identity: ClerkIdentity = Depends(require_clerk_user),
    db: Session = Depends(get_db),
):
    user = _local_user(db, identity)
    journey = db.scalar(
        select(SavedJourney).where(
            SavedJourney.id == journey_id,
            SavedJourney.user_id == user.id,
        )
    )
    if journey is None:
        # A 404 avoids revealing whether another user's journey exists.
        raise HTTPException(status_code=404, detail="Saved journey not found.")
    db.delete(journey)
    db.commit()
    return {"deleted": True, "id": str(journey_id)}
