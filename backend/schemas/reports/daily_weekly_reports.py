# services/reports/daily/schemas.py

from datetime import date
from pydantic import BaseModel, Field


class ReconciliationMetrics(BaseModel):
    total_cases_reported: int = 0
    files_received: int = 0
    files_pending: int = 0
    files_incomplete: int = 0
    files_verified: int = 0
    files_approved: str = "-"
    files_rejected: str = "-"
    verification_completion_pct: float = 0.0


class DiscountMetrics(BaseModel):
    total_discount_given: float = 0.0
    discount_as_per_approved_scheme: float = 0.0
    net_excess_discount_amount: float = 0.0

    highest_discount_car_model: str = "-"
    highest_discount_value: float = 0.0

    excess_discount_cases: int = 0
    allowable_discount_cases: int = 0
    excess_discount_verified_cases: int = 0
    zero_discount_cases: int = 0


class PendingFileRow(BaseModel):
    sno: int
    date: str
    name: str
    mobile: str | None = None
    tl: str | None = None


class OutOfScopeRow(BaseModel):
    sno: int
    date: str
    name: str
    mobile: str | None = None
    reason: str | None = None


class DelayedFileRow(BaseModel):
    sno: int
    record_date: str
    receiving_date: str
    delay_days: int
    name: str
    mobile: str | None = None
    tl: str | None = None


class RejectedDeliveredRow(BaseModel):
    sno: int
    date: str
    name: str
    mobile: str | None = None
    tl: str | None = None
    reason: str | None = None


class PendingDocRow(BaseModel):
    sno: int
    date: str
    name: str
    mobile: str | None = None
    tl: str | None = None
    # =====================================
    # COMMON DOC STATUS FIELDS
    # =====================================
    kyc: str | None = None
    vehicle: str | None = None
    quotation: str | None = None
    receipts: str | None = None
    accessories_indent: str | None = None
    exchange: str | None = None
    md_approval: str | None = None
    corp_id: str | None = None
    customer_sign: str | None = None
    ledger: str | None = None
    tax_invoice: str | None = None
    insurance: str | None = None
    rto: str | None = None
    finance: str | None = None
    eval_cert: str | None = None


class StageReport(BaseModel):
    reconciliation: ReconciliationMetrics
    discount: DiscountMetrics


class DailyReportData(BaseModel):
    report_date: str | dict
    booking: StageReport
    delivery: StageReport

    booking_files_pending: list[PendingFileRow] = Field(default_factory=list)
    delivery_files_pending: list[PendingFileRow] = Field(default_factory=list)
    booking_docs_pending: list[PendingDocRow] = Field(default_factory=list)
    delivery_docs_pending: list[PendingDocRow] = Field(default_factory=list)
    booking_out_of_scope: list[OutOfScopeRow] = Field(default_factory=list)
    delivery_out_of_scope: list[OutOfScopeRow] = Field(default_factory=list)
    booking_delay_files: list[DelayedFileRow] = Field(default_factory=list)
    delivery_delay_files: list[DelayedFileRow] = Field(default_factory=list)
    rejected_files_delivered: list[RejectedDeliveredRow] = Field(default_factory=list)
