import sqlite3
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class Database:

    def __init__(self, db_path: str = "test_2_2.db"):
        self.db_path = db_path

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            conn.close()

    def init_tables(self):
        """Создаёт все таблицы если не существуют"""
        statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT CHECK(LENGTH(login) <= 50) UNIQUE NOT NULL,
                username TEXT CHECK(LENGTH(username) <= 50) UNIQUE NOT NULL,
                password_hash TEXT CHECK(LENGTH(password_hash) <= 255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT CHECK(LENGTH(name) <= 50) NOT NULL,
                description TEXT,
                muscle_group TEXT CHECK(LENGTH(muscle_group) <= 100),
                equipment TEXT CHECK(LENGTH(equipment) <= 100),
                difficulty TEXT CHECK(difficulty IN ('beginner', 'intermediate', 'advanced')),
                is_public BOOLEAN DEFAULT TRUE,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                video_url TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS workout_daily_template (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER REFERENCES users(id),
                name TEXT NOT NULL,
                exercises TEXT DEFAULT '[]',
                difficulty TEXT CHECK(difficulty IN ('beginner', 'intermediate', 'advanced')),
                muscle_group TEXT CHECK(LENGTH(muscle_group) <= 100),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS workout_monthly_template (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER REFERENCES users(id),
                name TEXT NOT NULL,
                days_json TEXT DEFAULT '{}',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                monthly_template_id INTEGER NOT NULL REFERENCES workout_monthly_template(id) ON DELETE CASCADE,
                is_cycled BOOLEAN DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                UNIQUE(user_id, monthly_template_id)
            )
            """,
        ]
        for stmt in statements:
            self.execute(stmt)
        logger.info("Database tables initialized")

    def execute(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False,
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

            # Для INSERT возвращаем lastrowid, для остальных — rowcount
            if cursor.lastrowid:
                return cursor.lastrowid
            return cursor.rowcount

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            return cursor.rowcount

if __name__ == "__main__":
    db = Database("test_2_2.db")
    db.init_tables()
