from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from users import users_router
from exercises import exercises_router
from daily_templates import daily_templates_router
from monthly_templates import workout_monthly_template_router
from goals import goals_router

app = FastAPI(title="Workout Planner API")


# Подключаем роутеры
app.include_router(users_router)
app.include_router(exercises_router)
app.include_router(daily_templates_router)
app.include_router(workout_monthly_template_router)
app.include_router(goals_router)

# Корневой эндпоинт для проверки
@app.get("/")
def root():
    return {"message": "Workout Planner API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",          # Формат: "имя_файла:имя_переменной"
        host="0.0.0.0",      # Слушаем все интерфейсы
        port=8000,           # Порт
        reload=True          # Автоперезагрузка при изменениях
    )