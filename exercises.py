from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, List

from databases import Database
from functions import *
from schemas import (
    ExerciseCreate,
    ExerciseResponse,
    ExerciseUpdate
)
from utils import get_current_user

# Создаём роутер с префиксом /exercises и тегом для документации
exercises_router = APIRouter(prefix="/exercises", tags=["Упражнения"])



def get_db():
    db = Database("test_2_1.db")
    try:
        yield db
    finally:
        pass







@exercises_router.post(
    "/",
    response_model=ExerciseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новое упражнение",
    description="Создаёт новое упражнение (личное, доступно только автору)"
)
def create_new_exercise(
    exercise_data: ExerciseCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Создать новое упражнение.
    
    - **name**: название упражнения (обязательно)
    - **muscle_group**: группа мышц (обязательно)
    - **description**: описание (опционально)
    - **equipment**: необходимый инвентарь (опционально)
    - **difficulty**: сложность (beginner/intermediate/advanced)
    - **video_url**: ссылка на видео (опционально)
    """
    
    # Проверяем, не существует ли упражнение с таким названием у пользователя
    existing_exercises = get_available_exercises(db, current_user['id'])
    for ex in existing_exercises:
        if ex['name'].lower() == exercise_data.name.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exercise '{exercise_data.name}' already exists"
            )
    
    # Создаём упражнение
    exercise_id = create_exercise(
        db,
        name=exercise_data.name,
        description=exercise_data.description,
        muscle_group=exercise_data.muscle_group,
        equipment=exercise_data.equipment,
        difficulty=exercise_data.difficulty,
        video_url=str(exercise_data.video_url) if exercise_data.video_url else None,
        user_id=current_user['id'],
        is_public=False
    )
    
    if not exercise_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create exercise"
        )
    
    # Возвращаем созданное упражнение
    exercise = get_exercise_by_id(db, exercise_id)
    return exercise


# Обновите update_exercise_endpoint

@exercises_router.put(
    "/{exercise_id}",
    response_model=ExerciseResponse,
    summary="Обновить упражнение",
    description="Обновляет информацию об упражнении (только для владельца)"
)
def update_exercise_endpoint(
    exercise_id: int,
    update_data: ExerciseUpdate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Обновить существующее упражнение.
    
    Можно обновить:
    - **name**: новое название
    - **description**: новое описание
    - **muscle_group**: новая группа мышц
    - **equipment**: новый инвентарь
    - **difficulty**: новая сложность
    - **video_url**: новая ссылка на видео
    """
    
    # Проверяем, существует ли упражнение
    exercise = get_exercise_by_id(db, exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with id {exercise_id} not found"
        )
    
    # Проверяем права (только владелец может редактировать)
    if exercise['user_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this exercise"
        )
    
    # Проверяем, не занято ли новое название (если меняется)
    if update_data.name:
        existing = get_available_exercises(db, current_user['id'])
        for ex in existing:
            if ex['name'].lower() == update_data.name.lower() and ex['id'] != exercise_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Exercise '{update_data.name}' already exists"
                )
    
    # Обновляем упражнение
    success = update_exercise(
        db,
        exercise_id=exercise_id,
        name=update_data.name,
        description=update_data.description,
        muscle_group=update_data.muscle_group,
        equipment=update_data.equipment,
        difficulty=update_data.difficulty,
        video_url=str(update_data.video_url) if update_data.video_url else None,
        is_public=update_data.is_public
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update exercise"
        )
    
    # Возвращаем обновлённое упражнение
    updated_exercise = get_exercise_by_id(db, exercise_id)
    return updated_exercise


# Добавьте новый эндпоинт для фильтрации по сложности

@exercises_router.get(
    "/by-difficulty/{difficulty_level}",
    response_model=List[ExerciseResponse],
    summary="Получить упражнения по сложности",
    description="Возвращает упражнения с указанным уровнем сложности"
)
def get_exercises_by_difficulty(
    difficulty_level: str,
    db: Database = Depends(get_db)
):
    """
    Получить упражнения по уровню сложности.
    
    - **beginner**: для начинающих
    - **intermediate**: средний уровень
    - **advanced**: продвинутый уровень
    """
    allowed = ['beginner', 'intermediate', 'advanced']
    if difficulty_level.lower() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Difficulty must be one of: {allowed}"
        )
    
    exercises = get_available_exercises(db, user_id=None, difficulty=difficulty_level)
    return exercises


@exercises_router.get(
    "/{exercise_id}",
    response_model=ExerciseResponse,
    summary="Получить упражнение по ID",
    description="Возвращает подробную информацию об упражнении"
)
def get_exercise(
    exercise_id: int,
    db: Database = Depends(get_db)
):
    """
    Получить упражнение по его ID.
    
    Доступно без авторизации (публичные упражнения).
    """
    exercise = get_exercise_by_id(db, exercise_id)
    
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with id {exercise_id} not found"
        )
    
    # Если упражнение приватное и не принадлежит текущему пользователю,
    # но мы не знаем пользователя (нет авторизации) - не показываем
    if not exercise['is_public']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with id {exercise_id} not found"
        )
    
    return exercise


@exercises_router.delete(
    "/{exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить упражнение",
    description="Удаляет упражнение (только для владельца)"
)
def delete_exercise_endpoint(
    exercise_id: int,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Удалить упражнение.
    """
    
    # Проверяем, существует ли упражнение
    exercise = get_exercise_by_id(db, exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with id {exercise_id} not found"
        )
    
    # Проверяем права (только владелец может удалить)
    if exercise['user_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this exercise"
        )
    
    # Удаляем упражнение
    success = delete_exercise(db, exercise_id, current_user['id'])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete exercise"
        )
    
    # Возвращаем 204 No Content (без тела ответа)
    return None

@exercises_router.get(
    "/user/my",
    response_model=List[ExerciseResponse],
    summary="Получить мои упражнения",
    description="Возвращает все упражнения, созданные текущим пользователем"
)
def get_my_exercises(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Получить все личные упражнения текущего пользователя.
    
    Включает только упражнения, созданные пользователем.
    """
    exercises = get_available_exercises(db, current_user['id'])
    
    # Фильтруем только личные упражнения пользователя
    my_exercises = [e for e in exercises if e.get('user_id') == current_user['id']]
    
    return my_exercises


@exercises_router.get(
    "/public/all",
    response_model=List[ExerciseResponse],
    summary="Получить все публичные упражнения",
    description="Возвращает все публичные упражнения (созданные системой или другими пользователями)"
)
def get_public_exercises(
    muscle_group: Optional[str] = None,
    search: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """
    Получить все публичные упражнения.
    
    Доступно без авторизации.
    """
    exercises = get_available_exercises(db, user_id=None)
    
    if muscle_group:
        exercises = [e for e in exercises if e['muscle_group'] == muscle_group]
    
    if search:
        search_lower = search.lower()
        exercises = [e for e in exercises if search_lower in e['name'].lower()]
    
    return exercises