from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional

from database import Database
from dependencies import get_db
from schemas import ExerciseCreate, ExerciseResponse, ExerciseUpdate
from utils import get_current_user
from functions import (
    create_exercise,
    get_exercise_by_id,
    get_available_exercises,
    get_user_exercises,
    update_exercise,
    delete_exercise,
    exercise_name_exists,
)

exercises_router = APIRouter(prefix="/exercises", tags=["Упражнения"])


# --- Статические роуты выше динамических ---

@exercises_router.get(
    "/my",
    response_model=List[ExerciseResponse],
    summary="Мои упражнения",
)
def get_my_exercises(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Все упражнения созданные текущим пользователем."""
    return get_user_exercises(db, current_user["id"])


@exercises_router.get(
    "/public",
    response_model=List[ExerciseResponse],
    summary="Публичные упражнения",
)
def get_public_exercises(
    muscle_group: Optional[str] = None,
    search: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Database = Depends(get_db),
):
    exercises = get_available_exercises(db, user_id=None, muscle_group=muscle_group, difficulty=difficulty)
    if search:
        search_lower = search.lower()
        exercises = [e for e in exercises if search_lower in e["name"].lower()]
    return exercises


# --- Динамические роуты ---

@exercises_router.post(
    "/",
    response_model=ExerciseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать упражнение",
)
def create_new_exercise(
    exercise_data: ExerciseCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    if exercise_name_exists(db, exercise_data.name, current_user["id"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Exercise '{exercise_data.name}' already exists")

    exercise_id = create_exercise(
        db,
        name=exercise_data.name,
        description=exercise_data.description,
        muscle_group=exercise_data.muscle_group,
        equipment=exercise_data.equipment,
        difficulty=exercise_data.difficulty,
        video_url=str(exercise_data.video_url) if exercise_data.video_url else None,
        user_id=current_user["id"],
        is_public=False,
    )

    if not exercise_id:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create exercise")

    return get_exercise_by_id(db, exercise_id)


@exercises_router.get(
    "/{exercise_id}",
    response_model=ExerciseResponse,
    summary="Упражнение по ID",
)
def get_exercise(exercise_id: int, db: Database = Depends(get_db)):
    exercise = get_exercise_by_id(db, exercise_id)
    if not exercise or not exercise["is_public"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Exercise {exercise_id} not found")
    return exercise


@exercises_router.patch(
    "/{exercise_id}",
    response_model=ExerciseResponse,
    summary="Обновить упражнение",
)
def update_exercise_endpoint(
    exercise_id: int,
    update_data: ExerciseUpdate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    exercise = get_exercise_by_id(db, exercise_id)
    if not exercise:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Exercise {exercise_id} not found")
    if exercise["user_id"] != current_user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your exercise")

    if update_data.name and exercise_name_exists(db, update_data.name, current_user["id"], exclude_id=exercise_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Exercise '{update_data.name}' already exists")

    success = update_exercise(
        db,
        exercise_id=exercise_id,
        name=update_data.name,
        description=update_data.description,
        muscle_group=update_data.muscle_group,
        equipment=update_data.equipment,
        difficulty=update_data.difficulty,
        video_url=str(update_data.video_url) if update_data.video_url else None,
        is_public=update_data.is_public,
    )

    if not success:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update exercise")

    return get_exercise_by_id(db, exercise_id)


@exercises_router.delete(
    "/{exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить упражнение",
)
def delete_exercise_endpoint(
    exercise_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    exercise = get_exercise_by_id(db, exercise_id)
    if not exercise:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Exercise {exercise_id} not found")
    if exercise["user_id"] != current_user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your exercise")

    if not delete_exercise(db, exercise_id, current_user["id"]):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete exercise")
