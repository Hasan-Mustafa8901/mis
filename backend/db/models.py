from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from zoneinfo import ZoneInfo
from services.utils import get_ist_now


## User Table
class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    password_hash: str = Field(index=True)
    role: str = Field(index=True)  # "auditor", "manager/audit", "client"
    is_active: bool = True
    created_at: datetime = Field(default_factory=get_ist_now)
    is_logged_in: bool = False


# =========================
#  CORE MASTERS
# =========================
class Customer(SQLModel, table=True):
    # TODO: Make aaadhar_number and pan_number unique in the DB to prevent duplicates. Handle gracefully in API.
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    mobile_number: str = Field(index=True)
    alternate_mobile: Optional[str] = None
    email: Optional[str] = None
    pan_number: Optional[str] = None
    aadhar_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pin_code: Optional[str] = None
    created_at: datetime = Field(default_factory=get_ist_now)

    transactions: List["Transaction"] = Relationship(back_populates="customer")


class Car(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=get_ist_now)

    variants: List["Variant"] = Relationship(back_populates="car")


class Variant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    car_id: int = Field(foreign_key="car.id")

    variant_name: str
    full_variant_name: str  # Concatenated name for MIS display
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    model_year: Optional[int] = None

    created_at: datetime = Field(default_factory=get_ist_now)

    car: Optional[Car] = Relationship(back_populates="variants")
    price_list_items: List["PriceListItem"] = Relationship(back_populates="variant")


class Outlet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    city: Optional[str] = None
    state: Optional[str] = None
    created_at: datetime = Field(default_factory=get_ist_now)


# This table is for client employees data only.
class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    outlet_id: int = Field(foreign_key="outlet.id")
    designation: Optional[str] = None  # e.g., "Sales Executive", "Team Leader"
    created_at: datetime = Field(default_factory=get_ist_now)


class Bank(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    is_active: bool = True


# =========================
#  PRICE LIST & COMPONENTS
# =========================


class DiscountComponent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)  # Exact MIS column name
    type: str  # "price" or "discount"
    section: str  # "price_charged" or "discount_allowed"
    order: int  # For MIS reconstruction order

    price_list_items: List["PriceListItem"] = Relationship(back_populates="component")


class PriceList(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    valid_from: date
    valid_to: Optional[date] = None
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=get_ist_now)

    items: List["PriceListItem"] = Relationship(back_populates="price_list")


class PriceListItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    price_list_id: int = Field(foreign_key="pricelist.id")
    variant_id: int = Field(foreign_key="variant.id")
    component_id: int = Field(foreign_key="discountcomponent.id")

    allowed_amount: float = 0.0
    conditions: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    price_list: Optional[PriceList] = Relationship(back_populates="items")
    variant: Optional[Variant] = Relationship(back_populates="price_list_items")
    component: Optional[DiscountComponent] = Relationship(
        back_populates="price_list_items"
    )


# =========================
#  Accessory Master
# =========================
class Accessory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    listed_price: float

    transactions: List["TransactionAccessoryLink"] = Relationship(
        back_populates="accessory"
    )


class TransactionAccessoryLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    transaction_id: int = Field(foreign_key="transaction.id")
    accessory_id: int = Field(foreign_key="accessory.id")

    transaction: Optional["Transaction"] = Relationship(back_populates="accessories")
    accessory: Optional["Accessory"] = Relationship(back_populates="transactions")


# =========================
#  TRANSACTIONS (MIS CORE)
# =========================


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    variant_id: int = Field(foreign_key="variant.id")
    outlet_id: int = Field(foreign_key="outlet.id")
    sales_executive_id: int = Field(foreign_key="employee.id")
    bank_id: Optional[int] = Field(default=None, foreign_key="bank.id")

    # Core Transaction Info
    booking_date: date
    delivery_date: Optional[date] = None
    invoice_number: Optional[str] = Field(default=None, index=True)
    customer_file_number: Optional[str] = None

    # Vehicle Instance Details
    vin_number: Optional[str] = Field(default=None, index=True)
    engine_number: Optional[str] = None
    color: Optional[str] = None
    registration_number: Optional[str] = None
    registration_date: Optional[date] = None

    # MIS Logic Inputs
    team_leader: Optional[str] = None
    conditions: Dict[str, bool] = Field(default={}, sa_column=Column(JSON))

    # Additional MIS Sections
    exchange_details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    finance_details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    delivery_checks: Dict[str, bool] = Field(default={}, sa_column=Column(JSON))
    audit_info: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    invoice_details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    payment_details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Audit Results
    total_allowed_discount: float = 0.0
    total_actual_discount: float = 0.0
    total_excess_discount: float = 0.0
    status: str = "UnderLimit"  # "UnderLimit", "Excess"
    total_price_charged: float = 0.0
    total_discount: float = 0.0
    net_receivable: float = 0.0

    total_received: float = 0.0
    balance_amount: float = 0.0
    payment_status: Optional[str] = None

    created_at: datetime = Field(default_factory=get_ist_now)

    # Relationships
    customer: Customer = Relationship(back_populates="transactions")
    items: List["TransactionItem"] = Relationship(back_populates="transaction")
    accessories: List["TransactionAccessoryLink"] = Relationship(
        back_populates="transaction"
    )


class TransactionItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: int = Field(foreign_key="transaction.id")
    component_id: int = Field(foreign_key="discountcomponent.id")

    component_name: str  # Snapshot for history
    component_type: str  # Snapshot

    actual_amount: float = 0.0
    allowed_amount: float = 0.0
    difference: float = 0.0

    transaction: Optional[Transaction] = Relationship(back_populates="items")


class EditRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # ─────────────────────────────
    # RELATIONS
    # ─────────────────────────────
    transaction_id: int = Field(foreign_key="transaction.id", index=True)

    requested_by: Optional[int] = Field(
        foreign_key="user.id"
    )  # TODO: Remove this make it mandatory.
    reviewed_by: Optional[int] = Field(default=None, foreign_key="user.id")

    # ─────────────────────────────
    # TIMESTAMPS
    # ─────────────────────────────
    requested_at: datetime = Field(default_factory=get_ist_now)
    reviewed_at: Optional[datetime] = None

    # ─────────────────────────────
    # CHANGE DETAILS
    # ─────────────────────────────
    field: str = Field(index=True)  # e.g. "insurance", "registration", "cash_discount"

    old_value: Optional[str] = None
    new_value: Optional[str] = None

    # ─────────────────────────────
    # REVIEW / WORKFLOW
    # ─────────────────────────────
    status: str = Field(default="pending", description="pending | approved | rejected")

    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None

    # ─────────────────────────────
    # RELATIONSHIPS (optional but useful)
    # ─────────────────────────────
    transaction: Optional["Transaction"] = Relationship()
