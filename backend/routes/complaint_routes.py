from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func, desc
from typing import Dict, Any
from datetime import date
from pydantic import BaseModel
from db.session import get_session
from db.models import User, Complaint, Variant
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


@router.get("/flags")
def api_get_flags():
    return {"data": complaint_service.get_complaint_flags()}


@router.get("/statuses")
def api_get_statuses():
    return {"data": complaint_service.get_complaint_status()}


# Add access check later on when the complaints flow is complete
@router.get("/table")
def get_complaints_table(
    dealer: int | None = None,
    outlet: int | None = None,
    status: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 25,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Complaint).options(
        joinedload(Complaint.customer),
        joinedload(Complaint.variant).joinedload(Variant.car),
        joinedload(Complaint.complainant_dealership),
        joinedload(Complaint.complainant_outlet),
        joinedload(Complaint.complainee_dealership),
        joinedload(Complaint.complainee_outlet),
    )

    # FILTERS
    if dealer:
        stmt = stmt.where(
            or_(
                Complaint.complainant_dealership_id == dealer,
                Complaint.complainee_dealership_id == dealer,
            )
        )

    if outlet:
        stmt = stmt.where(
            or_(
                Complaint.complainant_outlet_id == outlet,
                Complaint.complainee_outlet_id == outlet,
            )
        )

    if status:
        stmt = stmt.where(Complaint.status == status)

    if from_date:
        stmt = stmt.where(Complaint.raised_at >= from_date)

    if to_date:
        stmt = stmt.where(Complaint.raised_at <= to_date)

    # TOTAL COUNT
    count_stmt = select(func.count()).select_from(stmt.subquery())

    total_count = session.exec(count_stmt).one()

    # PAGINATION
    stmt = stmt.order_by(desc(Complaint.raised_at)).offset(offset).limit(limit)

    complaints = session.exec(stmt).all()

    return {
        "rows": [complaint_service.serialize_complaint_rows(c) for c in complaints],
        "total": total_count,
    }


@router.get("/{complaint_id}")
def get_complaint(
    complaint_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    return complaint_service.get_complaint_reconstruction(session, complaint_id)


@router.get("/metrics/status")
def get_complaints_per_status(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return complaint_service.get_complaints_per_status(session)


@router.post("/remarks")
def submit_remark(
    payload: RemarkPayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
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


@router.post("/update-status")
def update_status(
    payload: UpdateStatusRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    updated = complaint_service.update_complaint_status(
        session=session,
        complaint_code=payload.complaint_code,
        status=payload.status,
        current_user=current_user,
    )

    return {
        "message": "Status updated successfully",
        "data": updated,
    }


@router.post("/update-flag")
def update_flag(
    payload: UpdateFlagRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    updated = complaint_service.update_complaint_flag(
        session=session,
        complaint_code=payload.complaint_code,
        flag=payload.flag,
        current_user=current_user,
    )
    return {
        "message": "Flag updated successfully",
        "data": updated,
    }


@router.post("/save-complaint")
def api_save_complaint(
    payload: Dict[str, Any],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from datetime import date
    from rich import print

    # Safely extract nested dictionaries
    quotation_details = payload.get("quotation_details") or {}
    booking_details = payload.get("booking_details") or {}
    remarks_page = payload.get("remarks_page") or {}
    vehicle_details = payload.get("vehicle_details") or {}

    # Parse nested string dates to native datetime.date objects
    if isinstance(quotation_details.get("quotation_date"), str):
        quotation_details["quotation_date"] = date.fromisoformat(
            quotation_details["quotation_date"]
        )

    if isinstance(booking_details.get("instrument_date"), str):
        booking_details["instrument_date"] = date.fromisoformat(
            booking_details["instrument_date"]
        )

    if isinstance(vehicle_details.get("registration_date"), str):
        vehicle_details["registration_date"] = date.fromisoformat(
            vehicle_details["registration_date"]
        )

    # Handle 'date_of_complaint' (mapped from frontend's 'complaint_raised_date')
    if isinstance(remarks_page.get("complaint_raised_date"), str):
        remarks_page["complaint_raised_date"] = date.fromisoformat(
            remarks_page["complaint_raised_date"]
        )

    # Also fallback-check the root layer just in case your service unpacks it early
    if isinstance(payload.get("date_of_complaint"), str):
        payload["date_of_complaint"] = date.fromisoformat(payload["date_of_complaint"])

    print("Corrected nested date payload handled safely:\n", payload)

    success, res = complaint_service.save_complaint(session, payload, current_user)
    if not success:
        print("ERROR:", res)
        raise HTTPException(status_code=400, detail=res)

    return {
        "message": "Complaint saved successfully",
        "code": res,
    }


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
    from backend.services.report.complaint_flash_report import ComplaintFlashReport
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
    from backend.services.report.bookings_report import booking_report_generator
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
    from backend.services.report.bookings_report import delivery_report_generator
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
