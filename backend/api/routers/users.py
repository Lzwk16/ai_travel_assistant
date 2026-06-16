"""Admin-only user endpoints."""

from api.schemas import UserRead
from api.security import require_admin
from api.storage import Storage, User, get_storage
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    _admin: User = Depends(require_admin),
    storage: Storage = Depends(get_storage),
) -> list[UserRead]:
    """List all registered users. Restricted to users with admin privileges."""
    return storage.list_users()
