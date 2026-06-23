# frontend\api.py
import httpx
from typing import Any
import os
import json
from datetime import datetime, date
from nicegui import app
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

BASE_URL = os.getenv("API_URL", "http://localhost:8000")


# Safe JSON helper
def json_serial(obj):
    """Fallback serializer for dates."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# EXCEPTIONS
class APIError(Exception):
    """Base API exception."""


class UnauthorizedError(APIError):
    """401 Unauthorized."""


class ForbiddenError(APIError):
    """403 Forbidden."""


class ConnectionFailedError(APIError):
    """Server connection failed."""


class ServerError(APIError):
    """5xx errors."""


# SHARED HTTP CLIENT

# IMPORTANT:
# Reuse ONE AsyncClient for the whole application.
# Creating a new client per request is expensive.

http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(20.0),
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
    ),
)


# AUTH HEADERS


def get_auth_headers() -> dict[str, str]:
    token = app.storage.user.get("token")

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


# =========================================================
# CORE REQUEST FUNCTION
# =========================================================


async def api_request(method: str, path: str, **kwargs) -> Any:
    """
    Centralized API request handler.

    IMPORTANT:
    - NO ui.notify()
    - NO ui.navigate()
    - NO UI OPERATIONS HERE

    This function can be called from:
    - timers
    - background tasks
    - page renders
    - async jobs

    UI operations here will crash NiceGUI context.
    """

    headers = kwargs.pop("headers", {})

    # MERGE AUTH HEADERS
    headers.update(get_auth_headers())

    # REMOVE NONE PARAMS
    if "params" in kwargs and kwargs["params"]:
        kwargs["params"] = {k: v for k, v in kwargs["params"].items() if v is not None}

    try:
        response = await http_client.request(
            method=method, url=f"{BASE_URL}{path}", headers=headers, **kwargs
        )

        # AUTH ERRORS
        if response.status_code == 401:
            raise UnauthorizedError("Session expired")

        if response.status_code == 403:
            raise ForbiddenError("Access denied")

        # SERVER ERRORS
        if response.status_code >= 500:
            raise ServerError(f"Server error: {response.status_code}")

        # RAISE OTHER HTTP ERRORS
        response.raise_for_status()

        # EMPTY RESPONSE
        if not response.content:
            return None

        # JSON RESPONSE
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            return response.json()

        return response.text

    except httpx.ConnectError as exc:
        raise ConnectionFailedError("Unable to connect to server") from exc

    except httpx.TimeoutException as exc:
        raise ConnectionFailedError("Request timeout") from exc

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        try:
            detail = exc.response.json().get("detail")
        except Exception:
            detail = exc.response.text

        logger.error("API ERROR %s %s -> %s", method, path, detail)

        if status == 401:
            raise UnauthorizedError(detail or "Session expired") from exc

        if status == 403:
            raise ForbiddenError(detail or "Access denied") from exc

        if status >= 500:
            raise ServerError(detail or f"Server error: {status}") from exc

        raise APIError(detail or f"HTTP Error: {status}") from exc


# WRAPPER METHODS
async def api_get(path: str, params: dict | None = None):
    return await api_request("GET", path, params=params)


async def api_post(path: str, payload: dict):
    safe_json_str = json.dumps(payload, default=json_serial)
    return await api_request(
        "POST",
        path,
        content=safe_json_str,
        headers={"Content-Type": "application/json"},
    )


async def api_put(path: str, payload: dict):
    safe_json_str = json.dumps(payload, default=json_serial)
    return await api_request(
        "PUT",
        path,
        content=safe_json_str,
        headers={"Content-Type": "application/json"},
    )


async def api_delete(path: str, payload: dict | None = None):
    return await api_request("DELETE", path, json=payload)


# FILE UPLOAD
async def api_post_file(path: str, file, data: dict):
    headers = get_auth_headers()

    name = file.file.name
    content = await file.file.read()

    response = await http_client.post(
        f"{BASE_URL}{path}",
        files={
            "file": (name, content),
        },
        data=data,
        headers=headers,
    )

    # AUTH
    if response.status_code == 401:
        raise UnauthorizedError("Session expired")

    if response.status_code == 403:
        raise ForbiddenError("Access denied")

    response.raise_for_status()

    return response.json()
