"""Phase 2 / Phase 3 storage: a single SQLAlchemy adapter.

One adapter serves both phases — only the ``DATABASE_URL`` differs:
  * Phase 2 -> ``sqlite:///./travel_assistant.db``
  * Phase 3 -> ``postgresql+psycopg://.../travel_assistant``

It maps ORM rows back to the backend-independent ``User`` / ``Trip`` dataclasses
from ``base.py``, so the API layer (routers, security, tasks) is byte-for-byte
unchanged from Phase 1. ``request`` / ``result`` use a JSON column that becomes
``JSONB`` automatically on PostgreSQL via ``with_variant``.

Each method runs its own short session (session-per-operation), which is the
safe pattern for FastAPI's threadpool plus the background trip threads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from api.storage.base import Feedback, Trip, User
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    inspect,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# Plain JSON on SQLite; JSONB on PostgreSQL (Phase 3) — chosen per-dialect.
_JSONType = JSON().with_variant(JSONB, "postgresql")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; re-attach UTC so the wire format matches
    the JSON backend exactly (ISO string with a ``+00:00`` offset)."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String(16), default="user", server_default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TripRow(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    trip_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    request: Mapped[dict[str, Any]] = mapped_column(_JSONType)
    result: Mapped[dict[str, Any] | None] = mapped_column(_JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FeedbackRow(Base):
    __tablename__ = "trip_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique: one feedback per trip (create_feedback upserts on this).
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.id"), unique=True, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SqlAlchemyStorage:
    def __init__(self, database_url: str) -> None:
        if database_url.startswith("sqlite"):
            # SQLite connections are thread-affine by default; the FastAPI
            # threadpool + background trip threads need this disabled. Safe with
            # session-per-operation (no connection shared across threads at once).
            engine = create_engine(
                database_url, connect_args={"check_same_thread": False}
            )
        else:
            # PostgreSQL (Phase 3): validate pooled connections before use to
            # survive DB restarts / idle drops.
            engine = create_engine(database_url, pool_pre_ping=True)

        self._engine = engine
        # expire_on_commit=False so attributes stay readable after commit when we
        # map the row to a dataclass.
        self._Session = sessionmaker(engine, expire_on_commit=False)
        Base.metadata.create_all(engine)
        self._ensure_columns()

    def _ensure_columns(self) -> None:
        """Idempotent stopgap migration for databases created before a column
        existed (e.g. ``users.role``). ``create_all`` only creates missing
        tables, never alters existing ones. Real migrations arrive with Alembic
        during deployment."""
        inspector = inspect(self._engine)
        user_columns = {c["name"] for c in inspector.get_columns("users")}
        if "role" not in user_columns:
            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN role VARCHAR(16) "
                        "NOT NULL DEFAULT 'user'"
                    )
                )

    # --- users ---
    def create_user(self, email: str, hashed_password: str) -> User:
        with self._Session() as session:
            row = UserRow(email=email, hashed_password=hashed_password)
            session.add(row)
            session.commit()
            return self._to_user(row)

    def get_user_by_email(self, email: str) -> User | None:
        with self._Session() as session:
            row = session.scalar(select(UserRow).where(UserRow.email == email))
            return self._to_user(row) if row else None

    def get_user(self, user_id: int) -> User | None:
        with self._Session() as session:
            row = session.get(UserRow, user_id)
            return self._to_user(row) if row else None

    def list_users(self) -> list[User]:
        with self._Session() as session:
            rows = session.scalars(select(UserRow).order_by(UserRow.id)).all()
            return [self._to_user(r) for r in rows]

    def set_user_role(self, user_id: int, role: str) -> User:
        with self._Session() as session:
            row = session.get(UserRow, user_id)
            if row is None:
                raise KeyError(f"User {user_id} not found")
            row.role = role
            session.commit()
            return self._to_user(row)

    # --- trips ---
    def create_trip(
        self, user_id: int, trip_type: str, request: dict[str, Any]
    ) -> Trip:
        with self._Session() as session:
            row = TripRow(
                user_id=user_id,
                trip_type=trip_type,
                status="pending",
                request=request,
                result=None,
            )
            session.add(row)
            session.commit()
            return self._to_trip(row)

    def get_trip(self, trip_id: int) -> Trip | None:
        with self._Session() as session:
            row = session.get(TripRow, trip_id)
            return self._to_trip(row) if row else None

    def list_trips(self, user_id: int) -> list[Trip]:
        with self._Session() as session:
            rows = session.scalars(
                select(TripRow)
                .where(TripRow.user_id == user_id)
                .order_by(TripRow.created_at.desc(), TripRow.id.desc())
            ).all()
            return [self._to_trip(r) for r in rows]

    def update_trip(self, trip_id: int, **fields: Any) -> Trip:
        with self._Session() as session:
            row = session.get(TripRow, trip_id)
            if row is None:
                raise KeyError(f"Trip {trip_id} not found")
            for key, value in fields.items():
                setattr(row, key, value)
            session.commit()
            return self._to_trip(row)

    # --- feedback for a completed trip ---
    def create_feedback(
        self, trip_id: int, user_id: int, rating: int, comment: str | None
    ) -> Feedback:
        with self._Session() as session:
            row = session.scalar(
                select(FeedbackRow).where(FeedbackRow.trip_id == trip_id)
            )
            if row is None:  # first feedback for this trip
                row = FeedbackRow(
                    trip_id=trip_id,
                    user_id=user_id,
                    rating=rating,
                    comment=comment,
                )
                session.add(row)
            else:  # re-submitting overwrites the prior feedback
                row.rating = rating
                row.comment = comment
                row.created_at = _now()
            session.commit()
            return self._to_feedback(row)

    def get_feedback_for_trip(self, trip_id: int) -> Feedback | None:
        with self._Session() as session:
            row = session.scalar(
                select(FeedbackRow).where(FeedbackRow.trip_id == trip_id)
            )
            return self._to_feedback(row) if row else None

    # --- row -> dataclass mappers ---
    @staticmethod
    def _to_user(row: UserRow) -> User:
        return User(
            id=row.id,
            email=row.email,
            hashed_password=row.hashed_password,
            role=row.role,
            created_at=_as_utc(row.created_at),
        )

    @staticmethod
    def _to_trip(row: TripRow) -> Trip:
        return Trip(
            id=row.id,
            user_id=row.user_id,
            trip_type=row.trip_type,
            status=row.status,
            request=row.request,
            result=row.result,
            created_at=_as_utc(row.created_at),
            completed_at=_as_utc(row.completed_at),
        )

    @staticmethod
    def _to_feedback(row: FeedbackRow) -> Feedback:
        return Feedback(
            id=row.id,
            trip_id=row.trip_id,
            user_id=row.user_id,
            rating=row.rating,
            comment=row.comment,
            created_at=_as_utc(row.created_at),
        )
