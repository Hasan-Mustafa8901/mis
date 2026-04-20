# frontend/auth.py
from nicegui import app, ui

from functools import wraps


def set_auth(token: str, roles: list[str]):
    app.storage.user["token"] = token
    app.storage.user["roles"] = roles


def get_roles() -> list[str]:
    return app.storage.user.get("roles", [])


def require_roles(*allowed_roles: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_roles = set(app.storage.user.get("roles", []))

            if not user_roles.intersection(allowed_roles):
                ui.notify("Access Denied", type="negative")
                ui.navigate.to("/")  # fallback page
                return

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def protected_page(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if "token" not in app.storage.user:
            ui.navigate.to("/login")
            return
        return await func(*args, **kwargs)

    return wrapper


def set_token(token: str):
    app.storage.user["token"] = token


def get_token():
    return app.storage.user.get("token")


def clear_token():
    app.storage.user.pop("token", None)
