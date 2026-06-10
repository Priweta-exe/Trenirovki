from fastapi import APIRouter, HTTPException, Depends, status
from typing import List

from database import Database
from dependencies import get_db
from schemas import GoalCreate, GoalResponse
from utils import get_current_user
from functions import (
    create_goal,
    get_goal,
    get_user_goals,
    get_active_goals,
    calculate_progress,
    build_progress,
    delete_goal,
    get_monthly_template,
)

goals_router = APIRouter(prefix="/goals", tags=["Цели"])


def validate_owner(goal: dict, user_id: int):
    if goal["user_id"] != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your goal")


# --- Статические роуты выше динамических ---

@goals_router.get(
    "/active",
    response_model=List[GoalResponse],
    summary="Активные цели",
)
def get_active(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Активные цели уже содержат template_name и total_days из JOIN.
    """
    goals = get_active_goals(db, current_user["id"])
    return [
        {**g, "progress": build_progress(g, g["total_days"])}
        for g in goals
    ]


@goals_router.get(
    "/",
    response_model=List[GoalResponse],
    summary="Все цели пользователя",
)
def get_all_goals(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    goals = get_user_goals(db, current_user["id"])
    return [
        {**g, "progress": build_progress(g, g["total_days"])}
        for g in goals
    ]


@goals_router.post(
    "/",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Начать новую цель",
)
def start_goal(
    data: GoalCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    template = get_monthly_template(db, data.monthly_template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    if template["author_id"] != current_user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your template")

    try:
        goal_id = create_goal(db, user_id=current_user["id"], monthly_template_id=data.monthly_template_id, is_cycled=data.is_cycled)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    goal = get_goal(db, goal_id)
    total_days = len(template["days"])
    return {**goal, "template_name": template["name"], "progress": build_progress(goal, total_days)}


# --- Динамические роуты ---

@goals_router.get(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Цель по ID",
)
def get_goal_by_id(
    goal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    goal = get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    validate_owner(goal, current_user["id"])

    template = get_monthly_template(db, goal["monthly_template_id"])
    total_days = len(template["days"]) if template else 0

    return {
        **goal,
        "template_name": template["name"] if template else None,
        "progress": build_progress(goal, total_days),
    }


@goals_router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить цель",
)
def remove_goal(
    goal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    goal = get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    validate_owner(goal, current_user["id"])

    if not delete_goal(db, goal_id, current_user["id"]):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete goal")
