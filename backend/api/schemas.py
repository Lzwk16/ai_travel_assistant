"""Pydantic request/response DTOs for the HTTP layer.

``UserRead`` / ``TripRead`` use ``from_attributes`` so they serialize the
backend-independent ``User`` / ``Trip`` dataclasses returned by storage.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TripCreate(BaseModel):
    trip_type: Literal["itinerary", "flights", "hotels"]
    request: dict[
        str, Any
    ]  # validated against Travel/Flight/HotelRequest in the router


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_type: str
    status: str
    request: dict[str, Any]
    result: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None
