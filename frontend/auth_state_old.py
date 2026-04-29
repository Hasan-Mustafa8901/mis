from nicegui import app


def set_user_context(user: dict):
    app.storage.user["user"] = user


def get_user_context() -> dict:
    return app.storage.user.get("user", {})


def get_user_roles() -> list[str]:
    return app.storage.user.get("user", {}).get("roles", [])
