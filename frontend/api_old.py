import httpx

BASE_URL = "http://localhost:8000"


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


async def fetch_reference_data() -> dict:
    """
    Fetch all static reference data needed by the form.
    Returns a dict with keys: cars, components, outlets, executives
    """
    result = {}
    for key, path, fallback in [
        ("cars", "/cars", []),
        ("components", "/components", []),
        ("outlets", "/outlets", [{"id": 1, "name": "Main Outlet"}]),
        ("executives", "/sales-executives", [{"id": 1, "name": "Default SE"}]),
        ("accessories", "/accessories", []),
    ]:
        try:
            result[key] = await api_get(path)
        except Exception:
            result[key] = fallback

    return result
