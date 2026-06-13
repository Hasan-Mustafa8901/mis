from datetime import date

from sqlmodel import Session, select

from db.models import Dealership
from services.reports.daily.service import DailyReportService


class CombinedReportService:
    @classmethod
    def generate(cls, session: Session, start_date: date, end_date: date) -> dict:
        """
        Generates payload for CombinedReportGenerator.


            Output format:

            {
                "report_date": ...,
                "scope": "All Dealerships",
                "dealers": [
                    {
                        "name": "...",
                        "booking": {...},
                        "delivery": {...},
                    }
                ]
            }
        """

        if start_date > end_date:
            raise ValueError("start_date cannot be greater than end_date")

        dealerships = session.exec(select(Dealership).order_by(Dealership.name)).all()

        dealers = []

        for dealership in dealerships:
            report = DailyReportService.generate(
                session=session,
                start_date=start_date,
                end_date=end_date,
                dealership_id=dealership.id,
            )
            if (
                report["booking"]["Total Cases Reported"] == 0
                and report["delivery"]["Total Cases Reported"] == 0
            ):
                continue

            dealers.append(
                {
                    "name": dealership.name,
                    "booking": report["booking"],
                    "delivery": report["delivery"],
                }
            )

        if start_date == end_date:
            report_date = end_date.strftime("%d/%m/%Y")
        else:
            report_date = {
                "from": start_date.strftime("%d/%m/%Y"),
                "to": end_date.strftime("%d/%m/%Y"),
            }

        return {
            "report_date": report_date,
            "scope": "All Dealerships",
            "dealers": dealers,
        }
