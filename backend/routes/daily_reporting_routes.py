from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import Optional, Dict, Any
from datetime import date
from services.daily_reporting.daily_rep_service import (
    display_daily_report,
    save_daily_report,
)
from db.session import get_session

router = APIRouter(prefix="/daily-report", tags=["Daily Reporting"])


@router.get("/")
def get_daily_report(
    report_from: Optional[date] = None,
    report_to: Optional[date] = None,
    session: Session = Depends(get_session),
):
    if report_from is None or report_to is None:
        report_from = report_to = date.today()

    report = display_daily_report(session, report_from, report_to)

    return report


@router.post("/")
def submit_daily_report(
    payload: Dict[str, Any], session: Session = Depends(get_session)
):

    print("Received daily report:", payload)
    save_daily_report(session, payload)
    return {"message": "Daily report submitted successfully"}
