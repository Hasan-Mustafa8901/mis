# # routes/report_routes.py

# from datetime import date

# from fastapi import APIRouter, Depends
# from fastapi.responses import StreamingResponse
# from sqlmodel import Session

# from db.session import get_session

# from services.reports.daily.service import DailyReportService

# from services.reports.daily.daily_report_generator import generate_daily_report


# router = APIRouter(
#     prefix="/reports",
#     tags=["Reports"],
# )


# @router.get("/daily")
# def download_daily_report(
#     start_date: date,
#     end_date: date,
#     dealership_id: int | None = None,
#     outlet_id: int | None = None,
#     session: Session = Depends(get_session),
# ):

#     report_data = DailyReportService.generate(
#         session=session,
#         start_date=start_date,
#         end_date=end_date,
#         dealership_id=dealership_id,
#         outlet_id=outlet_id,
#     )
#     buffer, filename = generate_daily_report(backend_data=report_data)

#     return StreamingResponse(
#         buffer,
#         media_type=(
#             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         ),
#         headers={"Content-Disposition": f'attachment; filename="{filename}"'},
#     )


# routes/report_routes.py
# REVIEW THIS
from datetime import date
from fastapi import APIRouter, Depends  # , HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from db.models import User, UserRole
from db.session import get_session
from services.auth.dependencies import get_current_user
from services.auth.scope import get_allowed_outlets, validate_outlet_access
from services.reports.daily.service import DailyReportService
from services.reports.daily.daily_report_generator import generate_daily_report

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily")
def download_daily_report(
    start_date: date,
    end_date: date,
    dealership_id: int | None = None,
    outlet_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    # ADMIN
    if current_user.role == UserRole.ADMIN:
        report_data = DailyReportService.generate(
            session=session,
            start_date=start_date,
            end_date=end_date,
            dealership_id=dealership_id,
            outlet_id=outlet_id,
        )

        buffer, filename = generate_daily_report(backend_data=report_data)

        return StreamingResponse(
            buffer,
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={"Content-Disposition": (f'attachment; filename="{filename}"')},
        )

    # NON ADMIN USERS
    allowed_outlets = get_allowed_outlets(current_user)

    # USER REQUESTED SPECIFIC OUTLET
    if outlet_id:
        validate_outlet_access(
            current_user,
            outlet_id,
        )

        report_data = DailyReportService.generate(
            session=session,
            start_date=start_date,
            end_date=end_date,
            outlet_id=outlet_id,
        )

    # MULTI OUTLET REPORT
    else:
        report_data = DailyReportService.generate(
            session=session,
            start_date=start_date,
            end_date=end_date,
            outlet_ids=allowed_outlets,
        )

    # GENERATE FILE
    buffer, filename = generate_daily_report(backend_data=report_data)

    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": (f'attachment; filename="{filename}"')},
    )
