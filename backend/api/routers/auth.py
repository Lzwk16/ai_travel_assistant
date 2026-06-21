"""Authentication endpoints: register and login (JWT)."""

from api.schemas import Token, UserCreate, UserRead
from api.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from api.storage import Storage, User, get_storage
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, storage: Storage = Depends(get_storage)) -> UserRead:
    if storage.get_user_by_email(body.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    return storage.create_user(
        email=body.email, hashed_password=hash_password(body.password)
    )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    storage: Storage = Depends(get_storage),
) -> Token:
    # OAuth2 form uses "username"; we carry the email there.
    user = storage.get_user_by_email(form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
def read_me(user: User = Depends(get_current_user)) -> UserRead:
    """Return the authenticated user (id, email, role).

    The login token carries only the user id, so the frontend calls this to
    resolve the current user's identity and role after signing in.
    """
    return user
