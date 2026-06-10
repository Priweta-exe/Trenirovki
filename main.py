import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv

from database import Database
from functions import check_and_update_completed_goals
from middleware import AuthMiddleware
from users import users_router
from exercises import exercises_router
from daily_templates import daily_templates_router
from monthly_templates import workout_monthly_template_router
from goals import goals_router
from pages import pages_router

load_dotenv("secrets.env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(os.getenv("DB_PATH", "test_2_1.db"))
    processed = check_and_update_completed_goals(db)
    logger.info(f"Startup: completed goals checked, processed={processed}")
    yield
    logger.info("Shutdown")


app = FastAPI(
    title="Workout Planner API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# API роутеры
app.include_router(users_router)
app.include_router(exercises_router)
app.include_router(daily_templates_router)
app.include_router(workout_monthly_template_router)
app.include_router(goals_router)

# HTML страницы
app.include_router(pages_router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_excludes=["logs/*"])
