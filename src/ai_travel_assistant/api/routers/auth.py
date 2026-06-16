"""Authentication endpoints: register and login (JWT)."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ai_travel_assistant.api.schemas import Token, UserCreate, UserRead
from ai_travel_assistant.api.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from ai_travel_assistant.api.storage import Storage, get_storage

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
