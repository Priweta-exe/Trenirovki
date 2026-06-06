from fastapi import APIRouter, HTTPException, Depends, status
from typing import List

from databases import Database
from functions import (
    create_empty_monthly_template,
    get_monthly_template,
    get_user_monthly_templates,
    add_day_to_monthly_template,
    remove_last_day_from_monthly_template,
    delete_monthly_template,
    get_daily_template
)
from schemas import (
    MonthlyTemplateCreate,
    MonthlyTemplateResponse,
    MonthlyTemplateListItem,
    MonthlyTemplateDayAdd,
    MonthlyTemplateDetailResponse
)
from utils import get_current_user

workout_monthly_template_router = APIRouter(prefix="/monthly-templates", tags=["Месячные шаблоны"])


def get_db():
    return Database("test_2_1.db")


def validate_owner(template: dict, user_id: int):
    """Проверяет, что шаблон принадлежит пользователю"""
    if template['author_id'] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this template"
        )


# ========== ОСНОВНЫЕ ЭНДПОИНТЫ ==========

@workout_monthly_template_router.post(
    "/",
    response_model=MonthlyTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать пустой месячный шаблон"
)
def create_template(
    template_data: MonthlyTemplateCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Создаёт пустой месячный шаблон (без дней)"""
    
    template_id = create_empty_monthly_template(
        db,
        author_id=current_user['id'],
        name=template_data.name,
        description=template_data.description
    )
    
    if not template_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )
    
    return get_monthly_template(db, template_id)


@workout_monthly_template_router.get(
    "/",
    response_model=List[MonthlyTemplateListItem],
    summary="Получить все месячные шаблоны пользователя"
)
def get_my_templates(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Возвращает все месячные шаблоны текущего пользователя"""
    return get_user_monthly_templates(db, current_user['id'])


@workout_monthly_template_router.get(
    "/{template_id}",
    response_model=MonthlyTemplateResponse,
    summary="Получить месячный шаблон по ID"
)
def get_template(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Возвращает месячный шаблон со всеми днями"""
    
    template = get_monthly_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )
    
    validate_owner(template, current_user['id'])
    return template


@workout_monthly_template_router.post(
    "/{template_id}/days",
    response_model=MonthlyTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить день в конец шаблона"
)
def add_day(
    template_id: int,
    day_data: MonthlyTemplateDayAdd,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Добавляет новый день в конец шаблона.
    Номер дня присваивается автоматически (длина списка + 1).
    """
    
    template = get_monthly_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )
    
    validate_owner(template, current_user['id'])
    
    # Проверяем существование дневного шаблона
    daily_template = get_daily_template(db, day_data.daily_template_id)
    if not daily_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily template with id {day_data.daily_template_id} not found"
        )
    
    # Проверяем право на использование
    if daily_template['author_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to use this daily template"
        )
    
    # Добавляем день в конец
    success, new_day_number = add_day_to_monthly_template(
        db,
        template_id=template_id,
        daily_template_id=day_data.daily_template_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add day to template"
        )
    
    return get_monthly_template(db, template_id)


@workout_monthly_template_router.delete(
    "/{template_id}/days/last",
    response_model=MonthlyTemplateResponse,
    summary="Удалить последний день из шаблона"
)
def remove_last_day(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Удаляет последний добавленный день из шаблона.
    """
    
    template = get_monthly_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )
    
    validate_owner(template, current_user['id'])
    
    # Проверяем, есть ли дни для удаления
    if not template['days']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No days to remove from template"
        )
    
    # Удаляем последний день
    success, removed_day = remove_last_day_from_monthly_template(db, template_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove last day from template"
        )
    
    return get_monthly_template(db, template_id)


@workout_monthly_template_router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить месячный шаблон"
)
def delete_template(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Полностью удаляет месячный шаблон"""
    
    template = get_monthly_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )
    
    validate_owner(template, current_user['id'])
    
    success = delete_monthly_template(db, template_id, current_user['id'])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        )
    
    return None