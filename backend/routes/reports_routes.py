# routes/report_routes.py

from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from db.session import get_session

from services.reports.daily.service import DailyReportService

from services.reports.daily.daily_report_generator import generate_daily_report


router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.get("/daily")
def download_daily_report(
    start_date: date,
    end_date: date,
    dealership_id: int | None = None,
    outlet_id: int | None = None,
    session: Session = Depends(get_session),
):

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
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
