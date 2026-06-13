# REVIEW THIS
from datetime import date
from fastapi import APIRouter, Depends
from sqlmodel import Session
from db.models import User
from db.session import get_session
from services.auth.dependencies import get_current_user
from services.auth.scope import get_allowed_outlets, validate_outlet_access
from services.daily_reporting.daily_rep_service import display_daily_report

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

    # ADMIN
    if current_user.role.value == "admin":
        report = display_daily_report(
            session=session,
            report_from=report_from,
            report_to=report_to,
            outlet_id=outlet_id,
            dealership_id=dealership_id,
        )

        return report

    # NON-ADMIN USERS
    allowed_outlets = get_allowed_outlets(current_user)

    # USER REQUESTED SPECIFIC OUTLET
    if outlet_id:
        validate_outlet_access(
            current_user,
            outlet_id,
        )

        report = display_daily_report(
            session=session,
            report_from=report_from,
            report_to=report_to,
            outlet_id=outlet_id,
            dealership_id=None,
        )

        return report

    # NO SPECIFIC OUTLET SELECTED
    # generate combined report for allowed outlets
    report = display_daily_report(
        session=session,
        report_from=report_from,
        report_to=report_to,
        outlet_ids=allowed_outlets,
        dealership_id=None,
    )

    return report
