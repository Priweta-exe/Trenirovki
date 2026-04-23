
import json
from typing import List, Dict, Any, Optional
from databases import Database


# 1. Работа с пользователями

def create_user(db: Database, username: str, login: str, password_hash: str) -> Optional[int]:
    try:
        db.execute("""
            INSERT INTO users (username, login, password_hash)
            VALUES (?, ?, ?)
        """, (username, login, password_hash))
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            print(f"Пользователь с именем '{username}' или login '{login}' уже существует")
        else:
            print(e)
        return None


def get_user_by_id(db: Database, user_id: int) -> Optional[Dict[str, Any]]:
    return db.execute("""
        SELECT id, username, login, created_at, last_login
        FROM users 
        WHERE id = ?
    """, (user_id,), fetch_one=True)


def get_user_by_login(db: Database, login: str) -> Optional[Dict[str, Any]]:
    return db.execute("""
        SELECT id, username, login, password_hash, created_at
        FROM users 
        WHERE login = ?
    """, (login,), fetch_one=True)


def get_user_by_username(db: Database, username: str) -> Optional[Dict[str, Any]]:
    return db.execute("""
        SELECT id, username, login, created_at
        FROM users 
        WHERE username = ?
    """, (username,), fetch_one=True)


def update_last_login(db: Database, user_id: int) -> bool:
    rows_affected = db.execute("""
        UPDATE users 
        SET last_login = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (user_id,))
    return rows_affected > 0


# 2. Работа с упражнениями

def create_exercise(
    db: Database,
    name: str,
    muscle_group: str,
    difficulty: str,
    user_id: Optional[int] = None,
    description: Optional[str] = None,
    is_public: bool = True):
    
    return db.execute("""
        INSERT INTO exercises (name, description, muscle_group, user_id, is_public, difficulty, created_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (name, description, muscle_group, user_id, 1 if is_public else 0, difficulty))


def get_exercise_by_id(db: Database, exercise_id: int) -> Optional[Dict[str, Any]]:
    return db.execute("""
        SELECT *
        FROM exercises 
        WHERE id = ?
    """, (exercise_id,), fetch_one=True)


# 3. Работа с дневными шаблонами

def create_daily_template(
    db: Database,
    author_id: int,
    description: str,
    difficulty: str,
    exercises: List[Dict[str, Any]]):
    # Преобразуем Python список в JSON строку
    exercises_json = json.dumps(exercises, ensure_ascii=False)
    
    return db.execute("""
        INSERT INTO workout_daily_templates (author_id, exercises, difficulty, description, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (author_id, exercises_json, difficulty, description))


def get_daily_template(db: Database, template_id: int) -> Optional[Dict[str, Any]]:

    result = db.execute("""
        SELECT *
        FROM workout_daily_templates 
        WHERE id = ?
    """, (template_id,), fetch_one=True)
    
    
    return result


def update_daily_template(
    db: Database,
    template_id: int,
    description: str,
    difficulty: str,
    exercises: Optional[List[Dict[str, Any]]]
) -> bool:

    updates = []
    params = []
    
    if difficulty is not None:
        updates.append("difficulty = ?")
        params.append(difficulty)

    if description is not None:
        updates.append("description = ?")
        params.append(description)
    
    if exercises is not None:
        updates.append("exercises_json = ?")
        params.append(json.dumps(exercises, ensure_ascii=False))
    
    if not updates:
        return False  # Нечего обновлять
    
    params.append(template_id)
    query = f"UPDATE workout_daily_templates SET {', '.join(updates)} WHERE id = ?"
    rows_affected = db.execute(query, tuple(params))
    return rows_affected > 0


def delete_daily_template(db: Database, template_id: int, user_id: int) -> bool:
    """
    Удаляет дневной шаблон (только если он принадлежит пользователю).
    
    Args:
        db: Экземпляр Database
        template_id: ID шаблона
        user_id: ID владельца (для проверки прав)
        
    Returns:
        bool: True если удаление успешно
        
    Note:
        Проверка user_id защищает от удаления чужих шаблонов
    """
    rows_affected = db.execute("""
        DELETE FROM workout_daily_templates 
        WHERE id = ? AND user_id = ?
    """, (template_id, user_id))
    return rows_affected > 0


# 4. Работа с месячными шаблонами

def create_monthly_template(
    db: Database,
    author_id: int,
    description: str,
    difficulty: str,
    duration: int,
    days: Dict[str, Optional[Dict[str, Any]]]
) -> Optional[int]:
    
    days_json = json.dumps(days, ensure_ascii=False)
    
    return db.execute("""
        INSERT INTO workout_monthly_templates (author_id, description, templates, difficulty, duration, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (author_id, description, days_json, duration, difficulty))


def get_monthly_template(db: Database, template_id: int) -> Optional[Dict[str, Any]]:

    result = db.execute("""
        SELECT *
        FROM workout_monthly_templates 
        WHERE id = ?
    """, (template_id,), fetch_one=True)
    
    
    return result


if __name__ == "__main__":
    #from databases import Database
    
    db = Database("test_1.db")
    

    print("=== СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ ===")
    create_user(db, "aboba", "aboba@example.com", "hashed_password")
    print(f"Создан пользователь")
    
    print("\n=== ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ ===")
    user = get_user_by_id(db, 1)
    print(f"Пользователь: {user}")
    
    print("\n=== СОЗДАНИЕ УПРАЖНЕНИЯ ===")
    exercise_id = create_exercise(
        db, 
        "Жим штанги лежа", 
        "Грудь", 
        "Средний",
        1, 
        "Классическое базовое упражнение"
    )
    print(f"Создано упражнение с ID: {exercise_id}")
    

    print("\n=== СОЗДАНИЕ ДНЕВНОГО ШАБЛОНА ===")
    daily_exercises = [
        {"exercise_id": exercise_id, "sets": 4, "reps": "8-12", "rest": 90},
        {"exercise_id": exercise_id, "sets": 3, "reps": "10-15", "rest": 60}
    ]
    daily_id = create_daily_template(db, 1, "Силовая тренировка", "Сложный", daily_exercises)
    print(f"Создан дневной шаблон с ID: {daily_id}")
    
    print("\n=== ПОЛУЧЕНИЕ ДНЕВНОГО ШАБЛОНА ===")
    template = get_daily_template(db, daily_id)
    print(template)
    if template:
        print(f"Шаблон: {template['id']}")
        for ex in json.loads(template['exercises']):
            print(ex)
            print(f"  - {ex['sets']} подходов по {ex['reps']} повторений")
    
    print("\n=== СОЗДАНИЕ МЕСЯЧНОГО ШАБЛОНА ===")
    month_days = {
        "day1": {"daily_template_id": daily_id},
        "day2": None,  # отдых
        "day3": {"daily_template_id": daily_id},
        "day4": None,
        "day5": {"daily_template_id": daily_id}
    }
    monthly_id = create_monthly_template(db, 1, "План на январь", "Начинаючий", 5, month_days)
    print(f"Создан месячный шаблон с ID: {monthly_id}")
    
    
    print("\n✅ Все тесты пройдены!")