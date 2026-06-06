
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from databases import Database


# 1. Работа с пользователями

def create_user(db: Database, username: str, login: str, password_hash: str) -> Optional[int]:
    try:
        db.execute("""
            INSERT INTO users (username, login, password_hash, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (username, login, password_hash))
        print('User created')
        return True
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

def delete_user(db: Database, user_id: int) -> bool:
    rows_affected = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return rows_affected > 0


def update_user_profile(
    db: Database, 
    user_id: int, 
    username: Optional[str] = None,
    login: Optional[str] = None,
    password_hash: Optional[str] = None) -> bool:
    updates = []
    params = []
    
    if username is not None:
        updates.append("username = ?")
        params.append(username)
    
    if login is not None:
        updates.append("login = ?")
        params.append(login)
    
    if password_hash is not None:
        updates.append("password_hash = ?")
        params.append(password_hash)
    
    updates.append("updated_at = CURRENT_TIMESTAMP")

    if not updates:
        return True  # Нечего обновлять
    
    params.append(user_id)
    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
    rows_affected = db.execute(query, tuple(params))
    return rows_affected > 0

# 2. Работа с упражнениями

def create_exercise(
    db: Database,
    name: str,
    muscle_group: str,
    user_id: Optional[int] = None,
    description: Optional[str] = None,
    equipment: Optional[str] = None,
    difficulty: Optional[str] = None,
    video_url: Optional[str] = None,
    is_public: bool = False
) -> Optional[int]:
    return db.execute("""
        INSERT INTO exercises (
            name, description, muscle_group, equipment, 
            difficulty, video_url, user_id, is_public, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        name, description, muscle_group, equipment,
        difficulty, video_url, user_id, 1 if is_public else 0
    ))



def update_exercise(
    db: Database,
    exercise_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
    difficulty: Optional[str] = None,
    video_url: Optional[str] = None,
    is_public: Optional[bool] = None
) -> bool:
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    
    if muscle_group is not None:
        updates.append("muscle_group = ?")
        params.append(muscle_group)
    
    if equipment is not None:
        updates.append("equipment = ?")
        params.append(equipment)
    
    if difficulty is not None:
        updates.append("difficulty = ?")
        params.append(difficulty)
    
    if video_url is not None:
        updates.append("video_url = ?")
        params.append(video_url)
    
    if is_public is not None:
        updates.append("is_public = ?")
        params.append(1 if is_public else 0)
    
    # Всегда обновляем updated_at
    updates.append("updated_at = CURRENT_TIMESTAMP")
    
    if not updates:
        return True  # Нечего обновлять
    
    params.append(exercise_id)
    query = f"UPDATE exercises SET {', '.join(updates)} WHERE id = ?"
    rows_affected = db.execute(query, tuple(params))
    return rows_affected > 0


def get_exercise_by_id(db: Database, exercise_id: int) -> Optional[Dict[str, Any]]:
    """Получает упражнение по ID со всеми полями"""
    return db.execute("""
        SELECT 
            id, name, description, muscle_group, equipment,
            difficulty, video_url, user_id, is_public, 
            created_at, updated_at
        FROM exercises 
        WHERE id = ?
    """, (exercise_id,), fetch_one=True)


