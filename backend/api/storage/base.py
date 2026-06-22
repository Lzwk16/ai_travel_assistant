"""Storage abstraction — the architectural backbone of the phased rollout.

Every component above this line (routers, security, tasks) depends only on the
``Storage`` protocol and the ``User`` / ``Trip`` dataclasses, so swapping the
backend (JSON files -> SQLite -> PostgreSQL) never touches the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass
class User:
    id: int
    email: str
    hashed_password: str
    role: str  # "user" | "admin"
    created_at: datetime


@dataclass
class Trip:
    id: int
    user_id: int
    trip_type: str  # "itinerary" | "flights"
    status: str  # "pending" | "running" | "completed" | "failed"
    request: dict[str, Any]
    result: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None


@dataclass
class Feedback:
    """User rating/comment on a completed trip. One row
    per trip; re-submitting overwrites the prior rating."""

    id: int
    trip_id: int
    user_id: int
    rating: int  # 1-5
    comment: str | None
    created_at: datetime


class Storage(Protocol):
    """Persistence operations the API needs. Implementations return the
    backend-independent dataclasses above so response shapes stay identical."""

    def create_user(self, email: str, hashed_password: str) -> User: ...
    def get_user_by_email(self, email: str) -> User | None: ...
    def get_user(self, user_id: int) -> User | None: ...
    def list_users(self) -> list[User]: ...
    def set_user_role(self, user_id: int, role: str) -> User: ...

    def create_trip(
        self, user_id: int, trip_type: str, request: dict[str, Any]
    ) -> Trip: ...
    def get_trip(self, trip_id: int) -> Trip | None: ...
    def list_trips(self, user_id: int) -> list[Trip]: ...
    def update_trip(self, trip_id: int, **fields: Any) -> Trip: ...

    # Feedback for a completed trip. One row per trip — ``create_feedback`` upserts.
    def create_feedback(
        self, trip_id: int, user_id: int, rating: int, comment: str | None
    ) -> Feedback: ...
    def get_feedback_for_trip(self, trip_id: int) -> Feedback | None: ...
