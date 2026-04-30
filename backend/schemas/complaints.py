from pydantic import BaseModel
from typing import Optional
from db.models import UserRole, ComplaintStatus, ComplaintFlag, User


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
