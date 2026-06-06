from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timedelta, timezone

# Импорты из нашего проекта
from databases import Database
from schemas import *
from utils import *
from functions import (
    create_user, 
    get_user_by_login, 
    get_user_by_id,
    get_user_by_username,
    update_last_login,
    delete_user,
    update_user_profile
)


users_router = APIRouter(prefix="/users", tags=["Пользователи"])

security = HTTPBearer()

def get_db():
    db = Database("test_2_1.db")
    try:
        yield db
    finally:
        pass


@users_router.post(
    "/register", 
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создаёт нового пользователя с уникальными username и email"
)
def register(
    user_data: UserCreate, 
    db: Database = Depends(get_db)
):
    """
    Регистрация нового пользователя.
    
    - **username**: уникальное имя пользователя (3-50 символов)
    - **email**: уникальный email (валидируется автоматически)
    - **password**: пароль (минимум 6 символов)
    """
    
    # 1. Проверяем, не занят ли email
    existing_login = get_user_by_login(db, user_data.login)
    if existing_login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="login already registered"
        )
    
    # 2. Проверяем, не занят ли username
    existing_username = get_user_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # 3. Хэшируем пароль (никогда не храним в открытом виде!)
    password_hash = hash_password(user_data.password)
    
    # 4. Создаём пользователя в БД
    user_id = create_user(
        db, 
        username=user_data.username,
        login=user_data.login,
        password_hash=password_hash
    )
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user. Please try again."
        )
    
    # 5. Получаем созданного пользователя и возвращаем (без пароля!)
    user = get_user_by_id(db, user_id)
    return user

@users_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход в систему",
    description="Аутентификация пользователя и получение JWT токена"
)
def login(
    login_data: UserLogin,
    db: Database = Depends(get_db)
):
    """
    Вход в систему.
    
    - **login**: email пользователя
    - **password**: пароль
    
    Возвращает JWT токен для последующих авторизованных запросов.
    Токен действителен 24 часа.
    """
    
    # 1. Ищем пользователя по email
    user = get_user_by_login(db, login_data.login)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Проверяем пароль
    if not verify_password(login_data.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Обновляем время последнего входа
    update_last_login(db, user['id'])
    
    # 4. Создаём JWT токен


    token_data = {
    "sub": str(user['id']),
    "login": user['login'],
    "username": user['username'],
    "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }


    access_token = create_access_token(token_data)
    
    # 5. Возвращаем токен
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400,  # 24 часа в секундах
        user_id=user['id'],
        username=user['username']
    )


@users_router.get(
    "/me",
    response_model=UserResponse,
    summary="Получить профиль текущего пользователя",
    description="Возвращает информацию о текущем авторизованном пользователе"
)
def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Получить профиль текущего пользователя.
    
    Требует наличия валидного JWT токена в заголовке Authorization.
    """
    # current_user уже содержит данные пользователя из токена
    # Но для безопасности получаем свежие данные из БД
    user = get_user_by_id(db, current_user['id'])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Получить профиль пользователя по ID",
    description="Возвращает публичную информацию о пользователе"
)
def get_user_by_id_endpoint(
    user_id: int,
    db: Database = Depends(get_db)
):
    """
    Получить публичную информацию о пользователе по его ID.
    
    Доступно без авторизации (только публичные данные).
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@users_router.put(
    "/me",
    response_model=UserResponse,
    summary="Обновить профиль текущего пользователя",
    description="Обновляет информацию о пользователе"
)
def update_my_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Обновить профиль текущего пользователя.
    
    Можно обновить:
    - username (если не занят другим пользователем)
    - email (если не занят другим пользователем)
    - password (будет автоматически захэширован)
    """
    
    # 1. Если обновляется username, проверяем, не занят ли он
    if update_data.username:
        existing = get_user_by_username(db, update_data.username)
        if existing and existing['id'] != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # 2. Если обновляется email, проверяем, не занят ли он
    if update_data.login:
        existing = get_user_by_login(db, update_data.login)
        if existing and existing['id'] != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="login already registered"
            )
    
    # 3. Если меняется пароль, хэшируем новый
    new_password_hash = None
    if update_data.password:
        new_password_hash = hash_password(update_data.password)
    
    # 4. Обновляем профиль в БД
    success = update_user_profile(
        db,
        user_id=current_user['id'],
        username=update_data.username,
        login=update_data.login,
        password_hash=new_password_hash
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )
    
    # 5. Возвращаем обновлённые данные
    updated_user = get_user_by_id(db, current_user['id'])
    return updated_user


@users_router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить аккаунт текущего пользователя",
    description="Полностью удаляет аккаунт пользователя и все связанные данные"
)
def delete_my_account(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Удалить аккаунт текущего пользователя.
    
    ВНИМАНИЕ: Это действие необратимо! Все данные пользователя
    (тренировки, упражнения, шаблоны, цели) будут удалены
    (благодаря ON DELETE CASCADE в БД).
    """
    
    success = delete_user(db, current_user['id'])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )
    
    # Возвращаем 204 No Content (без тела ответа)
    return None


@users_router.post(
    "/logout",
    summary="Выход из системы",
    description="Завершает сессию пользователя (на клиенте нужно удалить токен)"
)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    """
    Выход из системы.
    
    """
    
    return {
        "message": "Successfully logged out. Please delete your token on client side."
    }
