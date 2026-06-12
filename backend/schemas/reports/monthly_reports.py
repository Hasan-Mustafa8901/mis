# backend\schemas\reports\monthly_reports.py
from pydantic import BaseModel, Field


class DiscountComponentSummary(BaseModel):
    component: str
    amount: float


class ModelDiscountAnalysis(BaseModel):
    car_name: str
    fuel_type: str
    delivered_cases: int
    total_discount: float
    average_discount: float
    total_excess_discount: float
    average_excess_discount: float


# -------- Old Code -------
class OutletModelBreakdown(BaseModel):
    outlet_name: str
    delivered_cases: int
    total_discount: float
    average_discount: float
    total_excess_discount: float
    average_excess_discount: float


class ShowroomModelFuelAnalysis(BaseModel):
    car_name: str
    fuel_type: str
    outlet_breakdown: list[OutletModelBreakdown] = Field(default_factory=list)


# -----------------


class ShowroomModelAnalysisRow(BaseModel):
    car_name: str
    fuel_type: str
    outlet_name: str
    delivered_cases: int
    total_discount: float
    average_discount: float
    total_excess_discount: float
    average_excess_discount: float


class MonthlyStatistics(BaseModel):
    dealership_name: str = ""
    report_period_from: str = ""
    report_period_to: str = ""
    # Reconciliation
    total_vehicle_booked: int = 0
    total_vehicle_delivered: int = 0
    total_out_of_audit_purview: int = 0
    total_delivery_cases_to_be_verified: int = 0
    files_pending_verification: int = 0
    total_delivery_cases_verified: int = 0
    # Category Wise Discount
    category_discounts: list[DiscountComponentSummary] = Field(default_factory=list)
    # Summary
    total_discount_given: float = 0
    maximum_allowable_discount: float = 0
    excess_discount_given: float = 0
    average_discount: float = 0
    average_excess_discount: float = 0
    # Model and Fuel Type wise analysis
    model_discount_analysis: list[ModelDiscountAnalysis] = Field(default_factory=list)
    # Showroom + Model and FuelType wise analysis
    showroom_model_analysis: list[ShowroomModelAnalysisRow] = Field(
        default_factory=list
    )
