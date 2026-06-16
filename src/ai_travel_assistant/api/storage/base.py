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


class Storage(Protocol):
    """Persistence operations the API needs. Implementations return the
    backend-independent dataclasses above so response shapes stay identical."""

    def create_user(self, email: str, hashed_password: str) -> User: ...
    def get_user_by_email(self, email: str) -> User | None: ...
    def get_user(self, user_id: int) -> User | None: ...

    def create_trip(
        self, user_id: int, trip_type: str, request: dict[str, Any]
    ) -> Trip: ...
    def get_trip(self, trip_id: int) -> Trip | None: ...
    def list_trips(self, user_id: int) -> list[Trip]: ...
    def update_trip(self, trip_id: int, **fields: Any) -> Trip: ...
