import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

# Страницы, доступные без авторизации
PUBLIC_PATHS = {"/login", "/register", "/health"}
# Префиксы API не трогаем — у них своя авторизация через get_current_user
API_PREFIXES = ("/users/", "/exercises", "/daily-templates", "/monthly-templates",
                "/goals", "/calendar-templates")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Статику не проверяем
        if path.startswith("/static"):
            return await call_next(request)

        # API-эндпоинты не трогаем
        if any(path.startswith(p) for p in API_PREFIXES):
            return await call_next(request)

        # Публичные страницы пропускаем
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Для всего остального проверяем cookie
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)

        return await call_next(request)
