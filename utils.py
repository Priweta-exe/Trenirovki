"""
utils.py - Вспомогательные утилиты для приложения

Содержит:
- Хэширование и проверку паролей (bcrypt)
- JWT токены (создание, верификация, декодирование)
- Зависимости FastAPI для получения текущего пользователя
- Вспомогательные функции для работы с датами, валидацией и т.д.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

import bcrypt
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Конфигурация JWT
# В реальном проекте эти значения должны быть в переменных окружения!
JWT_SECRET_KEY = "your-secret-key-change-this-in-production"  # Замените на свой!
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

# Для проверки токенов в защищённых эндпоинтах
security = HTTPBearer()


# ============================================
# 1. РАБОТА С ПАРОЛЯМИ (bcrypt)
# ============================================

def hash_password(password: str) -> str:
    """
    Хэширует пароль с использованием bcrypt.
    
    Args:
        password: Обычный текст пароля
        
    Returns:
        str: Хэшированный пароль (с солью внутри)
        
    Example:
        hashed = hash_password("my_secret_password")
        # '$2b$12$QjH169pXq9GC9R8Z7kqG.1Vk/XzT8cFmW5yYpQFU3bYLxJzLmNqW'
    """
    # encode() - преобразует строку в байты (bcrypt работает с байтами)
    # gensalt() - генерирует случайную "соль"
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)  # rounds=12 - стандартная сложность
    hashed = bcrypt.hashpw(password_bytes, salt)
    # decode() - преобразуем обратно в строку для хранения в БД
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли пароль хэшу.
    
    Args:
        plain_password: Обычный текст пароля
        hashed_password: Хэш из базы данных
        
    Returns:
        bool: True если пароль правильный
        
    Example:
        is_correct = verify_password("my_secret_password", stored_hash)
    """
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


# ============================================
# 2. РАБОТА С JWT ТОКЕНАМИ
# ============================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Создаёт JWT токен доступа.
    
    Args:
        data: Словарь с данными для токена (обязательно содержит 'sub' - идентификатор пользователя)
        expires_delta: Время жизни токена (по умолчанию 24 часа)
        
    Returns:
        str: JWT токен
        
    Example:
        token = create_access_token({"sub": "123", "email": "user@example.com"})
    """
    # Копируем данные, чтобы не изменять оригинал
    to_encode = data.copy()
    
    # Устанавливаем время истечения
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    # Создаём токен
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Декодирует и проверяет JWT токен.
    
    Args:
        token: JWT токен
        
    Returns:
        dict: Данные из токена
        
    Raises:
        HTTPException: Если токен недействителен или просрочен
    """
    try:
        # Декодируем и проверяем подпись
        payload = jwt.decode(
            token, 
            JWT_SECRET_KEY, 
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = None  # Будет передано из эндпоинта
) -> Dict[str, Any]:
    """
    Зависимость FastAPI для получения текущего авторизованного пользователя.
    
    Используется в защищённых эндпоинтах:
        @app.get("/protected")
        def protected_route(current_user = Depends(get_current_user)):
            return {"user_id": current_user['id']}
    
    Args:
        credentials: Заголовок Authorization с токеном
        
    Returns:
        dict: Данные пользователя из токена
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    # Проверяем, что в токене есть 'sub' (идентификатор пользователя)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Здесь можно дополнительно загрузить пользователя из БД
    # и проверить, что он всё ещё существует и активен
    
    # Возвращаем данные из токена
    return {
        "id": int(user_id) if user_id.isdigit() else user_id,
        "email": payload.get("email"),
        "username": payload.get("username")
    }


# ============================================
# 3. ВАЛИДАЦИЯ ДАННЫХ
# ============================================

def validate_email(email: str) -> bool:
    """
    Проверяет, корректен ли email (без использования сложных библиотек).
    
    Args:
        email: Строка email
        
    Returns:
        bool: True если email валидный
    """
    # Простое регулярное выражение для проверки email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет сложность пароля.
    
    Args:
        password: Пароль для проверки
        
    Returns:
        tuple: (is_valid, error_message)
        
    Example:
        is_valid, error = validate_password_strength("weak")
        # (False, "Password must be at least 6 characters")
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    if len(password) > 100:
        return False, "Password is too long (max 100 characters)"
    
    # Опционально: проверка на наличие цифр и спецсимволов
    # if not any(c.isdigit() for c in password):
    #     return False, "Password must contain at least one digit"
    # 
    # if not any(c in "!@#$%^&*" for c in password):
    #     return False, "Password must contain at least one special character"
    
    return True, None


def sanitize_input(text: str) -> str:
    """
    Очищает входную строку от потенциально опасных символов.
    
    Args:
        text: Входная строка
        
    Returns:
        str: Очищенная строка
    """
    # Удаляем лишние пробелы в начале и конце
    text = text.strip()
    
    # Экранируем HTML символы (для защиты от XSS)
    html_chars = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
    }
    for char, escape in html_chars.items():
        text = text.replace(char, escape)
    
    return text


# ============================================
# 4. РАБОТА С ДАТАМИ
# ============================================

def get_current_date() -> str:
    """Возвращает текущую дату в формате YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")


