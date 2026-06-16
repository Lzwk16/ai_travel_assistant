"""Storage factory — selects the backend from settings and caches a singleton.

``get_storage`` is the FastAPI dependency every router/task depends on. The
``lru_cache`` makes it a process-wide singleton (important for ``JSONFileStorage``,
whose lock must be shared across all requests and background threads).
"""

from functools import lru_cache

from api import settings
from api.storage.base import Storage, Trip, User

__all__ = ["get_storage", "Storage", "User", "Trip"]


@lru_cache
def get_storage() -> Storage:
    if settings.STORAGE_BACKEND == "json":
        from api.storage.json_store import JSONFileStorage

        return JSONFileStorage(settings.JSON_DATA_DIR)

    if settings.STORAGE_BACKEND == "sql":
        # Added in Phase 2 (SQLite) / Phase 3 (PostgreSQL).
        from api.storage.sql_store import SqlAlchemyStorage

        if not settings.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is required when STORAGE_BACKEND='sql'.")
        return SqlAlchemyStorage(settings.DATABASE_URL)

    raise RuntimeError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND!r}")
