from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import Optional, Dict, Any
from datetime import date
from pydantic import BaseModel
from db.session import get_session
from services.complaints import query as complaint_service
from db.models import Complaint

router = APIRouter(prefix="/complaints", tags=["Complaints"])

@router.get("/dealerships")
def get_dealerships(session: Session = Depends(get_session)):
    return complaint_service.get_all_dealerships(session)

@router.get("/dealerships/{name}/outlets")
def get_outlets_by_dealership(name: str, session: Session = Depends(get_session)):
    return complaint_service.get_outlets_by_dealership(session, name)

@router.get("/")
def get_complaints(
    dealer: Optional[int] = None,
    outlet: Optional[int] = None,
    status: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    offset: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    filters = {}
    if dealer: filters["dealer"] = dealer
    if outlet: filters["outlet"] = outlet
    if status: filters["status"] = status
    if from_date: filters["from_date"] = from_date
    if to_date: filters["to_date"] = to_date

    rows, total = complaint_service.query_complaints(session, filters, offset, limit)
    return {"data": rows, "total": total}

@router.get("/metrics/status")
def get_complaints_per_status(session: Session = Depends(get_session)):
    return complaint_service.get_complaints_per_status(session)

class RemarkPayload(BaseModel):
    remark: str
    code: str
    submitted_by: str
    complainee_name: Optional[str] = None

@router.post("/remarks")
def submit_remark(payload: RemarkPayload, session: Session = Depends(get_session)):
    success = complaint_service.submit_remarks(
        session, 
        payload.remark, 
        payload.code, 
        payload.submitted_by, 
        payload.complainee_name
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to submit remark")
    return {"message": "Remark submitted successfully"}

@router.post("/save-complaint")
def api_save_complaint(payload: Dict[str, Any], session: Session = Depends(get_session)):
    success, res = complaint_service.save_complaint(session, payload)
    if not success:
        raise HTTPException(status_code=400, detail=res)
    return {"message": "Complaint saved successfully", "code": res}
