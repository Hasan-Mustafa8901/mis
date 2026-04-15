from typing import Dict, Tuple


RENAME_MAP = {
    "Ex-Showroom Price": "ex_showroom_price",
    "Insurance": "insurance",
    "Registration": "registration",
    "Hyundai Genuine Acc Kit": "accessory_kit",
    "TCS": "tcs",
    "FasTag": "fastag",
    "ext warr": "extended_warranty",
    "Shield Of Trust": "shield_trust",
    "Cash Discount All Customers": "discount_a",
    "Additional Discount From Dealer": "discount_b",
    "Extra Kitty on TR Cases": "tr_discount",
    "Additional for Exchange Customers": "exchange_discount",
    "Additional for Scrappage Customers": "scrappage_discount",
    "Additional for Upward Sales Customers": "upgrade_discount",
    "Maximum benefit due to price increase": "price_increase_benefit",
}


# Reverse map for output
REVERSE_MAP = {v: k for k, v in RENAME_MAP.items()}


class Normalizer:
    # =========================
    # 1. NORMALIZE KEYS
    # =========================
    @staticmethod
    def normalize_input(
        data: Dict[str, float],
        source: str,  # "current" or "listed"
    ) -> Dict[str, float]:

        normalized = {}

        for key, value in data.items():
            if key not in RENAME_MAP:
                raise ValueError(f"Unknown field: {key}")

            internal_name = RENAME_MAP[key]
            prefixed_name = f"{source}_{internal_name}"

            normalized[prefixed_name] = float(value)

        return normalized

    # =========================
    # 2. MERGE SOURCES
    # =========================
    @staticmethod
    def merge_data(
        current_data: Dict[str, float],
        listed_data: Dict[str, float],
    ) -> Dict[str, float]:

        return {
            **Normalizer.normalize_input(current_data, "current"),
            **Normalizer.normalize_input(listed_data, "listed"),
        }

    # =========================
    # 3. VALIDATE REQUIRED FIELDS
    # =========================
    @staticmethod
    def validate_required(data: Dict[str, float], required_fields: Tuple[str]):

        missing = [field for field in required_fields if field not in data]

        if missing:
            raise ValueError(f"Missing required fields: {missing}")

    # =========================
    # 4. REVERSE FOR OUTPUT
    # =========================
    @staticmethod
    def denormalize_output(data: Dict[str, float]) -> Dict[str, float]:

        output = {}

        for key, value in data.items():
            # remove prefix
            if key.startswith("current_"):
                base = key.replace("current_", "")
            elif key.startswith("listed_"):
                base = key.replace("listed_", "")
            else:
                base = key

            real_name = REVERSE_MAP.get(base, base)
            output[real_name] = value

        return output
