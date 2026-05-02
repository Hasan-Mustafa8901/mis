from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from db.models import User
from datetime import date
from services.daily_reporting.daily_rep_service import (
    display_daily_report,
    save_daily_report,
    get_incomplete_files,
    get_pending_files,
)
from services.auth.dependencies import get_current_user
from db.session import get_session

router = APIRouter(prefix="/daily-report", tags=["Daily Reporting"])


@router.get("/")
def get_daily_report(
    report_from: date | None = None,
    report_to: date | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if report_from is None or report_to is None:
        report_from = report_to = date.today()

    outlet_id = current_user.outlet_id

    report = display_daily_report(session, report_from, report_to, outlet_id)

    return report


@router.post("/")
def submit_daily_report(
    payload: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    outlet_id = current_user.outlet_id
    role = current_user.role

    for b in payload.get("bookings", []):
        b[outlet_id] = outlet_id

    for d in payload.get("deliveries", []):
        d[outlet_id] = outlet_id

    print("Received daily report:", payload)
    save_daily_report(session, payload)
    return {"message": "Daily report submitted successfully"}


@router.get("/pending")
def get_pending(
    type: str = Query(...),
    date: date = Query(...),
    session: Session = Depends(get_session),
):
    return get_pending_files(session, type, date)


@router.get("/incomplete")
def get_incomplete(
    type: str = Query(...),
    date: date = Query(...),
    session: Session = Depends(get_session),
):
    return get_incomplete_files(session, type, date)
