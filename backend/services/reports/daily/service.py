# services/reports/daily/service.py

from datetime import date

from sqlmodel import Session

from schemas.reports.daily_weekly_reports import (
    DailyReportData,
    StageReport,
)

from services.reports.daily.queries import (
    get_booking_reconciliation,
    get_delivery_reconciliation,
    get_booking_discount_summary,
    get_delivery_discount_summary,
    get_pending_files,
)


class DailyReportService:
    @classmethod
    def generate(
        cls,
        session: Session,
        start_date: date,
        end_date: date,
        dealership_id: int | None = None,
        outlet_id: int | None = None,
    ) -> dict:

        if start_date > end_date:
            raise ValueError("start_date cannot be greater than end_date")

        booking_stage = StageReport(
            reconciliation=get_booking_reconciliation(
                session, start_date, end_date, dealership_id, outlet_id
            ),
            discount=get_booking_discount_summary(
                session,
                start_date,
                end_date,
                dealership_id,
                outlet_id,
            ),
        )

        delivery_stage = StageReport(
            reconciliation=get_delivery_reconciliation(
                session, start_date, end_date, dealership_id, outlet_id
            ),
            discount=get_delivery_discount_summary(
                session, start_date, end_date, dealership_id, outlet_id
            ),
        )

        report = DailyReportData(
            report_date=end_date.strftime("%d/%m/%Y"),
            booking=booking_stage,
            delivery=delivery_stage,
            files_pending=get_pending_files(
                session,
                start_date,
                end_date,
                dealership_id,
                outlet_id,
            ),
            docs_pending=[],
        )

        return cls._to_excel_payload(report)

    @staticmethod
    def _to_excel_payload(
        report: DailyReportData,
    ) -> dict:

        return {
            "report_date": report.report_date,
            "booking": {
                "Total Cases Reported": report.booking.reconciliation.total_cases_reported,
                "Files Received": report.booking.reconciliation.files_received,
                "Files Pending": report.booking.reconciliation.files_pending,
                "Files Incomplete": report.booking.reconciliation.files_incomplete,
                "Files Verified": report.booking.reconciliation.files_verified,
                "Files Approved": report.booking.reconciliation.files_approved,
                "Files Rejected": report.booking.reconciliation.files_rejected,
                "Verification Completion %": report.booking.reconciliation.verification_completion_pct,
                "Total Discount Given": report.booking.discount.total_discount_given,
                "Discount as per Approved Scheme": report.booking.discount.discount_as_per_approved_scheme,
                "Net Excess Discount Amount": report.booking.discount.net_excess_discount_amount,
                "Highest Discount Car Model": report.booking.discount.highest_discount_car_model,
                "Highest Discount Value": report.booking.discount.highest_discount_value,
                "Excess Discount Cases": report.booking.discount.excess_discount_cases,
                "Allowable Discount Cases (out of Verified cases)": report.booking.discount.allowable_discount_cases,
                "Excess Discount Cases(out of Verified cases)": report.booking.discount.excess_discount_verified_cases,
                "Zero Discount Cases(out of Verified cases)": report.booking.discount.zero_discount_cases,
            },
            "delivery": {
                "Total Cases Reported": report.delivery.reconciliation.total_cases_reported,
                "Files Received": report.delivery.reconciliation.files_received,
                "Files Pending": report.delivery.reconciliation.files_pending,
                "Files Incomplete": report.delivery.reconciliation.files_incomplete,
                "Files Verified": report.delivery.reconciliation.files_verified,
                "Files Approved": report.delivery.reconciliation.files_approved,
                "Files Rejected": report.delivery.reconciliation.files_rejected,
                "Verification Completion %": report.delivery.reconciliation.verification_completion_pct,
                "Total Discount Given": report.delivery.discount.total_discount_given,
                "Discount as per Approved Scheme": report.delivery.discount.discount_as_per_approved_scheme,
                "Net Excess Discount Amount": report.delivery.discount.net_excess_discount_amount,
                "Highest Discount Car Model": report.delivery.discount.highest_discount_car_model,
                "Highest Discount Value": report.delivery.discount.highest_discount_value,
                "Excess Discount Cases": report.delivery.discount.excess_discount_cases,
                "Allowable Discount Cases (out of Verified cases)": report.delivery.discount.allowable_discount_cases,
                "Excess Discount Cases(out of Verified cases)": report.delivery.discount.excess_discount_verified_cases,
                "Zero Discount Cases(out of Verified cases)": report.delivery.discount.zero_discount_cases,
            },
            "files_pending": [row.model_dump() for row in report.files_pending],
            "docs_pending": [row.model_dump() for row in report.docs_pending],
        }
