from services.api import api_get

async def fetch_reference_data() -> dict:
    """
    Fetch all static reference data needed by the form.
    Returns a dict with keys: cars, components, outlets, executives
    """
    result = {}
    for key, path, fallback in [
        ("cars", "/cars", []),
        ("variants", "/variants", []),
        ("components", "/components", []),
        ("outlets", "/outlets", [{"id": 1, "name": "Main Outlet"}]),
        ("executives", "/sales-executives", [{"id": 1, "name": "Default SE"}]),
        ("accessories", "/accessories", []),
        ("dealerships", "/complaints/dealerships", []),
    ]:
        try:
            result[key] = await api_get(path)
        except Exception:
            result[key] = fallback

    return result
