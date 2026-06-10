from fastapi import APIRouter, HTTPException, Depends, status, Response
from datetime import datetime, timedelta, timezone

from database import Database
from dependencies import get_db
from schemas import UserCreate, UserResponse, UserLogin, TokenResponse, UserUpdate
from utils import hash_password, verify_password, create_access_token, get_current_user
from functions import (
    create_user,
    get_user_by_login,
    get_user_by_id,
    get_user_by_username,
    update_last_login,
    delete_user,
    update_user_profile,
)

users_router = APIRouter(prefix="/users", tags=["Пользователи"])


@users_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
def register(user_data: UserCreate, db: Database = Depends(get_db)):
    if get_user_by_login(db, user_data.login):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Login already registered")

    if get_user_by_username(db, user_data.username):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")

    password_hash = hash_password(user_data.password)
    user_id = create_user(db, username=user_data.username, login=str(user_data.login), password_hash=password_hash)

    if not user_id:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create user")

    # create_user возвращает lastrowid — получаем свежие данные по ID
    user = get_user_by_id(db, user_id)
    return user


@users_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход в систему",
)
def login(login_data: UserLogin, response: Response, db: Database = Depends(get_db)):
    user = get_user_by_login(db, str(login_data.login))
    if not user or not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    update_last_login(db, user["id"])

    token_data = {
        "sub": str(user["id"]),
        "login": user["login"],
        "username": user["username"],
    }
    access_token = create_access_token(token_data)


    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,      # недоступно JS — защита от XSS
        max_age=86400,      # 24 часа
        samesite="lax",     # защита от CSRF
    )


    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400,
        user_id=user["id"],
        username=user["username"],
    )


@users_router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}


@users_router.get(
    "/me",
    response_model=UserResponse,
    summary="Профиль текущего пользователя",
)
def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    user = get_user_by_id(db, current_user["id"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@users_router.patch(
    "/me",
    response_model=UserResponse,
    summary="Обновить профиль текущего пользователя",
)
def update_my_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if update_data.username:
        existing = get_user_by_username(db, update_data.username)
        if existing and existing["id"] != current_user["id"]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")

    if update_data.login:
        existing = get_user_by_login(db, update_data.login)
        if existing and existing["id"] != current_user["id"]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Login already registered")

    new_password_hash = hash_password(update_data.password) if update_data.password else None

    success = update_user_profile(
        db,
        user_id=current_user["id"],
        username=update_data.username,
        login=update_data.login,
        password_hash=new_password_hash,
    )

    if not success:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update profile")

    return get_user_by_id(db, current_user["id"])


@users_router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить аккаунт",
)
def delete_my_account(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if not delete_user(db, current_user["id"]):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete account")


@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Профиль пользователя по ID",
)
def get_user_by_id_endpoint(user_id: int, db: Database = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user
