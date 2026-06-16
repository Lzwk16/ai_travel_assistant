"""Authentication primitives: password hashing, JWT issue/verify,
current-user dependency.

The signing key and algorithm come exclusively from ``settings`` (env-backed
secret + constant algorithm) — never hardcoded here.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from ai_travel_assistant.api import settings
from ai_travel_assistant.api.storage import Storage, User, get_storage

# Only bcrypt is installed (pwdlib[bcrypt]); avoid PasswordHash.recommended(),
# which would also require argon2-cffi.
_password_hash = PasswordHash((BcryptHasher(),))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    storage: Storage = Depends(get_storage),
) -> User:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = int(payload["sub"])
        user = storage.get_user(user_id)
        if user is None:
            raise _credentials_exc
        return user
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _credentials_exc


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Authorize admin-only endpoints: the authenticated user's ``role`` must be
    ``"admin"`` (stored per-user in the database). Returns the user so handlers
    can reuse it; raises 403 otherwise."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{user.email} is not an admin. Admin privileges required",
        )
    return user
