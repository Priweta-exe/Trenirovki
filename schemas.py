"""
schemas.py - Pydantic модели для валидации входящих/исходящих данных
Отвечают за:
- Проверку типов данных
- Документирование API
- Сериализацию/десериализацию JSON
"""

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any






# === User schemas ===
class UserCreate(BaseModel):
    """Схема для регистрации пользователя"""
    username: str = Field(..., min_length=1, max_length=50)
    login: EmailStr
    password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    """Схема для ответа (без пароля)"""
    id: int
    username: str
    login: str
    created_at: datetime

class UserLogin(BaseModel):
    """Схема для входа"""
    login: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Время жизни в секундах")
    user_id: int
    username: str
    login: Optional[EmailStr] = None


class UserUpdate(BaseModel):
    
    username: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=50,
        description="Новое имя пользователя (3-50 символов)"
    )
    
    login: Optional[EmailStr] = Field(
        None,
        description="Новый login (должен быть валидным)"
    )
    
    password: Optional[str] = Field(
        None, 
        min_length=6, 
        max_length=100,
        description="Новый пароль (минимум 6 символов)"
    )





# === Exercise schemas ===





class ExerciseCreate(BaseModel):
    """Схема для создания упражнения"""
    name: str = Field(..., min_length=1, max_length=100, description="Название упражнения")
    description: Optional[str] = Field(None, max_length=1000, description="Описание и техника выполнения")
    muscle_group: str = Field(..., min_length=1, max_length=50, description="Основная группа мышц")
    equipment: Optional[str] = Field(None, max_length=100, description="Необходимый инвентарь")
    difficulty: Optional[str] = Field(None, max_length=20, description="Сложность")
    video_url: Optional[HttpUrl] = Field(None, description="Ссылка на видео с демонстрацией упражнения")
    @field_validator('difficulty')
    def validate_difficulty(cls, v):
        if v is not None:
            allowed = ['beginner', 'intermediate', 'advanced']
            if v.lower() not in allowed:
                raise ValueError(f'Difficulty must be one of: {allowed}')
        return v
    

class ExerciseUpdate(BaseModel):
    """Схема для обновления упражнения (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    muscle_group: Optional[str] = Field(None, min_length=1, max_length=50)
    equipment: Optional[str] = Field(None, max_length=100)
    difficulty: Optional[str] = Field(None, max_length=20)
    video_url: Optional[HttpUrl] = None
    is_public: Optional[bool] = Field(None, description="Публичное ли упражнение")

    @field_validator('difficulty')
    def validate_difficulty(cls, v):
        if v is not None:
            allowed = ['beginner', 'intermediate', 'advanced']
            if v.lower() not in allowed:
                raise ValueError(f'Difficulty must be one of: {allowed}')
        return v



class ExerciseResponse(BaseModel):
    """Схема ответа с данными упражнения"""
    id: int
    name: str
    description: Optional[str] = None
    muscle_group: str
    equipment: Optional[str] = None
    difficulty: Optional[str] = None
    video_url: Optional[str] = None
    is_public: bool
    created_at: datetime
    updated_at: Optional[datetime] = None






# === Daily Template schemas ===





class DailyTemplateCreate(BaseModel):
    """Схема для создания пустого шаблона"""
    name: str = Field(..., min_length=1, max_length=100, description="Название шаблона")
    description: Optional[str] = Field(None, max_length=500, description="Описание")
    muscle_group: Optional[str] = Field(None, max_length=50, description="Целевая группа мышц")
    difficulty: Optional[str] = Field(None, max_length=20, description="Сложность")
    
    @field_validator('difficulty')
    @classmethod
    def validate_difficulty(cls, v):
        if v is not None:
            allowed = ['beginner', 'intermediate', 'advanced']
            if v.lower() not in allowed:
                raise ValueError(f'Difficulty must be one of: {allowed}')
        return v


class TemplateExerciseCreate(BaseModel):
    """Схема для добавления упражнения в шаблон (для будущего использования)"""
    exercise_id: int = Field(..., gt=0)
    sets: int = Field(..., ge=1, le=50)
    reps: str = Field(..., min_length=1, max_length=20)
    rest: Optional[int] = Field(None, ge=30, le=300)


class TemplateExerciseResponse(BaseModel):
    """Упражнение в шаблоне (для ответа)"""
    id: int
    exercise_id: int
    exercise_name: str
    muscle_group: str
    sets: int
    reps: str
    rest: Optional[int] = None
    
    class Config:
        from_attributes = True


class DailyTemplateResponse(BaseModel):
    """Схема ответа с данными шаблона"""
    id: int
    author_id: int
    name: str
    description: Optional[str] = None
    muscle_group: Optional[str] = None
    difficulty: Optional[str] = None
    exercises: List[Any] = []  # Список упражнений (пока пустой)
    created_at: datetime
    
    class Config:
        from_attributes = True

# === Monthly Template schemas ===
class MonthlyTemplateCreate(BaseModel):
    """Создание пустого месячного шаблона"""
    name: str = Field(..., min_length=1, max_length=100, description="Название плана")
    description: Optional[str] = Field(None, max_length=500, description="Описание")


class MonthlyTemplateDayAdd(BaseModel):
    """Добавление дня (только ID дневного шаблона)"""
    daily_template_id: int = Field(..., gt=0, description="ID дневного шаблона")


class MonthlyTemplateDayRemove(BaseModel):
    """Удаление дня из шаблона"""
    day_number: int = Field(..., ge=1, description="Номер дня")


class MonthlyTemplateResponse(BaseModel):
    """Ответ с данными месячного шаблона"""
    id: int
    author_id: int
    name: str
    description: Optional[str] = None
    days: Dict[str, int] = {}
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MonthlyTemplateListItem(BaseModel):
    """Ответ для списка шаблонов (без дней)"""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MonthlyTemplateDetailResponse(BaseModel):
    """Детальный ответ с подгрузкой дневных шаблонов"""
    id: int
    name: str
    description: Optional[str] = None
    days: List[Dict[str, Any]]  # Список дней с информацией о тренировках
    created_at: datetime
    updated_at: Optional[datetime] = None

# === Goal schemas ===
class GoalCreate(BaseModel):
    monthly_template_id: int = Field(..., gt=0)
    is_cycled: bool = False


class GoalResponse(BaseModel):
    id: int
    monthly_template_id: int
    template_name: Optional[str] = None
    is_cycled: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Optional[dict] = None  # будет добавлено в эндпоинте
    
    class Config:
        from_attributes = True


class GoalProgressResponse(BaseModel):
    total_days: int
    completed_days: int
    progress_percent: float
    remaining_days: int
    is_completed: bool
    completed_at: Optional[datetime] = None