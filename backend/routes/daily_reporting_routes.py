from fastapi import APIRouter, Depends
from sqlmodel import Session
from db.models import User
from datetime import date
from services.daily_reporting.daily_rep_service import display_daily_report
from services.auth.dependencies import get_current_user
from db.session import get_session
from rich import print

router = APIRouter(prefix="/report", tags=["Reporting"])


@router.get("/")
def get_daily_report(
    report_from: date | None = None,
    report_to: date | None = None,
    outlet_id: int | None = None,
    dealership_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if report_from is None or report_to is None:
        report_from = report_to = date.today()
    # Change this for role based outlet_id
    # when a audit assistant accesses this
    # extract the outlet_id from current_user
    # While for a ADMIN they will send the outlet_id and dealership_id with payload

    if not outlet_id and not dealership_id:
        outlet_id = current_user.outlet_id

    report = display_daily_report(
        session, report_from, report_to, outlet_id, dealership_id
    )

    return report
