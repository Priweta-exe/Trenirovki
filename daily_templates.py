from fastapi import APIRouter, HTTPException, Depends, status
from typing import List

from database import Database
from dependencies import get_db
from schemas import DailyTemplateCreate, DailyTemplateResponse, TemplateExerciseCreate
from utils import get_current_user
from functions import (
    create_empty_template,
    get_daily_template,
    get_user_templates,
    add_exercise_to_daily_template,
    delete_daily_template,
    get_exercise_by_id,
)

daily_templates_router = APIRouter(prefix="/daily-templates", tags=["Дневные шаблоны"])


def validate_template_owner(template: dict, user_id: int):
    if template["author_id"] != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your template")


@daily_templates_router.post(
    "/",
    response_model=DailyTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать шаблон",
)
def create_template(
    template_data: DailyTemplateCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template_id = create_empty_template(
        db,
        author_id=current_user["id"],
        name=template_data.name,
        description=template_data.description,
        muscle_group=template_data.muscle_group,
        difficulty=template_data.difficulty,
    )

    if not template_id:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create template")

    return get_daily_template(db, template_id)


@daily_templates_router.get(
    "/",
    response_model=List[DailyTemplateResponse],
    summary="Мои шаблоны",
)
def get_my_templates(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    return get_user_templates(db, current_user["id"])


@daily_templates_router.get(
    "/{template_id}",
    response_model=DailyTemplateResponse,
    summary="Шаблон по ID",
)
def get_template_by_id(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template = get_daily_template(db, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Template {template_id} not found")
    validate_template_owner(template, current_user["id"])
    return template


@daily_templates_router.post(
    "/{template_id}/exercises",
    response_model=DailyTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить упражнение в шаблон",
)
def add_exercise_to_template(
    template_id: int,
    exercise_data: TemplateExerciseCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template = get_daily_template(db, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    validate_template_owner(template, current_user["id"])

    exercise = get_exercise_by_id(db, exercise_data.exercise_id)
    if not exercise:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercise not found")

    # Одна операция вместо двух
    success = add_exercise_to_daily_template(
        db,
        template_id=template_id,
        exercise_id=exercise_data.exercise_id,
        sets=exercise_data.sets,
        reps=exercise_data.reps,
        rest=exercise_data.rest,
    )

    if not success:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to add exercise")

    return get_daily_template(db, template_id)


@daily_templates_router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить шаблон",
)
def delete_template(
    template_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template = get_daily_template(db, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Template {template_id} not found")
    validate_template_owner(template, current_user["id"])

    if not delete_daily_template(db, template_id, current_user["id"]):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete template")
