from pydantic import BaseModel
from datetime import date


class MISExportRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    month: str | None = None
    outlet_id: int | None = None
    dealership_id: int | None = None
    stage: str | None = None


class DealershipCreate(BaseModel):
    name: str
    code: str


class OutletCreate(BaseModel):
    name: str
    code: str
    dealership_id: int
    address: str | None = None


class EmployeeCreate(BaseModel):
    name: str
    outlet_id: int
    designation: str | None = None


class MISRecordActionPayload(BaseModel):
    mis_record_id: int

    reason: str | None = None
