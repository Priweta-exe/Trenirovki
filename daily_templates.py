"""
routers/templates.py - Эндпоинты для работы с дневными шаблонами тренировок

Все эндпоинты требуют авторизации (шаблоны привязаны к пользователю)
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, List
from datetime import datetime

from databases import Database
from functions import *
from schemas import *
from utils import get_current_user

# Создаём роутер
daily_templates_router = APIRouter(prefix="/daily-templates", tags=["Дневные шаблоны"])


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_db():
    """Зависимость для получения подключения к БД"""
    return Database("test_2_1.db")


def validate_template_owner(template: dict, current_author_id: int):
    """Проверяет, что шаблон принадлежит текущему пользователю"""
    if template['author_id'] != current_author_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this template"
        )


# ============================================
# ОСНОВНЫЕ ЭНДПОИНТЫ
# ============================================

@daily_templates_router.post(
    "/",
    response_model=DailyTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать пустой шаблон",
    description="Создаёт новый пустой шаблон тренировки"
)
def create_empty_template_endpoint(
    template_data: DailyTemplateCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Создать пустой шаблон тренировки.
    
    - **name**: название шаблона (обязательно)
    - **description**: описание (опционально)
    - **muscle_group**: целевая группа мышц (опционально)
    - **difficulty**: сложность (beginner/intermediate/advanced)
    """
    
    # Создаём пустой шаблон
    template_id = create_empty_template(
        db,
        author_id=current_user['id'],
        name=template_data.name,
        description=template_data.description,
        muscle_group=template_data.muscle_group,
        difficulty=template_data.difficulty
    )
    
    if not template_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )
    
    # Получаем и возвращаем созданный шаблон
    template = get_daily_template(db, template_id)
    return template




@daily_templates_router.get(
    "/",
    response_model=List[DailyTemplateResponse],
    summary="Получить все шаблоны пользователя"
)
def get_my_templates(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Возвращает все шаблоны текущего пользователя"""
    templates = get_user_templates(db, current_user['id'])
    return templates


@daily_templates_router.get(
    "/{template_id}",
    response_model=DailyTemplateResponse,
    summary="Получить шаблон по ID"
)
def get_template_by_id(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Возвращает подробную информацию о шаблоне"""
    
    template = get_daily_template(db, template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )
    
    # Проверяем, что шаблон принадлежит пользователю
    if template['author_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this template"
        )
    
    return template




@daily_templates_router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить шаблон"
)
def delete_template(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Удаляет шаблон тренировки"""
    
    template = get_daily_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )
    
    validate_template_owner(template, current_user['id'])
    
    success = delete_daily_template(db, template_id, current_user['id'])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        )
    
    return None





# ============================================
# ЭНДПОИНТЫ ДЛЯ УПРАЖНЕНИЙ В ШАБЛОНЕ
# ============================================

@daily_templates_router.post("/{template_id}/exercises")
def add_exercise_to_template(
    template_id: int,
    exercise_data: TemplateExerciseCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Добавляет упражнение в конец шаблона"""
    
    # Проверяем существование шаблона и права
    template = get_daily_template(db, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    
    if template['author_id'] != current_user['id']:
        raise HTTPException(403, "Not your template")
    
    # Проверяем существование упражнения
    exercise = get_exercise_by_id(db, exercise_data.exercise_id)
    if not exercise:
        raise HTTPException(404, "Exercise not found")
    
    # Добавляем в конец списка
    exercises = template['exercises']
    exercises.append({
        "exercise_id": exercise_data.exercise_id,
        "sets": exercise_data.sets,
        "reps": exercise_data.reps,
        "rest": exercise_data.rest
    })
    
    # Обновляем шаблон
    update_daily_template(db, template_id, exercise_data.exercise_id, exercise_data.sets, exercise_data.reps, exercise_data.rest)
    
    return get_daily_template(db, template_id)


