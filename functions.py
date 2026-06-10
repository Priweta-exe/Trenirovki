import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date

from database import Database

logger = logging.getLogger(__name__)


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def _update_json_field(
    db: Database,
    table: str,
    field: str,
    record_id: int,
    mutate_fn,
    extra_sets: str = ""
) -> bool:
    """
    Читает JSON-поле, применяет мутацию и сохраняет обратно.
    extra_sets — дополнительные SET-выражения, например 'updated_at = CURRENT_TIMESTAMP'
    """
    row = db.execute(
        f"SELECT {field} FROM {table} WHERE id = ?",
        (record_id,),
        fetch_one=True
    )
    if not row:
        return False

    data = json.loads(row[field])
    mutate_fn(data)

    set_clause = f"{field} = ?"
    if extra_sets:
        set_clause += f", {extra_sets}"

    db.execute(
        f"UPDATE {table} SET {set_clause} WHERE id = ?",
        (json.dumps(data, ensure_ascii=False), record_id)
    )
    return True


def build_progress(goal: dict, total_days: int) -> dict:
    """Строит словарь прогресса для цели."""
    if goal.get("completed_at"):
        return {
            "total_days": total_days,
            "completed_days": total_days,
            "progress_percent": 100.0,
            "remaining_days": 0,
            "is_completed": True,
        }
    return calculate_progress(goal["started_at"], total_days)


# ============================================
# 1. ПОЛЬЗОВАТЕЛИ
# ============================================

def create_user(db: Database, username: str, login: str, password_hash: str) -> Optional[int]:
    try:
        return db.execute(
            "INSERT INTO users (username, login, password_hash) VALUES (?, ?, ?)",
            (username, login, password_hash),
        )
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            logger.warning(f"Duplicate user: username={username}, login={login}")
        else:
            logger.error(f"create_user error: {e}")
        return None


def get_user_by_id(db: Database, user_id: int) -> Optional[Dict[str, Any]]:
    return db.execute(
        "SELECT id, username, login, created_at, last_login FROM users WHERE id = ?",
        (user_id,),
        fetch_one=True,
    )


def get_user_by_login(db: Database, login: str) -> Optional[Dict[str, Any]]:
    return db.execute(
        "SELECT id, username, login, password_hash, created_at FROM users WHERE login = ?",
        (login,),
        fetch_one=True,
    )


def get_user_by_username(db: Database, username: str) -> Optional[Dict[str, Any]]:
    return db.execute(
        "SELECT id, username, login, created_at FROM users WHERE username = ?",
        (username,),
        fetch_one=True,
    )


def update_last_login(db: Database, user_id: int) -> bool:
    rows = db.execute(
        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
        (user_id,),
    )
    return rows > 0


def delete_user(db: Database, user_id: int) -> bool:
    return db.execute("DELETE FROM users WHERE id = ?", (user_id,)) > 0


def update_user_profile(
    db: Database,
    user_id: int,
    username: Optional[str] = None,
    login: Optional[str] = None,
    password_hash: Optional[str] = None,
) -> bool:
    updates, params = [], []

    if username is not None:
        updates.append("username = ?")
        params.append(username)
    if login is not None:
        updates.append("login = ?")
        params.append(login)
    if password_hash is not None:
        updates.append("password_hash = ?")
        params.append(password_hash)

    if not updates:
        return True

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
    return db.execute(query, tuple(params)) > 0


# ============================================
# 2. УПРАЖНЕНИЯ
# ============================================

