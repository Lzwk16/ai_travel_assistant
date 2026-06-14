"""Environment-driven configuration for the FastAPI layer.

Single source of truth for auth/storage settings. Secrets (the JWT signing key)
are read from the environment with **no in-code default** so a missing value
fails loudly rather than silently shipping a forgeable key. Non-secret values
are plain constants or env-overridable with safe defaults.
"""

import os

try:  # crewai[tools] usually pulls python-dotenv; if not fall back to the ambient env
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

# --- JWT (auth) ---
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is required. Generate one with "
        '`python -c "import secrets; print(secrets.token_hex(32))"` and add it to .env.'
    )

JWT_ALGORITHM = "HS256"  # not a secret — a public, standard algorithm name
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# --- CORS ---
CORS_ALLOW_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()
]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"

# --- Storage ---
# "json" -> JSON files (Phase 1 MVP);
# "sql" -> SQLAlchemy (Phase 2 SQLite/Phase 3 Postgres)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "json")
JSON_DATA_DIR = os.getenv("JSON_DATA_DIR", "data")
DATABASE_URL = os.getenv("DATABASE_URL", "")  # required when STORAGE_BACKEND == "sql"
