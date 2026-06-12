# services/reports/monthly/service.py
from sqlmodel import Session
from datetime import date
from schemas.reports.monthly_reports import (
    MonthlyStatistics,
    DiscountComponentSummary,
    ModelDiscountAnalysis,
)

from services.reports.monthly.queries import (
    get_monthly_reconciliation,
    get_category_discounts,
    get_discount_summary,
    get_model_discount_analysis,
    get_dealership_name,
)


class MonthlyReportService:
    @classmethod
    def generate(
        cls, session: Session, start_date: date, end_date: date, dealership_id: int
    ) -> MonthlyStatistics:
        dealership_name = get_dealership_name(
            session=session, dealership_id=dealership_id
        )
        reconciliation = get_monthly_reconciliation(
            session, start_date, end_date, dealership_id
        )

        discount_summary = get_discount_summary(
            session, start_date, end_date, dealership_id
        )

        discount_rows = get_category_discounts(
            session, start_date, end_date, dealership_id
        )
        model_rows = get_model_discount_analysis(
            session, start_date, end_date, dealership_id
        )

        if isinstance(start_date, date):
            report_from = start_date.strftime("%d/%m/%Y")
        if isinstance(end_date, date):
            report_to = end_date.strftime("%d/%m/%Y")

        return MonthlyStatistics(
            dealership_name=dealership_name,
            report_period_from=report_from,
            report_period_to=report_to,
            **reconciliation,
            category_discounts=[
                DiscountComponentSummary(component=name, amount=amount)
                for name, amount in discount_rows.items()
            ],
            model_discount_analysis=[
                ModelDiscountAnalysis(
                    car_name=car_name,
                    fuel_type=fuel_type,
                    delivered_cases=count,
                    total_discount=total_discount,
                    average_discount=(total_discount / count if count else 0),
                    total_excess_discount=(excess_discount),
                    average_excess_discount=(excess_discount / count if count else 0),
                )
                for (
                    car_name,
                    fuel_type,
                    count,
                    total_discount,
                    excess_discount,
                ) in model_rows
            ],
            **discount_summary,
        )
