import os
import sys
import json

# Add backend to sys.path
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


def reset_db():
    print("Dropping all tables...")
    SQLModel.metadata.drop_all(engine)
    print("Creating all tables...")
    SQLModel.metadata.create_all(engine)
    print("Database reset complete.")


def seed_masters():
    with Session(engine) as session:

        # ── 1. Dealerships & Showrooms ────────────────────────────
        # 2 dealerships × 3 showrooms = 6 outlets total
        dealership_data = [
            {
                "name": "Alpha Motors",
                "showrooms": [
                    {"name": "Alpha Motors – Main Branch",   "city": "Lucknow",   "state": "Uttar Pradesh"},
                    {"name": "Alpha Motors – Hazratganj",    "city": "Lucknow",   "state": "Uttar Pradesh"},
                    {"name": "Alpha Motors – Kanpur Road",   "city": "Lucknow",   "state": "Uttar Pradesh"},
                ],
            },
            {
                "name": "Beta Auto Group",
                "showrooms": [
                    {"name": "Beta Auto – Gomti Nagar",      "city": "Lucknow",   "state": "Uttar Pradesh"},
                    {"name": "Beta Auto – Aliganj",          "city": "Lucknow",   "state": "Uttar Pradesh"},
                    {"name": "Beta Auto – Faizabad Road",    "city": "Lucknow",   "state": "Uttar Pradesh"},
                ],
            },
        ]

        last_outlet = None
        for d_data in dealership_data:
            dealership = Dealership(name=d_data["name"])
            session.add(dealership)
            session.commit()
            session.refresh(dealership)

            for s in d_data["showrooms"]:
                outlet = Outlet(
                    name=s["name"],
                    city=s["city"],
                    state=s["state"],
                    dealership_id=dealership.id,
                )
                session.add(outlet)
                session.commit()
                session.refresh(outlet)
                last_outlet = outlet

        # ── 2. Sample Employees (assigned to the last seeded outlet) ──
        if last_outlet and last_outlet.id:
            session.add(Employee(
                name="John Doe",
                outlet_id=last_outlet.id,
                designation="Sales Executive",
            ))
            session.add(Employee(
                name="Jane Smith",
                outlet_id=last_outlet.id,
                designation="Team Leader",
            ))

        # ── 3. Banks ──────────────────────────────────────────────
        for bank_name in [
            "HDFC Bank",
            "ICICI Bank",
            "State Bank of India",
            "Axis Bank",
            "Kotak Mahindra Bank",
        ]:
            session.add(Bank(name=bank_name))

        # ── 4. Discount Components ────────────────────────────────
        components = [
            # Price Components
            ("Ex Showroom Price",                        "price",    "price_charged",    1),
            ("Insurance (With Depreciation Cover)",      "price",    "price_charged",    2),
            ("Registration",                             "price",    "price_charged",    3),
            ("Genuine Acc Kit",                          "price",    "price_charged",    4),
            ("TCS",                                      "price",    "price_charged",    5),
            ("FasTag",                                   "price",    "price_charged",    6),
            ("Ext Warr",                                 "price",    "price_charged",    7),
            ("Shield Of Trust",                          "price",    "price_charged",    8),
            # Discount Components
            ("Cash Discount All Customers",              "discount", "discount_allowed", 1),
            ("Additional Discount From Dealer",          "discount", "discount_allowed", 2),
            ("Extra Kitty on TR Cases",                  "discount", "discount_allowed", 3),
            ("Additional for POI /Corporate Customers",  "discount", "discount_allowed", 4),
            ("Additional for Exchange Customers",        "discount", "discount_allowed", 5),
            ("Additional for Scrappage Customers",       "discount", "discount_allowed", 6),
            ("Additional for Upward Sales Customers",    "discount", "discount_allowed", 7),
            ("Maximum benefit due to price increase",    "discount", "discount_allowed", 8),
        ]
        for name, type_, section, order in components:
            session.add(
                DiscountComponent(name=name, type=type_, section=section, order=order)
            )

        # ── 5. Accessories (from config) ──────────────────────────
        with open(r"config/column_config.json", encoding="utf-8") as f:
            config = json.load(f)
            for a in config.get("accessories", []):
                session.add(Accessory(**a))

        session.commit()
        print("Master data seeded.")


if __name__ == "__main__":
    reset_db()
    seed_masters()

