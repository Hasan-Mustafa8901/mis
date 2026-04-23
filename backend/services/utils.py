import re
from datetime import datetime, timezone, timedelta, date


def normalize_component_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def get_ist_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def get_ist_today() -> date:
    return get_ist_now().date()
