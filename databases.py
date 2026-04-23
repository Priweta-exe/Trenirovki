import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union
import json


class Database:

    def __init__(self, db_path: str = "test.db"):

        self.db_path = db_path

    @contextmanager
    def _get_connection(self):

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def execute(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Union[None, Dict[str, Any], List[Dict[str, Any]], int]:

        with self._get_connection() as conn:

            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_one:
                row = cursor.fetchone()
                return dict(row) if row else None
            
            if fetch_all:
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

            return cursor.rowcount
    
    def execute_many(
        self,
        query: str,
        params_list: List[tuple]
    ) -> int:

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    def execute_with_json(
        self,
        query: str,
        json_fields: Dict[str, Any],
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Union[None, Dict[str, Any], List[Dict[str, Any]], int]:
        params_list = list(params)
        
        for placeholder, data in json_fields.items():
            # placeholder ожидается в формате "$1", "$2", и т.д.
            index = int(placeholder[1:]) - 1
            # Заменяем Python-объект на JSON строку
            params_list[index] = json.dumps(data, ensure_ascii=False)
        
        # Выполняем обычный запрос с преобразованными параметрами
        return self.execute(query, tuple(params_list), fetch_one, fetch_all)
    

if __name__ == "__main__":
    db = Database("test_1.db")
    db.execute("""
        CREATE TABLE exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT CHECK(LENGTH(name) <= 50) NOT NULL,
    description TEXT,
    muscle_group TEXT CHECK(LENGTH(muscle_group) <= 100), 
    equipment TEXT CHECK(LENGTH(equipment) <= 100),
    difficulty TEXT CHECK(LENGTH(difficulty) <= 20),
    is_public BOOLEAN DEFAULT TRUE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP,
    video_url TEXT
    );
    """)
    db.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT CHECK(LENGTH(login) <= 50) UNIQUE NOT NULL,
        username TEXT CHECK(LENGTH(username) <= 50) UNIQUE NOT NULL,
        password_hash TEXT CHECK(LENGTH(password_hash) <= 255) NOT NULL,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        last_login TIMESTAMP
    );
    """)
    db.execute("""
    CREATE TABLE workout_daily_template (
    author_id INTEGER REFERENCES users(id),
    exercises JSONB,
    difficulty TEXT CHECK(LENGTH(difficulty) <= 20),
    muscle_group TEXT CHECK(LENGTH(muscle_group) <= 100),
    description TEXT,
    created_at TIMESTAMP
    );
    """)
    db.execute("""
    CREATE TABLE Workout_monthy_template (
    author_id INTEGER REFERENCES users(id),
    templates JSONB,
    difficulty TEXT CHECK(LENGTH(difficulty) <= 20),
    muscle_group TEXT CHECK(LENGTH(muscle_group) <= 100),
    description TEXT,
    created_at TIMESTAMP
    )

    """)
    
    db.execute(
        "INSERT INTO users (login, username, password_hash) VALUES (?, ?, ?)",
        ("12345@54321", 'Юра', 'qwerty')
    )
    
    # Читаем данные
    user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        ("Юра",),
        fetch_one=True
    )
    print(f"Found user: {user}")
    
    # Массовая вставка
    users_data = [
        ("222@333", 'Витя', 'asdfgh'),
        ("444@555", 'Маша', 'zxcvbn'),
        ("666@777", 'еще кто-то', 'qazwsx')
    ]
    db.execute_many(
        "INSERT INTO users (login, username, password_hash) VALUES (?, ?, ?)",
        users_data
    )
    
    all_users = db.execute("SELECT * FROM users", fetch_all=True)
    print(f"All users: {all_users}")
    

    print("\n База данных работает корректно.")