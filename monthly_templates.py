from fastapi import APIRouter, HTTPException, Depends, status
from typing import List

from database import Database
from dependencies import get_db
from schemas import (
    MonthlyTemplateCreate,
    MonthlyTemplateResponse,
    MonthlyTemplateListItem,
    MonthlyTemplateDayAdd,
)
from utils import get_current_user
from functions import (
    create_empty_monthly_template,
    get_monthly_template,
    get_user_monthly_templates,
    add_day_to_monthly_template,
    remove_last_day_from_monthly_template,
    delete_monthly_template,
    get_daily_template,
)

workout_monthly_template_router = APIRouter(prefix="/monthly-templates", tags=["Месячные шаблоны"])


def validate_owner(template: dict, user_id: int):
    if template["author_id"] != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your template")


@workout_monthly_template_router.post(
    "/",
    response_model=MonthlyTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать месячный шаблон",
)
def create_template(
    template_data: MonthlyTemplateCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template_id = create_empty_monthly_template(
        db,
        author_id=current_user["id"],
        name=template_data.name,
        description=template_data.description,
    )

    if not template_id:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create template")

    return get_monthly_template(db, template_id)


@workout_monthly_template_router.get(
    "/",
    response_model=List[MonthlyTemplateListItem],
    summary="Мои месячные шаблоны",
)
def get_my_templates(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    return get_user_monthly_templates(db, current_user["id"])


@workout_monthly_template_router.get(
    "/{template_id}",
    response_model=MonthlyTemplateResponse,
    summary="Месячный шаблон по ID",
)
def get_template(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template = get_monthly_template(db, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Template {template_id} not found")
    validate_owner(template, current_user["id"])
    return template


@workout_monthly_template_router.post(
    "/{template_id}/days",
    response_model=MonthlyTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить день в шаблон",
)
def add_day(
    template_id: int,
    day_data: MonthlyTemplateDayAdd,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template = get_monthly_template(db, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Template {template_id} not found")
    validate_owner(template, current_user["id"])

    daily = get_daily_template(db, day_data.daily_template_id)
    if not daily:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Daily template {day_data.daily_template_id} not found")

    # Разрешаем использовать свои и публичные дневные шаблоны
    if daily["author_id"] != current_user["id"] and not daily.get("is_public"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have permission to use this daily template")

    success, _ = add_day_to_monthly_template(db, template_id=template_id, daily_template_id=day_data.daily_template_id)

    if not success:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to add day")

    return get_monthly_template(db, template_id)


@workout_monthly_template_router.delete(
    "/{template_id}/days/last",
    response_model=MonthlyTemplateResponse,
    summary="Удалить последний день",
)
def remove_last_day(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template = get_monthly_template(db, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Template {template_id} not found")
    validate_owner(template, current_user["id"])

    if not template["days"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No days to remove")

    success, _ = remove_last_day_from_monthly_template(db, template_id)
    if not success:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to remove day")

    return get_monthly_template(db, template_id)


@workout_monthly_template_router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить месячный шаблон",
)
def delete_template(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template = get_monthly_template(db, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Template {template_id} not found")
    validate_owner(template, current_user["id"])

    if not delete_monthly_template(db, template_id, current_user["id"]):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete template")
