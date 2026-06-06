from fastapi import APIRouter, HTTPException, Depends, status
from typing import List

from databases import Database
from functions import (
    create_goal, get_goal, get_user_goals, get_active_goals,
    get_total_days_in_template, calculate_progress,
    delete_goal, check_and_update_completed_goals,
    get_monthly_template
)
from schemas import GoalCreate, GoalResponse, GoalProgressResponse
from utils import get_current_user

goals_router = APIRouter(prefix="/goals", tags=["Цели"])

def get_db():
    return Database("test_2_1.db")

def validate_owner(goal: dict, user_id: int):
    if goal['user_id'] != user_id:
        raise HTTPException(403, "Not your goal")


@goals_router.post("/", response_model=GoalResponse, status_code=201)
def start_goal(
    data: GoalCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Начинает новую цель (максимум 3 активных одновременно)"""
    # Проверяем, существует ли шаблон
    template = get_monthly_template(db, data.monthly_template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    if template['author_id'] != current_user['id']:
        raise HTTPException(403, "Not your template")
    
    try:
        goal_id = create_goal(
            db,
            user_id=current_user['id'],
            monthly_template_id=data.monthly_template_id,
            is_cycled=data.is_cycled
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    goal = get_goal(db, goal_id)
    goal['template_name'] = template['name']
    total_days = get_total_days_in_template(db, goal['monthly_template_id'])
    progress = calculate_progress(goal['started_at'], total_days)
    goal['progress'] = progress
    
    return goal


@goals_router.get("/active", response_model=List[GoalResponse])
def get_active(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Список активных целей (незавершённых)"""
    goals = get_active_goals(db, current_user['id'])
    result = []
    for g in goals:
        template = get_monthly_template(db, g['monthly_template_id'])
        total = get_total_days_in_template(db, g['monthly_template_id'])
        progress = calculate_progress(g['started_at'], total)
        result.append({
            **g,
            'template_name': template['name'] if template else None,
            'progress': progress
        })
    return result


@goals_router.get("/", response_model=List[GoalResponse])
def get_all_goals(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Все цели пользователя (активные и завершённые)"""
    goals = get_user_goals(db, current_user['id'])
    result = []
    for g in goals:
        template = get_monthly_template(db, g['monthly_template_id'])
        # Для завершённых целей прогресс 100% всегда
        if g['completed_at']:
            progress = {
                "total_days": get_total_days_in_template(db, g['monthly_template_id']),
                "completed_days": get_total_days_in_template(db, g['monthly_template_id']),
                "progress_percent": 100.0,
                "remaining_days": 0,
                "is_completed": True,
                "completed_at": g['completed_at']
            }
        else:
            total = get_total_days_in_template(db, g['monthly_template_id'])
            progress = calculate_progress(g['started_at'], total)
        result.append({
            **g,
            'template_name': template['name'] if template else None,
            'progress': progress
        })
    return result


@goals_router.get("/{goal_id}", response_model=GoalResponse)
def get_goal_by_id(
    goal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    goal = get_goal(db, goal_id)
    if not goal:
        raise HTTPException(404, "Goal not found")
    validate_owner(goal, current_user['id'])
    
    template = get_monthly_template(db, goal['monthly_template_id'])
    total = get_total_days_in_template(db, goal['monthly_template_id'])
    if goal['completed_at']:
        progress = {
            "total_days": total,
            "completed_days": total,
            "progress_percent": 100.0,
            "remaining_days": 0,
            "is_completed": True,
            "completed_at": goal['completed_at']
        }
    else:
        progress = calculate_progress(goal['started_at'], total)
    
    return {
        **goal,
        'template_name': template['name'] if template else None,
        'progress': progress
    }


@goals_router.delete("/{goal_id}", status_code=204)
def remove_goal(
    goal_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    goal = get_goal(db, goal_id)
    if not goal:
        raise HTTPException(404, "Goal not found")
    validate_owner(goal, current_user['id'])
    
    if not delete_goal(db, goal_id, current_user['id']):
        raise HTTPException(500, "Failed to delete goal")
    return None


# Опционально: эндпоинт для принудительного обновления завершённых целей
@goals_router.post("/check-completed")
def check_completed(
    db: Database = Depends(get_db)
):
    """Запускает проверку и перезапуск цикличных целей (можно вызывать раз в сутки)"""
    processed = check_and_update_completed_goals(db)
    return {"processed": processed}