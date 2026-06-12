# services/reports/daily/service.py

from datetime import date

from sqlmodel import Session

from db.models import MISRecordType, Dealership, Outlet
from schemas.reports.daily_weekly_reports import DailyReportData, StageReport

from services.reports.daily.queries import (
    get_booking_reconciliation,
    get_delivery_reconciliation,
    get_booking_discount_summary,
    get_delivery_discount_summary,
    get_delivery_pending_files,
    get_booking_docs_pending,
    get_booking_pending_files,
    get_delivery_docs_pending,
    get_booking_out_of_scope,
    get_delivery_out_of_scope,
    get_delayed_files,
    get_rejected_files_delivered,
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
            reconciliation=(
                get_booking_reconciliation(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
            discount=(
                get_booking_discount_summary(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
        )

        delivery_stage = StageReport(
            reconciliation=(
                get_delivery_reconciliation(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
            discount=(
                get_delivery_discount_summary(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
        )
        scope: str = cls.get_scope_label(
            session=session, dealership_id=dealership_id, outlet_id=outlet_id
        )
        print(scope)

        # REPORT DATE
        if start_date == end_date:
            report_date = end_date.strftime("%d/%m/%Y")

        else:
            report_date = {
                "from": start_date.strftime("%d/%m/%Y"),
                "to": end_date.strftime("%d/%m/%Y"),
            }

        # REPORT DATA
        report = DailyReportData(
            report_date=report_date,
            scope=scope,
            booking=booking_stage,
            delivery=delivery_stage,
            # BOOKING FILES PENDING
            booking_files_pending=(
                get_booking_pending_files(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
            # DELIVERY FILES PENDING
            delivery_files_pending=(
                get_delivery_pending_files(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
            # BOOKING DOCS PENDING
            booking_docs_pending=(
                get_booking_docs_pending(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
            # DELIVERY DOCS PENDING
            delivery_docs_pending=(
                get_delivery_docs_pending(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
            booking_out_of_scope=(
                get_booking_out_of_scope(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
            delivery_out_of_scope=(
                get_delivery_out_of_scope(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
            booking_delay_files=(
                get_delayed_files(
                    session,
                    start_date,
                    end_date,
                    MISRecordType.BOOKING,
                    dealership_id,
                    outlet_id,
                )
            ),
            delivery_delay_files=(
                get_delayed_files(
                    session,
                    start_date,
                    end_date,
                    MISRecordType.DELIVERY,
                    dealership_id,
                    outlet_id,
                )
            ),
            rejected_files_delivered=(
                get_rejected_files_delivered(
                    session, start_date, end_date, dealership_id, outlet_id
                )
            ),
        )

        # EXCEL PAYLOAD
        return cls._to_excel_payload(report)

    @staticmethod
    def _to_excel_payload(report: DailyReportData) -> dict:

        return {
            "report_date": report.report_date,
            "scope": report.scope,
            "booking": {
                "Total Cases Reported": report.booking.reconciliation.total_cases_reported,
                "Files Received": report.booking.reconciliation.files_received,
                "Files Out of Scope": report.booking.reconciliation.files_out_of_scope,
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
                "Files Out of Scope": report.delivery.reconciliation.files_out_of_scope,
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
            # =====================================
            # BOOKING FILES PENDING
            # =====================================
            "booking_files_pending": [
                row.model_dump() for row in report.booking_files_pending
            ],
            # =====================================
            # DELIVERY FILES PENDING
            # =====================================
            "delivery_files_pending": [
                row.model_dump() for row in report.delivery_files_pending
            ],
            # =====================================
            # BOOKING DOCS PENDING
            # =====================================
            "booking_docs_pending": [
                row.model_dump() for row in report.booking_docs_pending
            ],
            # =====================================
            # DELIVERY DOCS PENDING
            # =====================================
            "delivery_docs_pending": [
                row.model_dump() for row in report.delivery_docs_pending
            ],
            "booking_out_of_scope": [
                row.model_dump() for row in report.booking_out_of_scope
            ],
            "delivery_out_of_scope": [
                row.model_dump() for row in report.delivery_out_of_scope
            ],
            "booking_delay_files": [
                row.model_dump() for row in report.booking_delay_files
            ],
            "delivery_delay_files": [
                row.model_dump() for row in report.delivery_delay_files
            ],
            "rejected_files_delivered": [
                row.model_dump() for row in report.rejected_files_delivered
            ],
        }

    @staticmethod
    def get_scope_label(
        session: Session,
        dealership_id: int | None = None,
        outlet_id: int | None = None,
    ) -> str:
        """
        Returns report scope label.

        Priority:
        1. Outlet
        2. Dealership
        3. All Showrooms
        """

        # OUTLET
        if outlet_id:
            outlet = session.get(
                Outlet,
                outlet_id,
            )

            if outlet:
                return outlet.name

        # DEALERSHIP
        if dealership_id:
            dealership = session.get(
                Dealership,
                dealership_id,
            )

            if dealership:
                return dealership.name
        # Default
        return "All Showrooms"
