# services/reports/daily/computations.py

from typing import Any


def safe_divide(a: int | float, b: int | float) -> float:
    if not b:
        return 0.0
    return a / b


def extract_pending_docs(
    checklist: dict[str, Any] | None,
) -> list[str]:

    if not checklist:
        return []

    pending = []

    for key, value in checklist.items():
        if value is False:
            pending.append(key)

    return pending