def get_current_datetime() -> str:
    """Возвращает текущую дату и время в формате YYYY-MM-DD HH:MM:SS"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def days_between(date1: str, date2: str) -> int:
    """
    Вычисляет количество дней между двумя датами.
    
    Args:
        date1: Первая дата (YYYY-MM-DD)
        date2: Вторая дата (YYYY-MM-DD)
        
    Returns:
        int: Количество дней
    """
    d1 = datetime.strptime(date1, "%Y-%m-%d")
    d2 = datetime.strptime(date2, "%Y-%m-%d")
    return abs((d2 - d1).days)


def is_date_expired(date_str: str) -> bool:
    """
    Проверяет, истекла ли дата.
    
    Args:
        date_str: Дата в формате YYYY-MM-DD
        
    Returns:
        bool: True если дата в прошлом
    """
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    return target_date < today


# ============================================
# 5. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ FASTAPI
# ============================================

def success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """
    Формирует стандартный успешный ответ API.
    
    Args:
        data: Данные для возврата
        message: Сообщение
        
    Returns:
        dict: Стандартизированный ответ
    """
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": get_current_datetime()
    }


def error_response(message: str, error_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Формирует стандартный ответ с ошибкой.
    
    Args:
        message: Сообщение об ошибке
        error_code: Код ошибки (опционально)
        
    Returns:
        dict: Стандартизированный ответ об ошибке
    """
    response = {
        "success": False,
        "message": message,
        "timestamp": get_current_datetime()
    }
    if error_code:
        response["error_code"] = error_code
    return response


# ============================================
# 6. ФУНКЦИИ ДЛЯ ЛОГИРОВАНИЯ (опционально)
# ============================================

import logging
from functools import wraps

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def log_function_call(func):
    """
    Декоратор для логирования вызовов функций.
    
    Example:
        @log_function_call
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {str(e)}")
            raise
    return wrapper


# ============================================
# 7. ПРИМЕР ИСПОЛЬЗОВАНИЯ (для тестирования)
# ============================================

if __name__ == "__main__":
    # Тестирование хэширования паролей
    print("=== Тестирование bcrypt ===")
    password = "my_secret_password"
    hashed = hash_password(password)
    print(f"Password: {password}")
    print(f"Hash: {hashed}")
    print(f"Verify correct: {verify_password(password, hashed)}")
    print(f"Verify wrong: {verify_password('wrong', hashed)}")
    
    # Тестирование JWT
    print("\n=== Тестирование JWT ===")
    token_data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(token_data)
    print(f"Token: {token}")
    decoded = decode_token(token)
    print(f"Decoded: {decoded}")
    
    # Тестирование валидации
    print("\n=== Тестирование валидации ===")
    print(f"Email valid: {validate_email('test@example.com')}")
    print(f"Password strength: {validate_password_strength('weak')}")
    print(f"Sanitized: {sanitize_input('<script>alert("xss")</script>')}")
    
    # Тестирование дат
    print("\n=== Тестирование дат ===")
    print(f"Current date: {get_current_date()}")
    print(f"Days between: {days_between('2024-01-01', '2024-12-31')}")
    print(f"Is expired: {is_date_expired('2020-01-01')}")
    
    print("\n✅ Все тесты utils.py пройдены!")