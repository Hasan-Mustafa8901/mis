# frontend/auth.py
from nicegui import app, ui
from functools import wraps
import jwt
from datetime import datetime, timezone


def token_is_valid() -> bool:
    token = get_token()

    if not token:
        return False

    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )

        exp = payload.get("exp")

        if not exp:
            return False

        now = datetime.now(timezone.utc).timestamp()

        return exp > now

    except Exception:
        return False


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


def is_authenticated():
    return token_is_valid()


def protected_page(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        if not token_is_valid():
            clear_user()
            ui.notify("Session expired. Please login again.")
            ui.navigate.to("/login")
            return

        return await func(*args, **kwargs)

    return wrapper


def set_token(token: str):
    app.storage.user["token"] = token


def set_user(data: dict):
    app.storage.user.update(
        {
            "token": data["access_token"],
            "id": data["id"],
            "name": data["name"],
            "role": [data["role"]],
            "outlet_id": data["outlet_id"],
        }
    )


def get_token():
    return app.storage.user.get("token")


def clear_user():
    app.storage.user.clear()
