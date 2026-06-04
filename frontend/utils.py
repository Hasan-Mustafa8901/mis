import re
from datetime import datetime, date, timezone, timedelta
from datetime import date, datetime
from typing import Any


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


def disp_date(
    value: Any,
    output_fmt: str = "%d/%m/%Y",
) -> str | None:
    """
    Convert various date inputs into display format.

    Supports:
    - date
    - datetime
    - ISO strings:
        2026-05-16
        2026-05-16T00:00:00
        2026-05-16 00:00:00
        2026-05-16T00:00:00.000000
        2026-05-16T00:00:00Z

    Returns:
    - formatted date string
    - None if invalid/empty
    """

    if value in (None, "", "null"):
        return None

    try:
        # Already datetime
        if isinstance(value, datetime):
            dt = value

        # date but not datetime
        elif isinstance(value, date):
            dt = datetime.combine(value, datetime.min.time())

        # string handling
        elif isinstance(value, str):
            value = value.strip()

            # Handle trailing Z
            value = value.replace("Z", "+00:00")

            try:
                # Best universal parser for ISO-like strings
                dt = datetime.fromisoformat(value)
            except ValueError:
                # Fallback formats
                known_formats = [
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%Y/%m/%d",
                    "%d-%m-%Y",
                ]

                dt = None

                for fmt in known_formats:
                    try:
                        dt = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue

                if dt is None:
                    return None

        else:
            return None

        return dt.strftime(output_fmt)

    except Exception:
        return None


def date_for_input(date_str: str) -> date:
    if isinstance(date_str, str):
        return datetime.strptime(date_str, r"%d/%m/%Y")


ALIASES = {
    "insurance_with_depreciation_cover": "insurance",
    "genuine_acc_kit": "accessories",
    "cash_discount_all_customers": "cash_discount",
    "additional_discount_from_dealer": "dealer_discount",
    "registration": "registration",
    "ex_showroom_price": "ex_showroom_price",
}
