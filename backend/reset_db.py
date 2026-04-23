import os
import sys
import json


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import SQLModel, Session

from db.models import (
    Accessory,
    DiscountComponent,
    Outlet,
    Employee,
    Bank,
    Dealership,
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
        # -------------------------
        # 1. DEALERSHIP
        # -------------------------
        dealership = Dealership(name="SRM Motors", code="SRM")
        session.add(dealership)
        session.commit()
        session.refresh(dealership)

        # -------------------------
        # 2. OUTLETS
        # -------------------------
        outlet1 = Outlet(
            name="Kanpur Road Showroom",
            code="SRM-KNP",
            dealership_id=dealership.id,
        )

        outlet2 = Outlet(
            name="RR Showroom",
            code="SRM-VKN",
            dealership_id=dealership.id,
        )

        session.add(outlet1)
        session.add(outlet2)
        session.commit()

        # -------------------------
        # 4. EMPLOYEES
        # -------------------------
        if outlet1.id:
            exec_ = Employee(
                name="John Doe",
                outlet_id=outlet1.id,
                designation="Sales Executive",
            )

            tl = Employee(
                name="Jane Smith",
                outlet_id=outlet1.id,
                designation="Team Leader",
            )

            session.add(exec_)
            session.add(tl)

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
            ("Insurance (With Depreciation Cover)", "price", "price_charged", 2),
            ("Registration", "price", "price_charged", 3),
            ("Accessories", "price", "price_charged", 4),
            ("TCS", "price", "price_charged", 5),
            ("FasTag", "price", "price_charged", 6),
            ("Extended Warranty", "price", "price_charged", 7),
            ("Shield Of Trust", "price", "price_charged", 8),
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