def create_exercise(
    db: Database,
    name: str,
    muscle_group: str,
    user_id: Optional[int] = None,
    description: Optional[str] = None,
    equipment: Optional[str] = None,
    difficulty: Optional[str] = None,
    video_url: Optional[str] = None,
    is_public: bool = False,
) -> Optional[int]:
    return db.execute(
        """
        INSERT INTO exercises
            (name, description, muscle_group, equipment, difficulty, video_url, user_id, is_public)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, description, muscle_group, equipment, difficulty, video_url, user_id, 1 if is_public else 0),
    )


def update_exercise(
    db: Database,
    exercise_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
    difficulty: Optional[str] = None,
    video_url: Optional[str] = None,
    is_public: Optional[bool] = None,
) -> bool:
    updates, params = [], []

    fields = {
        "name": name,
        "description": description,
        "muscle_group": muscle_group,
        "equipment": equipment,
        "difficulty": difficulty,
        "video_url": video_url,
    }
    for col, val in fields.items():
        if val is not None:
            updates.append(f"{col} = ?")
            params.append(val)

    if is_public is not None:
        updates.append("is_public = ?")
        params.append(1 if is_public else 0)

    if not updates:
        return True

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(exercise_id)
    return db.execute(f"UPDATE exercises SET {', '.join(updates)} WHERE id = ?", tuple(params)) > 0


def get_exercise_by_id(db: Database, exercise_id: int) -> Optional[Dict[str, Any]]:
    return db.execute(
        """
        SELECT id, name, description, muscle_group, equipment,
               difficulty, video_url, user_id, is_public, created_at, updated_at
        FROM exercises WHERE id = ?
        """,
        (exercise_id,),
        fetch_one=True,
    )


def get_available_exercises(
    db: Database,
    user_id: Optional[int] = None,
    muscle_group: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = """
        SELECT id, name, description, muscle_group, equipment,
               difficulty, video_url, is_public, user_id, created_at
        FROM exercises
        WHERE (is_public = 1 OR user_id = ?)
    """
    params = [user_id if user_id else 0]

    if muscle_group:
        query += " AND muscle_group = ?"
        params.append(muscle_group)
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)

    query += " ORDER BY muscle_group, name"
    return db.execute(query, tuple(params), fetch_all=True)


def get_user_exercises(db: Database, user_id: int) -> List[Dict[str, Any]]:
    """Только упражнения созданные пользователем (без публичных)."""
    return db.execute(
        """
        SELECT id, name, description, muscle_group, equipment,
               difficulty, video_url, is_public, user_id, created_at
        FROM exercises
        WHERE user_id = ?
        ORDER BY muscle_group, name
        """,
        (user_id,),
        fetch_all=True,
    )


def exercise_name_exists(db: Database, name: str, user_id: int, exclude_id: Optional[int] = None) -> bool:
    """Проверяет уникальность названия упражнения для пользователя одним запросом."""
    query = "SELECT id FROM exercises WHERE LOWER(name) = LOWER(?) AND (is_public = 1 OR user_id = ?)"
    params = [name, user_id]
    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)
    return db.execute(query, tuple(params), fetch_one=True) is not None


def delete_exercise(db: Database, exercise_id: int, user_id: int) -> bool:
    return db.execute(
        "DELETE FROM exercises WHERE id = ? AND user_id = ?",
        (exercise_id, user_id),
    ) > 0


# ============================================
# 3. ДНЕВНЫЕ ШАБЛОНЫ
# ============================================

def create_daily_template(
    db: Database,
    author_id: int,
    name: str,
    description: Optional[str] = None,
    muscle_group: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> Optional[int]:
    return db.execute(
        """
        INSERT INTO workout_daily_template
            (author_id, name, description, muscle_group, difficulty, exercises)
        VALUES (?, ?, ?, ?, ?, '[]')
        """,
        (author_id, name, description, muscle_group, difficulty),
    )

# Оставляем псевдоним для обратной совместимости с роутером
create_empty_template = create_daily_template


def get_daily_template(db: Database, template_id: int) -> Optional[Dict[str, Any]]:
    result = db.execute(
        """
        SELECT id, author_id, name, description, muscle_group, difficulty, exercises, created_at
        FROM workout_daily_template WHERE id = ?
        """,
        (template_id,),
        fetch_one=True,
    )
    if result:
        result["exercises"] = json.loads(result["exercises"])
    return result


def get_user_templates(db: Database, author_id: int) -> List[Dict[str, Any]]:
    results = db.execute(
        """
        SELECT id, author_id, name, description, muscle_group, difficulty, exercises, created_at
        FROM workout_daily_template WHERE author_id = ?
        ORDER BY created_at DESC
        """,
        (author_id,),
        fetch_all=True,
    )
    for t in results:
        t["exercises"] = json.loads(t["exercises"])
    return results


def add_exercise_to_daily_template(
    db: Database,
    template_id: int,
    exercise_id: int,
    sets: int,
    reps: str,
    rest: Optional[int] = None,
) -> bool:
    """Добавляет упражнение в конец шаблона через _update_json_field."""
    new_entry = {"exercise_id": exercise_id, "sets": sets, "reps": reps}
    if rest is not None:
        new_entry["rest"] = rest

    return _update_json_field(
        db,
        table="workout_daily_template",
        field="exercises",
        record_id=template_id,
        mutate_fn=lambda exercises: exercises.append(new_entry),
    )

# Псевдоним для обратной совместимости
update_daily_template = add_exercise_to_daily_template


def delete_daily_template(db: Database, template_id: int, user_id: int) -> bool:
    return db.execute(
        "DELETE FROM workout_daily_template WHERE id = ? AND author_id = ?",
        (template_id, user_id),
    ) > 0


# ============================================
# 4. МЕСЯЧНЫЕ ШАБЛОНЫ
# ============================================

def create_empty_monthly_template(
    db: Database,
    author_id: int,
    name: str,
    description: Optional[str] = None,
) -> Optional[int]:
    return db.execute(
        "INSERT INTO workout_monthly_template (author_id, name, description, days_json) VALUES (?, ?, ?, '{}')",
        (author_id, name, description),
    )


def get_monthly_template(db: Database, template_id: int) -> Optional[Dict[str, Any]]:
    result = db.execute(
        """
        SELECT id, author_id, name, description, days_json, created_at, updated_at
        FROM workout_monthly_template WHERE id = ?
        """,
        (template_id,),
        fetch_one=True,
    )
    if result:
        result["days"] = json.loads(result.pop("days_json"))
    return result


def get_user_monthly_templates(db: Database, author_id: int) -> List[Dict[str, Any]]:
    return db.execute(
        """
        SELECT id, name, description, created_at, updated_at
        FROM workout_monthly_template WHERE author_id = ?
        ORDER BY created_at DESC
        """,
        (author_id,),
        fetch_all=True,
    )


def add_day_to_monthly_template(
    db: Database, template_id: int, daily_template_id: int
) -> Tuple[bool, Optional[int]]:
    """Добавляет день в конец шаблона. Возвращает (success, new_day_number)."""
    new_day_number = None

    def mutate(days: dict):
        nonlocal new_day_number
        new_day_number = len(days) + 1
        days[str(new_day_number)] = daily_template_id

    success = _update_json_field(
        db,
        table="workout_monthly_template",
        field="days_json",
        record_id=template_id,
        mutate_fn=mutate,
        extra_sets="updated_at = CURRENT_TIMESTAMP",
    )
    return success, new_day_number


def remove_last_day_from_monthly_template(
    db: Database, template_id: int
) -> Tuple[bool, Optional[int]]:
    """Удаляет последний день. Возвращает (success, removed_day_number)."""
    removed_day = None

    def mutate(days: dict):
        nonlocal removed_day
        if not days:
            return
        max_key = str(max(int(k) for k in days))
        removed_day = int(max_key)
        del days[max_key]

    success = _update_json_field(
        db,
        table="workout_monthly_template",
        field="days_json",
        record_id=template_id,
        mutate_fn=mutate,
        extra_sets="updated_at = CURRENT_TIMESTAMP",
    )
    return success, removed_day


def delete_monthly_template(db: Database, template_id: int, author_id: int) -> bool:
    return db.execute(
        "DELETE FROM workout_monthly_template WHERE id = ? AND author_id = ?",
        (template_id, author_id),
    ) > 0


# ============================================
# 5. ЦЕЛИ
# ============================================

def get_total_days_in_template(db: Database, monthly_template_id: int) -> int:
    row = db.execute(
        "SELECT days_json FROM workout_monthly_template WHERE id = ?",
        (monthly_template_id,),
        fetch_one=True,
    )
    if not row:
        return 0
    return len(json.loads(row["days_json"]))


def calculate_progress(started_at: datetime, total_days: int) -> Dict[str, Any]:
    if total_days == 0:
        return {"completed_days": 0, "progress_percent": 0.0, "remaining_days": 0, "is_completed": False}

    if isinstance(started_at, str):
        started_at = datetime.fromisoformat(started_at)

    days_passed = (date.today() - started_at.date()).days

    completed = min(days_passed, total_days)
    is_completed = days_passed >= total_days

    return {
        "total_days": total_days,
        "completed_days": completed,
        "progress_percent": round((completed / total_days) * 100, 1),
        "remaining_days": total_days - completed,
        "is_completed": is_completed,
    }


def get_active_goals_count(db: Database, user_id: int) -> int:
    result = db.execute(
        "SELECT COUNT(*) as cnt FROM goals WHERE user_id = ? AND completed_at IS NULL",
        (user_id,),
        fetch_one=True,
    )
    return result["cnt"] if result else 0


def create_goal(
    db: Database,
    user_id: int,
    monthly_template_id: int,
    is_cycled: bool = False,
) -> Optional[int]:
    if get_active_goals_count(db, user_id) >= 3:
        raise ValueError("Maximum 3 active goals allowed")

    existing = db.execute(
        "SELECT id FROM goals WHERE user_id = ? AND monthly_template_id = ? AND completed_at IS NULL",
        (user_id, monthly_template_id),
        fetch_one=True,
    )
    if existing:
        raise ValueError("You already have an active goal for this template")

    return db.execute(
        "INSERT INTO goals (user_id, monthly_template_id, is_cycled) VALUES (?, ?, ?)",
        (user_id, monthly_template_id, 1 if is_cycled else 0),
    )


def get_goal(db: Database, goal_id: int) -> Optional[Dict[str, Any]]:
    return db.execute(
        "SELECT id, user_id, monthly_template_id, is_cycled, started_at, completed_at FROM goals WHERE id = ?",
        (goal_id,),
        fetch_one=True,
    )


def get_user_goals(db: Database, user_id: int) -> List[Dict[str, Any]]:
    """Все цели пользователя с именем шаблона и количеством дней (JOIN)."""
    return db.execute(
        """
        SELECT g.id, g.monthly_template_id, g.is_cycled, g.started_at, g.completed_at,
               m.name AS template_name,
               LENGTH(m.days_json) - LENGTH(REPLACE(m.days_json, ':', '')) AS total_days
        FROM goals g
        JOIN workout_monthly_template m ON g.monthly_template_id = m.id
        WHERE g.user_id = ?
        ORDER BY g.started_at DESC
        """,
        (user_id,),
        fetch_all=True,
    )


def get_active_goals(db: Database, user_id: int) -> List[Dict[str, Any]]:
    """Активные цели пользователя с именем шаблона и количеством дней (JOIN)."""
    return db.execute(
        """
        SELECT g.id, g.monthly_template_id, g.is_cycled, g.started_at,
               m.name AS template_name,
               LENGTH(m.days_json) - LENGTH(REPLACE(m.days_json, ':', '')) AS total_days
        FROM goals g
        JOIN workout_monthly_template m ON g.monthly_template_id = m.id
        WHERE g.user_id = ? AND g.completed_at IS NULL
        ORDER BY g.started_at ASC
        """,
        (user_id,),
        fetch_all=True,
    )


def delete_goal(db: Database, goal_id: int, user_id: int) -> bool:
    return db.execute(
        "DELETE FROM goals WHERE id = ? AND user_id = ?",
        (goal_id, user_id),
    ) > 0


def check_and_update_completed_goals(db: Database) -> int:
    """
    Проверяет все активные цели и завершает просроченные.
    Для цикличных — создаёт новую цель. Вызывается при старте приложения.
    """
    active = db.execute(
        """
        SELECT g.id, g.user_id, g.monthly_template_id, g.is_cycled, g.started_at,
               LENGTH(m.days_json) - LENGTH(REPLACE(m.days_json, ':', '')) AS total_days
        FROM goals g
        JOIN workout_monthly_template m ON g.monthly_template_id = m.id
        WHERE g.completed_at IS NULL
        """,
        fetch_all=True,
    )

    processed = 0
    for goal in active:
        started = datetime.fromisoformat(goal["started_at"])
        progress = calculate_progress(started, goal["total_days"])

        if progress["is_completed"]:
            db.execute(
                "UPDATE goals SET completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (goal["id"],),
            )
            if goal["is_cycled"] and get_active_goals_count(db, goal["user_id"]) < 3:
                create_goal(db, goal["user_id"], goal["monthly_template_id"], is_cycled=True)
            processed += 1

    logger.info(f"check_and_update_completed_goals: processed {processed} goals")
    return processed
