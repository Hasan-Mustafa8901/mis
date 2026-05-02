import asyncio
from services.api import api_get

async def fetch_reference_data() -> dict:
    """
    Fetch all static reference data needed by the form.
    Returns a dict with keys: cars, variants, outlets, executives, accessories, dealerships
    """
    tasks = {
        "cars": api_get("/cars"),
        "variants": api_get("/variants"),
        "outlets": api_get("/outlets"),
        "executives": api_get("/sales-executives"),
        "accessories": api_get("/accessories"),
        "dealerships": api_get("/complaints/dealerships"),
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    final = {}
    for (key, _), result in zip(tasks.items(), results):
        if isinstance(result, Exception):
            final[key] = []
        else:
            final[key] = result
    return final
