# services/reports/daily/queries.py

from datetime import date

from sqlmodel import Session, select
from sqlalchemy import func

from db.models import (
    DailyBooking,
    DailyDelivery,
    Transaction,
    Customer,
    MISRecord,
    MISRecordType,
    Variant,
    Car,
)

from schemas.reports.daily_weekly_reports import (
    ReconciliationMetrics,
    DiscountMetrics,
    PendingFileRow,
)
from services.reports.daily.filters import apply_scope_filters
from services.reports.daily.computations import extract_pending_docs


def get_booking_reconciliation(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
) -> ReconciliationMetrics:

    stmt = select(
        func.coalesce(func.sum(DailyBooking.number_bookings), 0).label("total_cases"),
        func.coalesce(func.sum(DailyBooking.file_received), 0).label("files_received"),
        func.coalesce(func.sum(DailyBooking.files_pending), 0).label("files_pending"),
        func.coalesce(func.sum(DailyBooking.files_verified), 0).label("files_verified"),
        func.coalesce(func.sum(DailyBooking.files_approved), 0).label("files_approved"),
        func.coalesce(func.sum(DailyBooking.files_rejected), 0).label("files_rejected"),
    ).where(
        DailyBooking.date.between(
            start_date,
            end_date,
        )
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=DailyBooking,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    (
        total_cases,
        files_received,
        files_pending,
        files_verified,
        files_approved,
        files_rejected,
    ) = session.exec(stmt).one()

    incomplete_stmt = select(func.count(Transaction.id)).where(
        Transaction.booking_date.between(
            start_date,
            end_date,
        ),
        Transaction.booking_file_incomplete == True,
    )

    incomplete_stmt = apply_scope_filters(
        stmt=incomplete_stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    files_incomplete = session.exec(incomplete_stmt).one()

    return ReconciliationMetrics(
        total_cases_reported=total_cases,
        files_received=files_received,
        files_pending=files_pending,
        files_incomplete=files_incomplete,
        files_verified=files_verified,
        files_approved=files_approved,
        files_rejected=files_rejected,
        verification_completion_pct=(
            files_verified / total_cases if total_cases else 0
        ),
    )


def get_delivery_reconciliation(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
) -> ReconciliationMetrics:

    stmt = select(
        func.coalesce(func.sum(DailyDelivery.number_deliveries), 0),
        func.coalesce(func.sum(DailyDelivery.file_received), 0),
        func.coalesce(func.sum(DailyDelivery.files_pending), 0),
        func.coalesce(func.sum(DailyDelivery.files_verified), 0),
    ).where(
        DailyDelivery.date.between(
            start_date,
            end_date,
        )
    )
    stmt = apply_scope_filters(
        stmt=stmt,
        model=DailyDelivery,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    (
        total_cases,
        files_received,
        files_pending,
        files_verified,
    ) = session.exec(stmt).one()

    incomplete_stmt = select(func.count(Transaction.id)).where(
        Transaction.delivery_date.is_not(None),
        Transaction.delivery_date.between(
            start_date,
            end_date,
        ),
        Transaction.delivery_file_incomplete == True,
    )

    incomplete_stmt = apply_scope_filters(
        stmt=incomplete_stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    files_incomplete = session.exec(incomplete_stmt).one()

    return ReconciliationMetrics(
        total_cases_reported=total_cases,
        files_received=files_received,
        files_pending=files_pending,
        files_incomplete=files_incomplete,
        files_verified=files_verified,
        verification_completion_pct=(
            files_verified / total_cases if total_cases else 0
        ),
    )


# =========================================================
# DISCOUNT SUMMARY
# =========================================================


def get_booking_discount_summary(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
) -> DiscountMetrics:

    stmt = select(
        func.coalesce(
            func.sum(Transaction.total_discount_booking),
            0,
        ),
        func.coalesce(
            func.sum(Transaction.discount_booking),
            0,
        ),
        func.coalesce(
            func.sum(Transaction.excess_booking),
            0,
        ),
        func.count(Transaction.id),
    ).where(
        Transaction.booking_date.between(
            start_date,
            end_date,
        )
    )
    stmt = apply_scope_filters(
        stmt=stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )
    (
        total_discount,
        approved_discount,
        excess_discount,
        total_cases,
    ) = session.exec(stmt).one()

    highest_stmt = (
        select(
            Car.name,
            Transaction.total_discount_booking,
        )
        .join(
            Variant,
            Variant.id == Transaction.variant_id,
        )
        .join(
            Car,
            Car.id == Variant.car_id,
        )
        .where(
            Transaction.booking_date.between(
                start_date,
                end_date,
            )
        )
        .order_by(Transaction.total_discount_booking.desc())
        .limit(1)
    )
    highest_stmt = apply_scope_filters(
        stmt=highest_stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    highest = session.exec(highest_stmt).first()

    excess_cases_stmt = select(func.count(Transaction.id)).where(
        Transaction.booking_date.between(
            start_date,
            end_date,
        ),
        Transaction.excess_booking > 0,
    )
    excess_cases_stmt = apply_scope_filters(
        stmt=excess_cases_stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    excess_cases = session.exec(excess_cases_stmt).one()

    zero_discount_stmt = select(func.count(Transaction.id)).where(
        Transaction.booking_date.between(
            start_date,
            end_date,
        ),
        Transaction.total_discount_booking == 0,
    )

    zero_discount_stmt = apply_scope_filters(
        stmt=zero_discount_stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )
    zero_discount_cases = session.exec(zero_discount_stmt).one()

    return DiscountMetrics(
        total_discount_given=total_discount,
        discount_as_per_approved_scheme=approved_discount,
        net_excess_discount_amount=excess_discount,
        highest_discount_car_model=(highest[0] if highest else "-"),
        highest_discount_value=(highest[1] if highest else 0),
        excess_discount_cases=excess_cases,
        allowable_discount_cases=(total_cases - excess_cases),
        excess_discount_verified_cases=excess_cases,
        zero_discount_cases=zero_discount_cases,
    )


def get_delivery_discount_summary(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
) -> DiscountMetrics:

    stmt = select(
        func.coalesce(
            func.sum(Transaction.total_actual_discount),
            0,
        ),
        func.coalesce(
            func.sum(Transaction.total_allowed_discount),
            0,
        ),
        func.coalesce(
            func.sum(Transaction.total_excess_discount),
            0,
        ),
        func.count(Transaction.id),
    ).where(
        Transaction.delivery_date.is_not(None),
        Transaction.delivery_date.between(
            start_date,
            end_date,
        ),
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    (
        total_discount,
        approved_discount,
        excess_discount,
        total_cases,
    ) = session.exec(stmt).one()

    highest_stmt = (
        select(
            Car.name,
            Transaction.total_actual_discount,
        )
        .join(
            Variant,
            Variant.id == Transaction.variant_id,
        )
        .join(
            Car,
            Car.id == Variant.car_id,
        )
        .where(
            Transaction.delivery_date.is_not(None),
            Transaction.delivery_date.between(
                start_date,
                end_date,
            ),
        )
        .order_by(Transaction.total_actual_discount.desc())
        .limit(1)
    )

    highest_stmt = apply_scope_filters(
        stmt=highest_stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    highest = session.exec(highest_stmt).first()

    excess_cases_stmt = select(func.count(Transaction.id)).where(
        Transaction.delivery_date.is_not(None),
        Transaction.delivery_date.between(
            start_date,
            end_date,
        ),
        Transaction.total_excess_discount > 0,
    )

    excess_cases_stmt = apply_scope_filters(
        stmt=excess_cases_stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    excess_cases = session.exec(excess_cases_stmt).one()

    zero_discount_stmt = select(func.count(Transaction.id)).where(
        Transaction.delivery_date.is_not(None),
        Transaction.delivery_date.between(
            start_date,
            end_date,
        ),
        Transaction.total_actual_discount == 0,
    )

    zero_discount_stmt = apply_scope_filters(
        stmt=zero_discount_stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    zero_discount_cases = session.exec(zero_discount_stmt).one()

    return DiscountMetrics(
        total_discount_given=total_discount,
        discount_as_per_approved_scheme=approved_discount,
        net_excess_discount_amount=excess_discount,
        highest_discount_car_model=(highest[0] if highest else "-"),
        highest_discount_value=(highest[1] if highest else 0),
        excess_discount_cases=excess_cases,
        allowable_discount_cases=(total_cases - excess_cases),
        excess_discount_verified_cases=excess_cases,
        zero_discount_cases=zero_discount_cases,
    )


# =========================================================
# PENDING FILES
# =========================================================
def get_booking_pending_files(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
):

    stmt = (
        select(
            MISRecord,
        )
        .where(
            MISRecord.type == MISRecordType.BOOKING,
            MISRecord.record_date.between(
                start_date,
                end_date,
            ),
            MISRecord.received.is_(False),
        )
        .order_by(MISRecord.record_date.desc())
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=MISRecord,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    rows = session.exec(stmt).all()

    result = []

    for idx, row in enumerate(rows, start=1):
        result.append(
            {
                "sno": idx,
                "date": row.record_date.strftime("%d/%m/%Y"),
                "name": row.customer_name,
                "mobile": row.customer_mobile,
                "tl": row.team_leader,
            }
        )

    return result


def get_delivery_pending_files(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
):

    stmt = (
        select(
            MISRecord,
        )
        .where(
            MISRecord.type == MISRecordType.DELIVERY,
            MISRecord.record_date.between(
                start_date,
                end_date,
            ),
            MISRecord.received.is_(False),
        )
        .order_by(MISRecord.record_date.desc())
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=MISRecord,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    rows = session.exec(stmt).all()

    result = []

    for idx, row in enumerate(rows, start=1):
        result.append(
            {
                "sno": idx,
                "date": row.record_date.strftime("%d/%m/%Y"),
                "name": row.customer_name,
                "mobile": row.customer_mobile,
                "tl": row.team_leader,
            }
        )

    return result


## Pending Docs


def get_booking_docs_pending(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
):

    stmt = (
        select(
            Transaction,
            Customer,
        )
        .join(
            Customer,
            Customer.id == Transaction.customer_id,
        )
        .where(
            Transaction.booking_date.between(
                start_date,
                end_date,
            ),
            Transaction.booking_file_incomplete == True,
        )
        .order_by(Transaction.booking_date.desc())
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    rows = session.exec(stmt).all()

    result = []

    for idx, (txn, customer) in enumerate(
        rows,
        start=1,
    ):
        pending_docs = extract_pending_docs(txn.booking_checklist)

        result.append(
            {
                "sno": idx,
                "date": txn.booking_date.strftime("%d/%m/%Y"),
                "name": customer.name,
                "mobile": customer.mobile_number,
                "tl": txn.team_leader,
                # =====================================
                # BOOKING CHECKLIST
                # =====================================
                "kyc": ("Pending" if "kyc" in pending_docs else "Received"),
                "vehicle": ("Pending" if "vehicle" in pending_docs else "Received"),
                "quotation": ("Pending" if "quotation" in pending_docs else "Received"),
                "receipts": ("Pending" if "receipts" in pending_docs else "Received"),
                "accessories_indent": (
                    "Pending" if "accessories_indent" in pending_docs else "Received"
                ),
                "exchange": ("Pending" if "exchange" in pending_docs else "Received"),
                "md_approval": (
                    "Pending" if "md_approval" in pending_docs else "Received"
                ),
                "corp_id": ("Pending" if "corp_id" in pending_docs else "Received"),
                "customer_sign": (
                    "Pending" if "customer_sign" in pending_docs else "Received"
                ),
            }
        )

    return result


def get_delivery_docs_pending(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
):

    stmt = (
        select(
            Transaction,
            Customer,
        )
        .join(
            Customer,
            Customer.id == Transaction.customer_id,
        )
        .where(
            Transaction.delivery_date.is_not(None),
            Transaction.delivery_date.between(
                start_date,
                end_date,
            ),
            Transaction.delivery_file_incomplete == True,
        )
        .order_by(Transaction.delivery_date.desc())
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=Transaction,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    rows = session.exec(stmt).all()

    result = []

    for idx, (txn, customer) in enumerate(
        rows,
        start=1,
    ):
        pending_docs = extract_pending_docs(txn.delivery_checklist)

        result.append(
            {
                "sno": idx,
                "date": txn.delivery_date.strftime("%d/%m/%Y"),
                "name": customer.name,
                "mobile": customer.mobile_number,
                "tl": txn.team_leader,
                # =====================================
                # DELIVERY CHECKLIST
                # =====================================
                "ledger": ("Pending" if "ledger" in pending_docs else "Received"),
                "tax_invoice": (
                    "Pending" if "tax_invoice" in pending_docs else "Received"
                ),
                "accessories_indent": (
                    "Pending" if "accessories_indent" in pending_docs else "Received"
                ),
                "insurance": ("Pending" if "insurance" in pending_docs else "Received"),
                "rto": ("Pending" if "rto" in pending_docs else "Received"),
                "finance": ("Pending" if "finance" in pending_docs else "Received"),
                "eval_cert": ("Pending" if "eval_cert" in pending_docs else "Received"),
            }
        )

    return result


def get_booking_out_of_scope(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
):

    stmt = (
        select(MISRecord)
        .where(
            MISRecord.type == MISRecordType.BOOKING,
            MISRecord.record_date.between(
                start_date,
                end_date,
            ),
            MISRecord.out_of_scope.is_(True),
        )
        .order_by(MISRecord.record_date.desc())
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=MISRecord,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    rows = session.exec(stmt).all()

    result = []

    for idx, row in enumerate(
        rows,
        start=1,
    ):
        result.append(
            {
                "sno": idx,
                "date": row.record_date.strftime("%d/%m/%Y"),
                "name": row.customer_name,
                "mobile": row.customer_mobile,
                "reason": (row.out_of_scope_reason or ""),
            }
        )

    return result


def get_delivery_out_of_scope(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
):

    stmt = (
        select(MISRecord)
        .where(
            MISRecord.type == MISRecordType.DELIVERY,
            MISRecord.record_date.between(
                start_date,
                end_date,
            ),
            MISRecord.out_of_scope.is_(True),
        )
        .order_by(MISRecord.record_date.desc())
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=MISRecord,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    rows = session.exec(stmt).all()

    result = []

    for idx, row in enumerate(
        rows,
        start=1,
    ):
        result.append(
            {
                "sno": idx,
                "date": row.record_date.strftime("%d/%m/%Y"),
                "name": row.customer_name,
                "mobile": row.customer_mobile,
                "reason": (row.out_of_scope_reason or ""),
            }
        )

    return result


def get_delayed_files(
    session: Session,
    start_date: date,
    end_date: date,
    stage: MISRecordType,
    dealership_id: int | None,
    outlet_id: int | None,
):

    stmt = (
        select(MISRecord)
        .where(
            MISRecord.type == stage,
            MISRecord.record_date.between(
                start_date,
                end_date,
            ),
            MISRecord.receiving_date.is_not(None),
        )
        .order_by(MISRecord.record_date.desc())
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=MISRecord,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    rows = session.exec(stmt).all()

    result = []

    sno = 1

    for row in rows:
        if not row.receiving_date:
            continue

        delay_days = (row.receiving_date.date() - row.record_date).days

        if delay_days <= 1:
            continue

        result.append(
            {
                "sno": sno,
                "record_date": (row.record_date.strftime("%d/%m/%Y")),
                "receiving_date": (row.receiving_date.strftime("%d/%m/%Y")),
                "delay_days": delay_days,
                "name": row.customer_name,
                "mobile": row.customer_mobile,
                "tl": row.team_leader,
            }
        )

        sno += 1

    return result


def get_rejected_files_delivered(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
):

    stmt = (
        select(MISRecord)
        .where(
            MISRecord.type == MISRecordType.DELIVERY,
            MISRecord.record_date.between(
                start_date,
                end_date,
            ),
            MISRecord.rejected.is_(True),
        )
        .order_by(MISRecord.record_date.desc())
    )

    stmt = apply_scope_filters(
        stmt=stmt,
        model=MISRecord,
        dealership_id=dealership_id,
        outlet_id=outlet_id,
    )

    rows = session.exec(stmt).all()

    result = []

    for idx, row in enumerate(
        rows,
        start=1,
    ):
        result.append(
            {
                "sno": idx,
                "date": row.record_date.strftime("%d/%m/%Y"),
                "name": row.customer_name,
                "mobile": row.customer_mobile,
                "tl": row.team_leader,
                "reason": (row.rejection_reason or ""),
            }
        )

    return result
