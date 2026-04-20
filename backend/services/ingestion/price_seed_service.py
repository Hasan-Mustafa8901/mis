import re
import pandas as pd
from datetime import datetime, date
from typing import Optional, Union
from sqlmodel import Session, select
from db.models import (
    Car,
    Variant,
    PriceList,
    PriceListItem,
    DiscountComponent,
    FuelType,
)
from rich import print


def parse_date_from_string(date_str: str) -> Optional[date]:
    date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str)

    match = re.search(r"\d{1,2}\s+[A-Za-z]+\s+\d{2,4}", date_str)
    if match:
        clean_str = match.group(0)
        for fmt in ["%d %B %y", "%d %B %Y"]:
            try:
                return datetime.strptime(clean_str, fmt).date()
            except ValueError:
                continue
    return None


def normalize(name: str):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


class PriceListIngestionService:
    @staticmethod
    def seed_from_excel(
        session: Session,
        file_path: str,
        sheet_name: Union[str, int] = 0,
        valid_from: date = None,
        valid_to: date = None,
    ):

        # 🔹 1. Read Excel (SINGLE HEADER ONLY)
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print("EXCEL HEADERS:", df.columns.tolist())
        print("EXCEL HEADS:\n", df.head())

        # 🔹 2. Components from DB
        db_components = session.exec(select(DiscountComponent)).all()
        print("DB COMPONENTS:", [c.name for c in db_components])

        comp_map = {normalize(c.name): c for c in db_components}
        print("NORMALIZED DB COMPONENTS:", list(comp_map.keys()))

        # 🔹 3. Map columns → components (SIMPLE MATCH)
        mapped_cols = []  # (col_index, component)

        print("DB COMPONENTS:", comp_map.keys())
        print("EXCEL HEADERS:", [normalize(c) for c in df.columns])
        for i, col in enumerate(df.columns):
            normalized_header = normalize(col)

            comp = None
            for key in comp_map:
                if key == normalized_header:
                    comp = comp_map[key]
                    break

            if comp:
                mapped_cols.append((i, comp))
                print(f"MAPPED COLUMN: '{col}' → Component '{comp.name}'")
            else:
                print("UNMATCHED COLUMN:", col)

        # 🚨 If nothing matched → fail early
        if not mapped_cols:
            raise ValueError("No columns matched with DiscountComponent table")

        # 🔹 4. Create ONE price list (no schemes now)
        if not valid_from:
            raise ValueError("valid_from is required")

        price_list = session.exec(
            select(PriceList).where(PriceList.valid_from == valid_from)
        ).first()

        if not price_list:
            price_list = PriceList(
                valid_from=valid_from,
                valid_to=valid_to,
                name=f"Price List {valid_from}",
            )
            session.add(price_list)
            session.flush()

        # 🔹 5. Cache existing items (avoid duplicates)
        existing_items = {
            (i.price_list_id, i.variant_id, i.component_id): i
            for i in session.exec(select(PriceListItem)).all()
        }

        # 🔹 6. Process rows
        for _, row in df.iterrows():
            raw_model = row.iloc[0]
            raw_variant = row.iloc[4]  # Concatenate column
            fuel_type_col = row.iloc[5]

            if pd.isna(raw_model) or pd.isna(raw_variant):
                continue

            if str(raw_model).strip().isdigit():
                continue

            car_name = str(raw_model).strip()
            full_variant = str(raw_variant).strip()
            fuel_type = str(fuel_type_col).lower().strip()

            # --- Car ---
            car = session.exec(select(Car).where(Car.name == car_name)).first()
            if not car:
                car = Car(name=car_name)
                session.add(car)
                session.flush()

            # --- Variant ---
            variant = session.exec(
                select(Variant).where(Variant.full_variant_name == full_variant)
            ).first()

            if not variant and car.id:
                variant = Variant(
                    car_id=car.id,
                    variant_name=full_variant,
                    full_variant_name=full_variant,
                    fuel_type=FuelType(fuel_type),
                    model_year=2025,
                )
                session.add(variant)
                session.flush()

            # --- Insert components ---
            for col_idx, comp in mapped_cols:
                val = row.iloc[col_idx]

                if pd.notna(val) and isinstance(val, (int, float)):
                    key = (price_list.id, variant.id, comp.id)

                    if key in existing_items:
                        existing_items[key].allowed_amount = float(val)
                    else:
                        item = PriceListItem(
                            price_list_id=price_list.id,
                            variant_id=variant.id,
                            component_id=comp.id,
                            allowed_amount=float(val),
                        )
                        session.add(item)
                        existing_items[key] = item

        # 🔹 7. Commit once
        session.commit()

        return {
            "status": "success",
            "columns_mapped": len(mapped_cols),
            "valid_from_used": str(valid_from),
        }
