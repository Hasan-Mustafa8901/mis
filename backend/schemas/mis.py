from pydantic import BaseModel


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
