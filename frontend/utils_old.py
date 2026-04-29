import re
from datetime import datetime, date, timezone, timedelta


def build_component_map_from_booking(booking_data: dict) -> dict:
    component_map = {}

    for key, val in booking_data.items():
        if key.endswith("_actual"):
            clean_key = key.replace("_actual", "").strip()

            # normalize for fallback
            norm = re.sub(r"[^a-z0-9]", "", clean_key.lower())

            component_map[clean_key] = val
            component_map[norm] = val  # fallback key

    return component_map


def normalize_key(key: str) -> str:
    key = key.replace("_actual", "")
    key = key.lower()
    key = re.sub(r"[()]", "", key)
    key = re.sub(r"[^a-z0-9]+", "_", key)
    return key.strip("_")


def get_ist_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def get_ist_today() -> date:
    return get_ist_now().date()


ALIASES = {
    "insurance_with_depreciation_cover": "insurance",
    "genuine_acc_kit": "accessories",
    "cash_discount_all_customers": "cash_discount",
    "additional_discount_from_dealer": "dealer_discount",
    "registration": "registration",
    "ex_showroom_price": "ex_showroom_price",
}
