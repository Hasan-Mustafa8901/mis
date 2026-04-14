from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreateEditRequest(BaseModel):
    transaction_id: int
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    remarks: Optional[str] = None
    requested_by: int


class ApproveEditRequest(BaseModel):
    reviewed_by: int


class RejectEditRequest(BaseModel):
    reviewed_by: int
    rejection_reason: str


class EditRequestResponse(BaseModel):
    id: int
    transaction_id: int
    field: str
    old_value: Optional[str]
    new_value: Optional[str]
    status: str
    remarks: Optional[str]
    rejection_reason: Optional[str]
    requested_by: int
    reviewed_by: Optional[int]
    requested_at: datetime
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True
