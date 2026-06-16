"""Phase 1 storage: plain JSON files, zero database infrastructure.

Each entity lives in its own JSON array file. All mutations are guarded by a
re-entrant lock and written via a temp-file + ``os.replace`` so a crash mid-write
cannot corrupt the file. Suitable for a single-worker MVP; Phases 2-3 replace it
with SQLAlchemy without changing any caller.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

from ai_travel_assistant.api.storage.base import Trip, User


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class JSONFileStorage:
    def __init__(self, data_dir: str) -> None:
        self._lock = threading.RLock()
        os.makedirs(data_dir, exist_ok=True)
        self._users_path = os.path.join(data_dir, "users.json")
        self._trips_path = os.path.join(data_dir, "trips.json")
        for path in (self._users_path, self._trips_path):
            if not os.path.exists(path):
                self._write(path, [])

    # --- low-level file IO (callers hold self._lock) ---
    @staticmethod
    def _read(path: str) -> list[dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write(path: str, rows: list[dict[str, Any]]) -> None:
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    @staticmethod
    def _next_id(rows: list[dict[str, Any]]) -> int:
        return max((row["id"] for row in rows), default=0) + 1

    # --- users ---
    def create_user(self, email: str, hashed_password: str) -> User:
        with self._lock:
            rows = self._read(self._users_path)
            row = {
                "id": self._next_id(rows),
                "email": email,
                "hashed_password": hashed_password,
                "created_at": _now_iso(),
            }
            rows.append(row)
            self._write(self._users_path, rows)
            return self._to_user(row)

    def get_user_by_email(self, email: str) -> User | None:
        with self._lock:
            for row in self._read(self._users_path):
                if row["email"] == email:
                    return self._to_user(row)
        return None

    def get_user(self, user_id: int) -> User | None:
        with self._lock:
            for row in self._read(self._users_path):
                if row["id"] == user_id:
                    return self._to_user(row)
        return None

    # --- trips ---
    def create_trip(
        self, user_id: int, trip_type: str, request: dict[str, Any]
    ) -> Trip:
        with self._lock:
            rows = self._read(self._trips_path)
            row = {
                "id": self._next_id(rows),
                "user_id": user_id,
                "trip_type": trip_type,
                "status": "pending",
                "request": request,
                "result": None,
                "created_at": _now_iso(),
                "completed_at": None,
            }
            rows.append(row)
            self._write(self._trips_path, rows)
            return self._to_trip(row)

    def get_trip(self, trip_id: int) -> Trip | None:
        with self._lock:
            for row in self._read(self._trips_path):
                if row["id"] == trip_id:
                    return self._to_trip(row)
        return None

    def list_trips(self, user_id: int) -> list[Trip]:
        with self._lock:
            rows = [r for r in self._read(self._trips_path) if r["user_id"] == user_id]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return [self._to_trip(r) for r in rows]

    def update_trip(self, trip_id: int, **fields: Any) -> Trip:
        with self._lock:
            rows = self._read(self._trips_path)
            for row in rows:
                if row["id"] == trip_id:
                    for key, value in fields.items():
                        row[key] = (
                            value.isoformat() if isinstance(value, datetime) else value
                        )
                    self._write(self._trips_path, rows)
                    return self._to_trip(row)
        raise KeyError(f"Trip {trip_id} not found")

    # --- row -> dataclass mappers ---
    @staticmethod
    def _to_user(row: dict[str, Any]) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            created_at=_parse_dt(row["created_at"]),
        )

    @staticmethod
    def _to_trip(row: dict[str, Any]) -> Trip:
        return Trip(
            id=row["id"],
            user_id=row["user_id"],
            trip_type=row["trip_type"],
            status=row["status"],
            request=row["request"],
            result=row["result"],
            created_at=_parse_dt(row["created_at"]),
            completed_at=_parse_dt(row["completed_at"]),
        )
