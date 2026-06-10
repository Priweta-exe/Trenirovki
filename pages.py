from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
 
from dependencies import get_db
from utils import get_current_user
 
jinja = Jinja2Templates(directory="templates")
pages_router = APIRouter(include_in_schema=False)
 
 
@pages_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return jinja.TemplateResponse(request=request, name="login.html")
 
 
@pages_router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return jinja.TemplateResponse(request=request, name="register.html")
 
 
@pages_router.get("/logout")
def logout_page():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response
 
 
@pages_router.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/dashboard", status_code=302)
 
 
@pages_router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, current_user: dict = Depends(get_current_user)):
    return jinja.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"user": current_user, "active_page": "dashboard"},
    )
 
 
@pages_router.get("/exercises", response_class=HTMLResponse)
def exercises_page(request: Request, current_user: dict = Depends(get_current_user)):
    return jinja.TemplateResponse(
        request=request,
        name="exercises.html",
        context={"user": current_user, "active_page": "exercises"},
    )
 
 
@pages_router.get("/daily-templates", response_class=HTMLResponse)
def daily_templates_page(request: Request, current_user: dict = Depends(get_current_user)):
    return jinja.TemplateResponse(
        request=request,
        name="daily_templates.html",
        context={"user": current_user, "active_page": "daily"},
    )
 
 
@pages_router.get("/calendar-templates", response_class=HTMLResponse)
def calendar_templates_page(request: Request, current_user: dict = Depends(get_current_user)):
    return jinja.TemplateResponse(
        request=request,
        name="calendar_templates.html",
        context={"user": current_user, "active_page": "calendar"},
    )
 
