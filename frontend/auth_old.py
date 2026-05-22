# frontend/auth.py
from nicegui import app, ui
import asyncio
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


# def require_roles(*allowed_roles: str):
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(*args, **kwargs):
#             user_roles = set(app.storage.user.get("roles", []))
#             if not user_roles.intersection(allowed_roles):
#                 ui.notify("Access Denied", type="negative")
#                 ui.navigate.to("/")  # fallback page
#                 return
#             return await func(*args, **kwargs)
#         return wrapper
#     return decorator


def is_authenticated():
    return token_is_valid()


def protected_page(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        if not token_is_valid():
            await logout_user()
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
            "allowed_outlet_ids": data["allowed_outlet_ids"],
        }
    )


def get_token():
    return app.storage.user.get("token")


def clear_user():
    app.storage.user.clear()


_logout_lock = asyncio.Lock()


async def logout_user():

    if _logout_lock.locked():
        return

    async with _logout_lock:
        try:
            # remove only auth keys
            for key in [
                "token",
                "roles",
                "id",
                "name",
                "allowed_outlet_ids",
            ]:
                app.storage.user.pop(key, None)

            ui.notify(
                "Session expired. Please login again.",
                type="warning",
            )

            ui.navigate.to("/login")

        except Exception as e:
            print("Logout error:", e)


# NEW Version might use this
def require_roles(*allowed_roles: str):
    def decorator(func):

        @wraps(func)
        async def wrapper(*args, **kwargs):

            # AUTH CHECK
            if not is_authenticated():
                print("AUTH: ", is_authenticated())
                await logout_user()

                return

            user_roles = set(app.storage.user.get("role", []))

            # ROLE CHECK
            if not user_roles.intersection(allowed_roles):
                ui.notify(
                    "Access Denied",
                    type="negative",
                )

                ui.navigate.to("/")

                return

            return await func(*args, **kwargs)

        return wrapper

    return decorator
