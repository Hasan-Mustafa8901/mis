from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from typing import Optional, Dict, Any
from datetime import date
from pydantic import BaseModel
from db.session import get_session
from db.models import User
from services.complaints import query as complaint_service
from services.auth.dependencies import get_current_user
from schemas.complaints import UpdateStatusRequest, UpdateFlagRequest, RemarkPayload

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
    session: Session = Depends(get_session),
):
    filters = {}
    if dealer:
        filters["dealer"] = dealer
    if outlet:
        filters["outlet"] = outlet
    if status:
        filters["status"] = status
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date

    rows, total = complaint_service.query_complaints(session, filters, offset, limit)
    return {"data": rows, "total": total}


@router.get("/metrics/status")
def get_complaints_per_status(session: Session = Depends(get_session)):
    return complaint_service.get_complaints_per_status(session)


@router.post("/remarks")
def submit_remark(
    payload: RemarkPayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    print(payload)
    success = complaint_service.submit_remarks(
        session=session,
        remark=payload.remark,
        code=payload.code,
        submitted_by=payload.submitted_by,
        user=current_user,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to submit remark")
    return {"message": "Remark submitted successfully"}


@router.get("/flags")
def api_get_flags():
    return {"data": complaint_service.get_complaint_flags()}


@router.get("/statuses")
def api_get_statuses():
    return {"data": complaint_service.get_complaint_status()}


@router.post("/update-status")
def update_status(
    payload: UpdateStatusRequest,
    session: Session = Depends(get_session),
):
    updated = complaint_service.update_complaint_status(
        session=session,
        complaint_code=payload.complaint_code,
        status=payload.status,
    )

    return {
        "message": "Status updated successfully",
        "data": updated,
    }


@router.post("/update-flag")
def update_flag(
    payload: UpdateFlagRequest,
    session: Session = Depends(get_session),
):
    updated = complaint_service.update_complaint_flag(
        session=session,
        complaint_code=payload.complaint_code,
        flag=payload.flag,
    )
    return {
        "message": "Flag updated successfully",
        "data": updated,
    }


@router.post("/save-complaint")
def api_save_complaint(
    payload: Dict[str, Any], session: Session = Depends(get_session)
):
    success, res = complaint_service.save_complaint(session, payload)
    if not success:
        raise HTTPException(status_code=400, detail=res)
    return {"message": "Complaint saved successfully", "code": res}


class FlashReportPayload(BaseModel):
    complaint_no: str
    date_of_complaint: str
    date_of_resolution: str
    dealer: str
    showroom: str
    point_of_complaint: str
    booking_date: str
    complainant_name: str
    customer_name: str
    designation_complainant: str
    complainant_aa: str
    complainant_aa_designation: str
    car_name: str
    price_offered: str
    reviewer: str
    reviewer_designation: str
    audit_procedure: str
    audit_findings: str
    audit_evidence: str
    conclusion: str


@router.post("/report/flash")
def generate_flash_report(payload: FlashReportPayload):
    from services.complaints.report.complaint_flash_report import ComplaintFlashReport
    from io import BytesIO

    try:
        pdf = ComplaintFlashReport()
        pdf.build(payload.model_dump())
        buffer = BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=flash_report.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class ExcelReportPayload(BaseModel):
    data: list[Dict[str, Any]]
    start_date: str
    end_date: str


@router.post("/report/bookings")
def generate_bookings_report(payload: ExcelReportPayload):
    from services.complaints.report.bookings_report import booking_report_generator
    import pandas as pd
    from datetime import datetime

    df = pd.DataFrame(payload.data)
    start = datetime.strptime(payload.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(payload.end_date, "%Y-%m-%d").date()
    try:
        buffer, filename = booking_report_generator(df, start, end)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/report/deliveries")
def generate_deliveries_report(payload: ExcelReportPayload):
    from services.complaints.report.bookings_report import delivery_report_generator
    import pandas as pd
    from datetime import datetime

    df = pd.DataFrame(payload.data)
    start = datetime.strptime(payload.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(payload.end_date, "%Y-%m-%d").date()
    try:
        buffer, filename = delivery_report_generator(df, start, end)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
