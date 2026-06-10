from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    JSON,
    UniqueConstraint,
    Enum as SQLEnum,
)
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from services.utils import get_ist_now, get_ist_today
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    CLIENT = "client"
    AUDIT_ASST = "audit_assistant"


class FuelType(str, Enum):
    CNG = "cng"
    PET = "petrol"
    DIESEL = "diesel"
    EV = "ev"


class ComplaintStatus(str, Enum):
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    DETAILS_PENDING_FROM_COMPLAINANT = "details pending from complainant"
    PENDING_WITH_COMPLAINEE = "pending with complainee"
    PENDING_WITH_COMPLAINEE_STATION_TEAM = "pending with complainee station team"


class ComplaintFlag(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


# tracking duration (in months)
FLAG_DURATIONS = {
    ComplaintFlag.GREEN: 0,
    ComplaintFlag.YELLOW: 1,
    ComplaintFlag.ORANGE: 2,
    ComplaintFlag.RED: 3,
}


class MISRecordType(str, Enum):
    ENQUIRY = "enquiry"
    BOOKING = "booking"
    DELIVERY = "delivery"


class MISMatchingStatus(str, Enum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    MANUAL = "manual"


class ExportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class Dealership(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    code: str

    outlets: List["Outlet"] = Relationship(back_populates="dealership")

    created_at: datetime = Field(default_factory=get_ist_now)


class Outlet(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    code: str = Field(index=True, unique=True)

    dealership_id: int = Field(foreign_key="dealership.id")

    address: Optional[str] = None
    last_serial_no: int = Field(default=0)
    last_serial_month: int = Field(default=0)

    # CORRECT RELATIONSHIPS
    dealership: Optional["Dealership"] = Relationship(back_populates="outlets")
    employees: List["Employee"] = Relationship(back_populates="outlet")
    users: List["User"] = Relationship(back_populates="outlet")
    transactions: List["Transaction"] = Relationship(back_populates="outlet")

    created_at: datetime = Field(default_factory=get_ist_now)


# This table is for client employees data only.
class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    outlet_id: int = Field(foreign_key="outlet.id")
    designation: Optional[str] = None  # e.g., "Sales Executive", "Team Leader"
    created_at: datetime = Field(default_factory=get_ist_now)

    outlet: Optional["Outlet"] = Relationship(back_populates="employees")
    transactions: List["Transaction"] = Relationship(back_populates="sales_executive")


## User Table
class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    username: str = Field(unique=True)
    password_hash: str
    # Old Field for transition
    outlet_id: Optional[int] = Field(default=None, foreign_key="outlet.id")
    role: UserRole = Field(default=UserRole.AUDIT_ASST, index=True)

    # NEW FIELD
    allowed_outlet_ids: list[int] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )

    transactions: list["Transaction"] = Relationship(back_populates="user")
    export_jobs: list["ExportJob"] = Relationship(back_populates="user")
    outlet: Optional["Outlet"] = Relationship(back_populates="users")

    is_active: bool = Field(default=True)
    is_logged_in: bool = Field(default=False)
    created_at: datetime = Field(default_factory=get_ist_now)


#  CORE MASTERS
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
    fuel_type: FuelType
    transmission: Optional[str] = None

    created_at: datetime = Field(default_factory=get_ist_now)

    car: Optional[Car] = Relationship(back_populates="variants")
    price_list_items: List["PriceListItem"] = Relationship(back_populates="variant")
    transactions: List["Transaction"] = Relationship(back_populates="variant")


class Bank(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    is_active: bool = True


#  PRICE LIST & COMPONENTS
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
    model_year: int
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=get_ist_now)

    items: List["PriceListItem"] = Relationship(
        back_populates="price_list",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class PriceListItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    price_list_id: int = Field(foreign_key="pricelist.id", ondelete="CASCADE")
    variant_id: int = Field(foreign_key="variant.id")
    component_id: int = Field(foreign_key="discountcomponent.id")

    allowed_amount: float = 0.0
    conditions: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    price_list: Optional[PriceList] = Relationship(back_populates="items")
    variant: Optional[Variant] = Relationship(back_populates="price_list_items")
    component: Optional[DiscountComponent] = Relationship(
        back_populates="price_list_items"
    )


#  Accessory Master
class Accessory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    listed_price: float

    transactions: List["TransactionAccessoryLink"] = Relationship(
        back_populates="accessory"
    )


class TransactionAccessoryLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    transaction_id: int = Field(foreign_key="transaction.id", ondelete="CASCADE")
    accessory_id: int = Field(foreign_key="accessory.id")

    transaction: Optional["Transaction"] = Relationship(back_populates="accessories")
    accessory: Optional["Accessory"] = Relationship(back_populates="transactions")


#  TRANSACTIONS (MIS CORE)
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    variant_id: int = Field(foreign_key="variant.id")
    outlet_id: int = Field(foreign_key="outlet.id")
    sales_executive_id: int = Field(foreign_key="employee.id")
    bank_id: Optional[int] = Field(default=None, foreign_key="bank.id")

    # Core Transaction Info
    booking_date: date
    booking_amt: float = 0.0
    booking_receipt_num: Optional[str] = None
    booking_file_incomplete: bool = Field(default=False)
    delivery_file_incomplete: bool = Field(default=False)
    booking_file_incomplete_remarks: Optional[str] = None
    delivery_file_incomplete_remarks: Optional[str] = None
    delivery_date: Optional[date] = None
    invoice_number: Optional[str] = Field(default=None, index=True)
    customer_file_number: Optional[str] = None

    stage: str = Field(default="booking")  # booking | delivery
    mode: str = Field(default="booking")  # booking | book_and_delivery
    delivery_checklist: Dict[str, bool] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    booking_checklist: Dict[str, bool] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )

    # Vehicle Instance Details
    vin_number: Optional[str] = Field(default=None, nullable=True)
    engine_number: Optional[str] = Field(default=None, nullable=True)
    color: Optional[str] = None
    model_year: Optional[int] = None
    registration_number: Optional[str] = None
    registration_date: Optional[date] = None

    # MIS Logic Inputs
    team_leader: Optional[str] = None
    conditions: Dict[str, bool] = Field(default_factory=dict, sa_column=Column(JSON))

    # Additional MIS Sections
    exchange_details: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    finance_details: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    audit_info: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # this is important for discount calculation at delivery that is the final discount
    invoice_details: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    payment_details: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )

    total_receivable: float = 0.0
    total_received: float = 0.0
    balance: float = 0.0
    balance_by_user: float = 0.0  # This is the balance calculated by user based on the inputs they have given. This is required to track the difference if any in calculation by MIS and user.
    ledger_adjustment: int = 0
    ledger_adjustment_remarks: str = ""

    # Values at the time of booking
    price_offered_booking: float = 0.0  # Total price that the customer is being offered with all the components that they are buying.
    discount_booking: float = 0.0  # Other Discount Given at the time on booking
    total_discount_booking: float = 0.0  # Total Discount at the time of booking
    excess_booking: float = 0.0  # excess discount at booking
    adjustment_booking: Optional[int] = 0  #
    status: str = "No Excess Discount"  # "No Excess Discount", "Excess"

    # Values at the time of delivery
    total_actual_discount: float = 0.0
    total_allowed_discount: float = 0.0
    total_excess_discount: float = 0.0
    other_discount_delivery: Optional[int] = 0
    adjustment_delivery: Optional[int] = 0
    payment_status: Optional[str] = None

    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=get_ist_now)
    updated_by: Optional[int] = Field(default=None, foreign_key="user.id")
    updated_at: Optional[datetime] = None

    # Relationships
    outlet: Optional[Outlet] = Relationship(back_populates="transactions")
    variant: Optional[Variant] = Relationship(back_populates="transactions")
    sales_executive: Optional[Employee] = Relationship(back_populates="transactions")
    user: Optional["User"] = Relationship(back_populates="transactions")
    customer: Customer = Relationship(back_populates="transactions")
    items: List["TransactionItem"] = Relationship(
        back_populates="transaction",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    accessories: List["TransactionAccessoryLink"] = Relationship(
        back_populates="transaction",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class TransactionItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: int = Field(foreign_key="transaction.id", ondelete="CASCADE")
    component_id: int = Field(foreign_key="discountcomponent.id")

    component_name: str  # Snapshot for history
    component_type: str  # Snapshot

    actual_amount: float = 0.0
    allowed_amount: float = 0.0
    difference: float = 0.0

    transaction: Optional[Transaction] = Relationship(back_populates="items")


class EditRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # RELATIONS
    transaction_id: int = Field(foreign_key="transaction.id", index=True)

    requested_by: Optional[int] = Field(
        foreign_key="user.id"
    )  # TODO: Remove this make it mandatory.
    reviewed_by: Optional[int] = Field(default=None, foreign_key="user.id")

    # TIMESTAMPS
    requested_at: datetime = Field(default_factory=get_ist_now)
    reviewed_at: Optional[datetime] = None

    # CHANGE DETAILS
    field: str = Field(index=True)  # e.g. "insurance", "registration", "cash_discount"
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    # REVIEW / WORKFLOW
    status: str = Field(default="pending", description="pending | approved | rejected")
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None

    # RELATIONSHIPS (optional but useful)
    transaction: Optional["Transaction"] = Relationship()


#  COMPLAINT MANAGEMENT
# Add No of files rejected, accepted, incomplete.
class DailyBooking(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "date",
            "outlet_id",
            name="uq_booking_date_outlet",
        ),
    )
    id: int | None = Field(default=None, primary_key=True)
    date: date
    outlet_id: int = Field(foreign_key="outlet.id")
    number_bookings: int = Field(default=0)
    file_received: int = Field(default=0)
    files_pending: int = Field(default=0)
    files_verified: int = Field(default=0)
    files_out_of_scope: int = Field(default=0)
    files_incomplete: int = Field(default=0)
    files_approved: int = Field(default=0)
    files_rejected: int = Field(default=0)
    files_scanned: int = Field(default=0)
    files_in_mis: int = Field(default=0)
    files_not_verified: int = Field(default=0)
    is_locked: bool = Field(default=False)


class DailyDelivery(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "date",
            "outlet_id",
            name="uq_delivery_date_outlet",
        ),
    )

    id: int | None = Field(
        default=None,
        primary_key=True,
    )

    date: date
    outlet_id: int = Field(foreign_key="outlet.id")
    number_deliveries: int = Field(default=0)
    file_received: int = Field(default=0)
    files_pending: int = Field(default=0)
    files_verified: int = Field(default=0)
    files_out_of_scope: int = Field(default=0)
    files_incomplete: int = Field(default=0)
    files_approved: int = Field(default=0)
    files_rejected: int = Field(default=0)
    files_scanned: int = Field(default=0)
    files_in_mis: int = Field(default=0)
    rejected_but_delivered: int = Field(default=0)
    is_locked: bool = Field(default=False)


class MISRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Core
    record_date: date = Field(index=True)
    type: MISRecordType = Field(
        sa_column=Column(
            SQLEnum(
                MISRecordType,
                values_callable=lambda obj: [e.value for e in obj],
                name="misrecordtype",
            ),
            nullable=False,
            index=True,
        )
    )

    outlet_id: int = Field(foreign_key="outlet.id", index=True)
    dealership_id: int = Field(foreign_key="dealership.id", index=True)

    customer_name: str = Field(index=True)
    customer_mobile: Optional[str] = Field(default=None, index=True)

    car_model: str
    team_leader: Optional[str] = None

    # Workflow
    received: bool = Field(default=False)
    receiving_date: Optional[datetime] = None

    approved: bool = Field(default=False)
    approved_date: Optional[datetime] = None

    scanned: bool = Field(default=False)
    scanning_date: Optional[datetime] = None

    rejected: bool = Field(default=False)
    rejection_reason: Optional[str] = None

    out_of_scope: bool = Field(default=False)
    out_of_scope_reason: Optional[str] = None

    # Transaction Linking
    transaction_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("transaction.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    matching_status: MISMatchingStatus = Field(
        sa_column=Column(
            SQLEnum(
                MISMatchingStatus,
                values_callable=lambda obj: [e.value for e in obj],
                name="mismatchingstatus",
            ),
            nullable=False,
        ),
        default=MISMatchingStatus.UNMATCHED,
    )

    matched_automatically: bool = Field(default=False)

    # Raw upload row
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
    )

    created_at: datetime = Field(default_factory=get_ist_now)