def get_available_exercises(
    db: Database, 
    user_id: Optional[int] = None,
    muscle_group: Optional[str] = None,
    difficulty: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Получает все упражнения, доступные пользователю.
    """
    query = """
        SELECT 
            id, name, description, muscle_group, equipment,
            difficulty, video_url, is_public, created_at
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


def delete_exercise(db: Database, exercise_id: int, user_id: int) -> bool:
    """Удаляет упражнение (проверяет, что оно принадлежит пользователю)"""
    rows_affected = db.execute("""
        DELETE FROM exercises 
        WHERE id = ? AND user_id = ?
    """, (exercise_id, user_id))
    return rows_affected > 0

# 3. Работа с дневными шаблонами

def create_empty_template(
    db: Database,
    author_id: int,
    name: str,
    description: Optional[str] = None,
    muscle_group: Optional[str] = None,
    difficulty: Optional[str] = None
) -> Optional[int]:
    # Пустой JSON список для упражнений
    empty_exercises_json = json.dumps([])
    
    return db.execute("""
        INSERT INTO workout_daily_template (
            author_id, 
            name, 
            description, 
            muscle_group, 
            difficulty, 
            exercises,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        author_id,
        name,
        description,
        muscle_group,
        difficulty,
        empty_exercises_json
    ))


def get_daily_template(db: Database, template_id: int) -> Optional[Dict[str, Any]]:
    """Получает шаблон по ID"""
    result = db.execute("""
        SELECT 
            id, 
            author_id, 
            name, 
            description, 
            muscle_group, 
            difficulty, 
            exercises,
            created_at
        FROM workout_daily_template
        WHERE id = ?
    """, (template_id,), fetch_one=True)
    
    if result:
        # Преобразуем JSON строку в список
        result['exercises'] = json.loads(result['exercises'])
        #del result['exercises']
    
    return result


def get_user_templates(db: Database, author_id: int) -> List[Dict[str, Any]]:
    """Получает все шаблоны пользователя"""
    results = db.execute("""
        SELECT 
            id,
            author_id, 
            name, 
            description, 
            muscle_group, 
            difficulty, 
            exercises,
            created_at
        FROM workout_daily_template 
        WHERE author_id = ?
        ORDER BY created_at DESC
    """, (author_id,), fetch_all=True)
    
    # Преобразуем JSON строку в список для каждого шаблона
    for template in results:
        template['exercises'] = json.loads(template['exercises'])
        #del template['exercises']  # Удаляем старое поле
    
    return results


def update_daily_template(
    db: Database,
    template_id: int,
    exercise_id: int,
    sets: int,
    reps: str,
    rest: Optional[int] = None
) -> bool:
    """
    Добавляет упражнение в конец шаблона.
    """
    # 1. Получаем текущий шаблон
    template = db.execute("""
        SELECT exercises FROM workout_daily_template WHERE id = ?
    """, (template_id,), fetch_one=True)
    
    if not template:
        return False
    
    # 2. Преобразуем JSON строку в список
    exercises = json.loads(template['exercises'])
    
    # 3. Создаём новое упражнение
    new_exercise = {
        "exercise_id": exercise_id,
        "sets": sets,
        "reps": reps
    }
    
    # Добавляем rest, если он передан
    if rest is not None:
        new_exercise["rest"] = rest
    
    # 4. Добавляем в конец списка
    exercises.append(new_exercise)
    
    # 5. Преобразуем обратно в JSON строку
    new_exercises_json = json.dumps(exercises, ensure_ascii=False)
    
    # 6. Обновляем в базе данных
    rows_affected = db.execute("""
        UPDATE workout_daily_template
        SET exercises = ?
        WHERE id = ?
    """, (new_exercises_json, template_id))
    
    return rows_affected > 0


def delete_daily_template(db: Database, template_id: int, user_id: int) -> bool:
    rows_affected = db.execute("""
        DELETE FROM workout_daily_template
        WHERE id = ? AND author_id = ?
    """, (template_id, user_id))
    return rows_affected > 0


# 4. Работа с месячными шаблонами



def create_empty_monthly_template(
    db: Database,
    author_id: int,
    name: str,
    description: Optional[str] = None
) -> Optional[int]:

    return db.execute("""
        INSERT INTO workout_monthly_template (author_id, name, description, days_json)
        VALUES (?, ?, ?, ?)
    """, (author_id, name, description, '{}'))


def get_monthly_template(db: Database, template_id: int) -> Optional[Dict[str, Any]]:
    """Получает месячный шаблон по ID"""
    result = db.execute("""
        SELECT 
            id, 
            author_id, 
            name, 
            description, 
            days_json,
            created_at,
            updated_at
        FROM workout_monthly_template 
        WHERE id = ?
    """, (template_id,), fetch_one=True)
    
    if result:
        result['days'] = json.loads(result['days_json'])
        del result['days_json']
    
    return result


def get_user_monthly_templates(db: Database, author_id: int) -> List[Dict[str, Any]]:
    """Получает все месячные шаблоны пользователя (без дней)"""
    results = db.execute("""
        SELECT 
            id, 
            name, 
            description, 
            created_at,
            updated_at
        FROM workout_monthly_template 
        WHERE author_id = ?
        ORDER BY created_at DESC
    """, (author_id,), fetch_all=True)
    
    return results


# ========== РАБОТА С ДНЯМИ ==========

def add_day_to_monthly_template(
    db: Database,
    template_id: int,
    daily_template_id: int
) -> bool:
    """
    Добавляет новый день в конец шаблона.
    Номер дня = текущее количество дней + 1
    """
    template = get_monthly_template(db, template_id)
    if not template:
        return False
    
    days = template['days']
    
    # Новый день получает номер = количество существующих дней + 1
    new_day_number = len(days) + 1
    day_key = f"day{new_day_number}"
    days[day_key] = daily_template_id
    
    days_json = json.dumps(days, ensure_ascii=False)
    rows_affected = db.execute("""
        UPDATE workout_monthly_template 
        SET days_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (days_json, template_id))
    
    return rows_affected > 0, new_day_number


def remove_last_day_from_monthly_template(
    db: Database,
    template_id: int
) -> bool:
    """
    Удаляет последний день из шаблона.
    """
    template = get_monthly_template(db, template_id)
    if not template:
        return False, None
    
    days = template['days']
    
    if not days:
        return False, None  # Нет дней для удаления
    
    # Находим последний день (максимальный номер)
    max_day = max(int(key.replace('day', '')) for key in days.keys())
    removed_day_number = max_day
    
    day_key = f"day{max_day}"
    del days[day_key]
    
    days_json = json.dumps(days, ensure_ascii=False)
    rows_affected = db.execute("""
        UPDATE workout_monthly_template 
        SET days_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (days_json, template_id))
    
    return rows_affected > 0, removed_day_number







def get_total_days_in_template(db: Database, monthly_template_id: int) -> int:
    """Возвращает количество дней в месячном шаблоне (по длине days_json)"""
    template = db.execute("""
        SELECT days_json FROM workout_monthly_template WHERE id = ?
    """, (monthly_template_id,), fetch_one=True)
    if not template:
        return 0
    days_dict = json.loads(template['days_json'])
    return len(days_dict)  # количество добавленных дней


def calculate_progress(started_at: datetime, total_days: int) -> Dict[str, Any]:
    """
    Рассчитывает прогресс на основе текущей даты.
    """

    if isinstance(started_at, str):
        started_at = datetime.fromisoformat(started_at)

    if total_days == 0:
        return {
            "completed_days": 0,
            "progress_percent": 0.0,
            "remaining_days": 0,
            "is_completed": False
        }
    
    today = date.today()
    start_date = started_at.date()
    days_passed = (today - start_date).days
    
    if days_passed >= total_days:
        completed = total_days
        is_completed = True
    else:
        completed = days_passed
        is_completed = False
    
    percent = (completed / total_days) * 100
    
    return {
        "completed_days": completed,
        "progress_percent": round(percent, 1),
        "remaining_days": total_days - completed,
        "is_completed": is_completed
    }


def get_active_goals_count(db: Database, user_id: int) -> int:
    """Сколько активных (незавершённых) целей у пользователя"""
    result = db.execute("""
        SELECT COUNT(*) as cnt FROM goals
        WHERE user_id = ? AND completed_at IS NULL
    """, (user_id,), fetch_one=True)
    return result['cnt'] if result else 0


# ========== ОСНОВНЫЕ ОПЕРАЦИИ ==========

def create_goal(
    db: Database,
    user_id: int,
    monthly_template_id: int,
    is_cycled: bool = False
) -> Optional[int]:
    """
    Создаёт новую цель, если не превышен лимит активных целей (3).
    """
    # Проверка лимита активных целей
    active_count = get_active_goals_count(db, user_id)
    if active_count >= 3:
        raise ValueError("Maximum 3 active goals allowed")
    
    # Проверяем, нет ли уже активной цели с этим же шаблоном
    existing = db.execute("""
        SELECT id FROM goals
        WHERE user_id = ? AND monthly_template_id = ? AND completed_at IS NULL
    """, (user_id, monthly_template_id), fetch_one=True)
    if existing:
        raise ValueError("You already have an active goal for this template")
    
    return db.execute("""
        INSERT INTO goals (user_id, monthly_template_id, is_cycled)
        VALUES (?, ?, ?)
    """, (user_id, monthly_template_id, 1 if is_cycled else 0))


def get_goal(db: Database, goal_id: int) -> Optional[Dict[str, Any]]:
    """Получает цель по ID"""
    result = db.execute("""
        SELECT id, user_id, monthly_template_id, is_cycled, started_at, completed_at
        FROM goals WHERE id = ?
    """, (goal_id,), fetch_one=True)
    return result


def get_user_goals(db: Database, user_id: int) -> List[Dict[str, Any]]:
    """Получает все цели пользователя (активные и завершённые)"""
    return db.execute("""
        SELECT id, monthly_template_id, is_cycled, started_at, completed_at
        FROM goals WHERE user_id = ?
        ORDER BY started_at DESC
    """, (user_id,), fetch_all=True)


def get_active_goals(db: Database, user_id: int) -> List[Dict[str, Any]]:
    """Получает только активные (незавершённые) цели"""
    return db.execute("""
        SELECT id, monthly_template_id, is_cycled, started_at
        FROM goals 
        WHERE user_id = ? AND completed_at IS NULL
        ORDER BY started_at ASC
    """, (user_id,), fetch_all=True)


def check_and_update_completed_goals(db: Database) -> int:
    """
    Проверяет все активные цели и завершает те, у которых прогресс >= 100%.
    Для цикличных целей автоматически перезапускает (создаёт новую цель с текущей датой).
    Возвращает количество обработанных целей.
    """
    # Все активные цели
    active = db.execute("""
        SELECT id, user_id, monthly_template_id, is_cycled, started_at
        FROM goals WHERE completed_at IS NULL
    """, fetch_all=True)
    
    processed = 0
    for goal in active:
        total = get_total_days_in_template(db, goal['monthly_template_id'])
        started = datetime.fromisoformat(goal['started_at'])
        progress = calculate_progress(started, total)
        
        if progress['is_completed']:
            # Завершаем текущую цель
            db.execute("""
                UPDATE goals SET completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (goal['id'],))
            
            if goal['is_cycled']:
                # Создаём новую цель с тем же шаблоном (если не превышен лимит)
                active_count = get_active_goals_count(db, goal['user_id'])
                if active_count < 3:
                    create_goal(
                        db,
                        user_id=goal['user_id'],
                        monthly_template_id=goal['monthly_template_id'],
                        is_cycled=True
                    )
            processed += 1
    
    return processed


# ========== УДАЛЕНИЕ ЦЕЛИ ==========

def delete_goal(db: Database, goal_id: int, user_id: int) -> bool:
    """Удаляет цель (любую)"""
    rows = db.execute("""
        DELETE FROM goals WHERE id = ? AND user_id = ?
    """, (goal_id, user_id))
    return rows > 0







# ========== УДАЛЕНИЕ ==========

def delete_monthly_template(db: Database, template_id: int, author_id: int) -> bool:
    """Удаляет месячный шаблон"""
    rows_affected = db.execute("""
        DELETE FROM workout_monthly_template
        WHERE id = ? AND author_id = ?
    """, (template_id, author_id))
    return rows_affected > 0




if __name__ == "__main__":
    #from databases import Database
    
    db = Database("test_1.db")
    
    '''
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
    
    '''

    #print(get_user_by_username(db, 'aboba'))
    #print(update_last_login(db, 1))
    #print(create_user(db, 'smert', 'net@net.net', 'hashed_pswd'))
    #print(delete_user(db, 2))
    print(update_user_profile(db, 1, 'nikto', 'new@email.com', 'new_hash'))


    print("\n✅ Все тесты пройдены!")