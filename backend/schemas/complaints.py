from datetime import date
from pydantic import BaseModel
from typing import Optional
from db.models import UserRole, ComplaintStatus, ComplaintFlag


class UpdateStatusRequest(BaseModel):
    complaint_code: str
    status: ComplaintStatus


class UpdateFlagRequest(BaseModel):
    complaint_code: str
    flag: ComplaintFlag


class RemarkPayload(BaseModel):
    remark: str
    code: str
    submitted_by: Optional[UserRole] = UserRole.ADMIN


class CustomerDetails(BaseModel):
    customer_name: str | None = None
    contact_number: str | None = None
    address: str | None = None
    city: str | None = None
    pin: str | None = None
    pan: str | None = None
    aadhar: str | None = None
    email: str | None = None
    relative_name: str | None = None
    other_id: str | None = None


class BookingDetails(BaseModel):
    booking_file_number: str | None = None
    receipt_number: str | None = None
    booking_amount: int | None = None
    mode_of_payment: str | None = None
    instrument_date: date | None = None
    instrument_number: str | None = None
    bank_name: str | None = None


class QuotationDetails(BaseModel):
    quotation_number: str | None = None
    quotation_date: date | None = None
    tcs_amount: int | None = None
    total_offered_price: int | None = None
    net_offered_price: int | None = None


class VehicleDetails(BaseModel):
    car_color: str | None = None
    engine_number: str | None = None
    registration_number: str | None = None
    registration_date: date | None = None
    vin_number: str | None = None


class PriceInfo(BaseModel):
    ex_showroom_price: int | None = None
    insurance: int | None = None
    registration_road_tax: int | None = None
    discount: float | None = None
    accessories_charged: int | None = None


class RemarksPage(BaseModel):
    complaint_raised_date: date | None = None
    remarks_by_complainant: str | None = None
    remarks_by_aa: str | None = None
    aa_name: str | None = None


class ComplaintUpdatePayload(BaseModel):
    variant_id: int | None = None
    employee_id: int | None = None

    customer_details: CustomerDetails | None = None
    booking_details: BookingDetails | None = None
    quotation_details: QuotationDetails | None = None
    vehicle_details: VehicleDetails | None = None
    price_info: PriceInfo | None = None
    remarks_page: RemarksPage | None = None
