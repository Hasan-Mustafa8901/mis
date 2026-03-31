import re


def normalize_component_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())
