import os
from database import Database


def get_db() -> Database:
    return Database(os.getenv("DB_PATH", "test_2_2.db"))
