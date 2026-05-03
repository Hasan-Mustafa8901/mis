import os
import sys
import json


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import SQLModel, Session

from db.models import (
    Accessory,
    Dealership,
    DiscountComponent,
    Outlet,
    Employee,
    Bank,
)
from db.session import engine


# -------------------------
# RESET DB
# -------------------------
def reset_db():
    print("Dropping all tables...")
    SQLModel.metadata.drop_all(engine)

    print("Creating all tables...")
    SQLModel.metadata.create_all(engine)

    print("Database reset complete.")


# -------------------------
# SEED DATA
# -------------------------
def seed_masters():
    with Session(engine) as session:
        # ── 1. Dealerships & Showrooms ────────────────────────────
        # (1 dealerships × 5 showrooms) + 1 dealerships × 1 showrooms = 6 outlets total
        dealership_data = [
            {
                "name": "SRM Motors",
                "code": "SRM",
                "showrooms": [
                    {
                        "name": "SRM Motors – SRM VKN",
                        "code": "SRM VKN",
                        "address": "Lucknow, Uttar Pradesh",
                    },
                    {
                        "name": "SRM Motors – SRM KPR",
                        "code": "SRM KPR",
                        "address": "Lucknow, Uttar Pradesh",
                    },
                    {
                        "name": "SRM Motors – SRM STR",
                        "code": "SRM STR",
                        "address": "Lucknow, Uttar Pradesh",
                    },
                    {
                        "name": "SRM Motors – SRM MLG",
                        "code": "SRM MLG",
                        "address": "Lucknow, Uttar Pradesh",
                    },
                    {
                        "name": "SRM Motors – SRM RBL",
                        "code": "SRM RBL",
                        "address": "Raebareli, Uttar Pradesh",
                    },
                ],
            },
            {
                "name": "Beeaar TATA",
                "code": "BR",
                "showrooms": [
                    {
                        "name": "Beeaar TATA – BR GC",
                        "code": "BR-GN",
                        "address": "Lucknow, Uttar Pradesh",
                    },
                ],
            },
        ]
        for d_data in dealership_data:
            dealership = Dealership(name=d_data["name"], code=d_data["code"])
            session.add(dealership)
            session.commit()
            session.refresh(dealership)

            for s in d_data["showrooms"]:
                outlet = Outlet(
                    name=s["name"],
                    code=s["code"],
                    address=s["address"],
                    dealership_id=dealership.id,
                )
                session.add(outlet)
                session.commit()
                session.refresh(outlet)
        # -------------------------
        # 5. BANKS
        # -------------------------
        banks = [
            "HDFC Bank",
            "ICICI Bank",
            "State Bank of India",
            "Axis Bank",
            "Kotak Mahindra Bank",
        ]

        for bank_name in banks:
            session.add(Bank(name=bank_name))

        # -------------------------
        # 6. DISCOUNT COMPONENTS
        # -------------------------
        components = [
            ("Ex Showroom Price", "price", "price_charged", 1),
            ("TCS", "price", "price_charged", 2),
            ("Insurance", "price", "price_charged", 3),
            ("Registration", "price", "price_charged", 4),
            ("FasTag", "price", "price_charged", 5),
            ("Accessories", "price", "price_charged", 6),
            ("AMC", "price", "price_charged", 7),
            ("Extended Warranty", "price", "price_charged", 8),
            ("Cash Discount All Customers", "discount", "discount_allowed", 1),
            ("Additional Discount From Dealer", "discount", "discount_allowed", 2),
            (
                "Additional for POI /Corporate Customers",
                "discount",
                "discount_allowed",
                3,
            ),
            ("Green Bonus", "discount", "discount_allowed", 4),
            ("Additional for Exchange Customers", "discount", "discount_allowed", 5),
            ("Additional for Scrappage Customers", "discount", "discount_allowed", 6),
            (
                "Additional Loyalty (EV TO EV)",
                "discount",
                "discount_allowed",
                7,
            ),
            (
                "Additional Loyalty (ICE TO EV)",
                "discount",
                "discount_allowed",
                8,
            ),
            (
                "Maximum benefit due to price increase",
                "discount",
                "discount_allowed",
                9,
            ),
        ]

        for name, type_, section, order in components:
            session.add(
                DiscountComponent(
                    name=name,
                    type=type_,
                    section=section,
                    order=order,
                )
            )

        # -------------------------
        # 7. ACCESSORIES
        # -------------------------
        with open("config/column_config.json", encoding="utf-8") as f:
            config = json.load(f)

        for a in config.get("accessories", []):
            session.add(Accessory(**a))

        # -------------------------
        # FINAL COMMIT
        # -------------------------
        session.commit()

        print("Master data seeded successfully.")


# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    reset_db()
    seed_masters()
