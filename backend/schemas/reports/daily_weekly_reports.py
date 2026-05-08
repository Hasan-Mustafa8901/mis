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
    pan: str
    type: str


class PendingDocRow(BaseModel):
    sno: int
    date: str
    name: str
    pan: str
    docs: str


class StageReport(BaseModel):
    reconciliation: ReconciliationMetrics
    discount: DiscountMetrics


class DailyReportData(BaseModel):
    report_date: str | dict

    booking: StageReport
    delivery: StageReport

    files_pending: list[PendingFileRow] = Field(default_factory=list)

    docs_pending: list[PendingDocRow] = Field(default_factory=list)
