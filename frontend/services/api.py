import httpx
from utils.constants import BASE_URL
from auth.auth import get_token
from nicegui import app

def get_auth_headers():
    token = app.storage.user.get("token")
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

async def api_get(path: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BASE_URL}{path}", headers=get_auth_headers(), timeout=10
        )
        r.raise_for_status()
        return r.json()

async def api_post(path: str, payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}{path}", json=payload, headers=get_auth_headers(), timeout=10
        )
        r.raise_for_status()
        return r.json()

async def api_post_file(path: str, file, data: dict):
    token = app.storage.user.get("token")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Check if 'file' is a NiceGUI UploadEvent arguments (has .file attribute) or already a file object
    if hasattr(file, "file"):
        name = file.file.name
        content = await file.file.read()
    else:
        name = getattr(file, "name", "file")
        content = await file.read()

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}{path}",
            files={"file": (name, content)},
            data=data,
            headers=headers,
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

async def api_put(path: str, payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"{BASE_URL}{path}", json=payload, headers=get_auth_headers(), timeout=10
        )
        r.raise_for_status()
        return r.json()
