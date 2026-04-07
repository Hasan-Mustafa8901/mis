import os
import sys
import json

# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import SQLModel, Session
from db.models import (
    Accessory,
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
        # 1. Add Outlets
        outlet = Outlet(name="HN Showroom", city="Lucknow", state="Uttar Pradesh")
        session.add(outlet)
        session.commit()
        session.refresh(outlet)
        outlet = Outlet(name="RR Showroom", city="Lucknow", state="Uttar Pradesh")
        session.add(outlet)
        session.commit()
        session.refresh(outlet)

        # 2. Add Employees
        if outlet.id:
            exec_ = Employee(
                name="John Doe",
                employee_code="E001",
                outlet_id=outlet.id,
                designation="Sales Executive",
            )
            tl = Employee(
                name="Jane Smith",
                employee_code="E002",
                outlet_id=outlet.id,
                designation="Team Leader",
            )
            session.add(exec_)
            session.add(tl)

        # 3. Add Banks
        banks = [
            "HDFC Bank",
            "ICICI Bank",
            "State Bank of India",
            "Axis Bank",
            "Kotak Mahindra Bank",
        ]
        for bank_name in banks:
            session.add(Bank(name=bank_name))

        # 4. Add Discount Components (Initial set based on column_config.json)
        components = [
            # Price Components
            ("Ex Showroom Price", "price", "price_charged", 1),
            ("Insurance (With Depreciation Cover)", "price", "price_charged", 2),
            ("Registration", "price", "price_charged", 3),
            ("Genuine Acc Kit", "price", "price_charged", 4),
            ("TCS", "price", "price_charged", 5),
            ("FasTag", "price", "price_charged", 6),
            ("Ext Warr", "price", "price_charged", 7),
            ("Shield Of Trust", "price", "price_charged", 8),
            # Discount Components
            ("Cash Discount All Customers", "discount", "discount_allowed", 1),
            ("Additional Discount From Dealer", "discount", "discount_allowed", 2),
            ("Extra Kitty on TR Cases", "discount", "discount_allowed", 3),
            (
                "Additional for POI /Corporate Customers",
                "discount",
                "discount_allowed",
                4,
            ),
            ("Additional for Exchange Customers", "discount", "discount_allowed", 5),
            ("Additional for Scrappage Customers", "discount", "discount_allowed", 6),
            (
                "Additional for Upward Sales Customers",
                "discount",
                "discount_allowed",
                7,
            ),
            (
                "Maximum benefit due to price increase",
                "discount",
                "discount_allowed",
                8,
            ),
        ]
        for name, type_, section, order in components:
            session.add(
                DiscountComponent(name=name, type=type_, section=section, order=order)
            )
        with open(r"config/column_config.json", encoding="utf-8") as f:
            config = json.load(f)
            for a in config.get("accessories", []):
                session.add(Accessory(**a))

        session.commit()
        print("Master data seeded.")


if __name__ == "__main__":
    reset_db()
    seed_masters()
