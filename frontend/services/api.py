import httpx
from utils.constants import BASE_URL
from auth.auth import get_token

async def api_get(path: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json()

async def api_post(path: str, payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()

async def api_post_file(path: str, file, data: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}{path}",
            files={"file": (file.name, await file.content.read())},
            data=data,
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

async def api_put(path: str, payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.put(f"{BASE_URL}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