class Remark(SQLModel, table=True):
    id: str = Field(primary_key=True)
    remarks_complainant: Optional[str] = None
    remarks_complainant_aa: Optional[str] = None
    aa_complainee: Optional[str] = None


class Complaint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    complaint_code: str = Field(unique=True)

    complainant_dealership_id: Optional[int] = Field(
        default=None, foreign_key="dealership.id"
    )
    complainant_outlet_id: Optional[int] = Field(default=None, foreign_key="outlet.id")
    complainee_outlet_id: Optional[int] = Field(default=None, foreign_key="outlet.id")
    complainee_dealership_id: Optional[int] = Field(
        default=None, foreign_key="dealership.id"
    )

    status: ComplaintStatus = Field(default=ComplaintStatus.ESCALATED)
    raised_by: int = Field(foreign_key="user.id")

    raised_at: date = Field(default_factory=get_ist_today)
    date_of_complaint: date

    remark_complainee_aa: Optional[str] = None
    remark_admin: Optional[str] = None

    flag: Optional[ComplaintFlag] = None

    customer_id: Optional[int] = Field(default=None, foreign_key="customer.id")
    transaction_id: Optional[int] = Field(default=None, foreign_key="transaction.id")
    remark_id: Optional[str] = Field(default=None, foreign_key="remark.id")

    # --- Vehicle Details ---
    variant_id: Optional[int] = Field(default=None, foreign_key="variant.id")
    car_color: Optional[str] = None

    # --- Quotation Details ---
    quotation_number: Optional[str] = None
    quotation_date: Optional[str] = None
    tcs_amount: Optional[int] = 0
    total_offered_price: Optional[int] = 0
    net_offered_price: Optional[int] = 0

    # --- Booking Details ---
    booking_file_number: Optional[str] = None
    receipt_number: Optional[str] = None
    booking_amount: Optional[int] = 0
    mode_of_payment: Optional[str] = None
    instrument_date: Optional[str] = None
    instrument_number: Optional[str] = None
    bank_name: Optional[str] = None

    # --- Price Details ---
    ex_showroom_price: Optional[int] = 0
    insurance: Optional[int] = 0
    registration_road_tax: Optional[int] = 0
    discount: Optional[float] = 0.0
    accessories_charged: Optional[int] = 0

    # Plain-text overrides for complainee (used when "X" is selected)
    complainee_dealer_text: Optional[str] = None
    complainee_showroom_text: Optional[str] = None

    customer: Optional["Customer"] = Relationship()
    transaction: Optional["Transaction"] = Relationship()
    remark: Optional["Remark"] = Relationship()
    variant: Optional["Variant"] = Relationship()

    complainant_dealership: Optional["Dealership"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Complaint.complainant_dealership_id]"}
    )
    complainant_outlet: Optional["Outlet"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Complaint.complainant_outlet_id]"}
    )
    complainee_dealership: Optional["Dealership"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Complaint.complainee_dealership_id]"}
    )
    complainee_outlet: Optional["Outlet"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Complaint.complainee_outlet_id]"}
    )


class ExportJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_by: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    status: ExportStatus = Field(default=ExportStatus.PENDING, index=True)

    file_name: Optional[str] = None
    file_path: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=get_ist_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    filters: Optional[str] = None

    total_rows: Optional[int] = None  # expected rows before export starts
    processed_rows: int = Field(default=0)  # progress during export
    row_count: Optional[int] = None  # final exported rows

    error_message: Optional[str] = None
    user: Optional["User"] = Relationship(back_populates="export_jobs")
