from fastapi import FastAPI, Request
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

# Подключаем статические файлы (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем шаблоны Jinja2
templates = Jinja2Templates(directory="templates")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключаем роутеры
app.include_router(users_router)
app.include_router(exercises_router)
app.include_router(daily_templates_router)
app.include_router(workout_monthly_template_router)
app.include_router(goals_router)

@app.get("/")
def home(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login")
def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register")
def register_page(request: Request):
    """Страница регистрации"""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/exercises")
def exercises_page(request: Request):
    """Страница со списком упражнений"""
    return templates.TemplateResponse("exercises/list.html", {"request": request})


@app.get("/daily-templates")
def daily_templates_page(request: Request):
    """Страница со списком дневных шаблонов"""
    return templates.TemplateResponse("daily_templates/list.html", {"request": request})


@app.get("/monthly-templates")
def monthly_templates_page(request: Request):
    """Страница со списком месячных шаблонов"""
    return templates.TemplateResponse("monthly_templates/list.html", {"request": request})


@app.get("/goals")
def goals_page(request: Request):
    """Страница с целями"""
    return templates.TemplateResponse("goals/list.html", {"request": request})
if __name__ == "__main__":
    uvicorn.run(
        "main:app",          # Формат: "имя_файла:имя_переменной"
        host="0.0.0.0",      # Слушаем все интерфейсы
        port=8000,           # Порт
        reload=True          # Автоперезагрузка при изменениях
    )