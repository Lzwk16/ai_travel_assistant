"""Admin-only user endpoints."""

from fastapi import APIRouter, Depends

from ai_travel_assistant.api.schemas import UserRead
from ai_travel_assistant.api.security import require_admin
from ai_travel_assistant.api.storage import Storage, User, get_storage

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    _admin: User = Depends(require_admin),
    storage: Storage = Depends(get_storage),
) -> list[UserRead]:
    """List all registered users. Restricted to admins (``settings.ADMIN_EMAILS``).

    Returns ``UserRead`` rows, which deliberately exclude ``hashed_password`` —
    the password hash is never exposed over the API.
    """
    return storage.list_users()
