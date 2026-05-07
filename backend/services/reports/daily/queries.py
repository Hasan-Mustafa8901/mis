# services/reports/daily/queries.py

from datetime import date

from sqlmodel import Session, select
from sqlalchemy import func

from db.models import (
    DailyBooking,
    DailyDelivery,
    Transaction,
    Customer,
    Variant,
    Car,
)

from schemas.reports.daily_weekly_reports import (
    ReconciliationMetrics,
    DiscountMetrics,
    PendingFileRow,
)
from services.reports.daily.filters import apply_scope_filters


def get_booking_reconciliation(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
) -> ReconciliationMetrics:

    stmt = select(
        func.coalesce(func.sum(DailyBooking.number_bookings), 0),
        func.coalesce(func.sum(DailyBooking.file_received), 0),
        func.coalesce(func.sum(DailyBooking.files_pending), 0),
        func.coalesce(func.sum(DailyBooking.files_verified), 0),
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
def get_pending_files(
    session: Session,
    start_date: date,
    end_date: date,
    dealership_id: int | None,
    outlet_id: int | None,
) -> list[PendingFileRow]:

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
            (
                (
                    Transaction.booking_date.between(
                        start_date,
                        end_date,
                    )
                )
                & (Transaction.booking_file_incomplete == True)
            )
            | (
                (Transaction.delivery_date.is_not(None))
                & (
                    Transaction.delivery_date.between(
                        start_date,
                        end_date,
                    )
                )
                & (Transaction.delivery_file_incomplete == True)
            )
        )
        .order_by(Transaction.created_at.desc())
        .limit(10)
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
        file_type = "Delivery" if txn.delivery_file_incomplete else "Booking"

        report_date = txn.delivery_date if file_type == "Delivery" else txn.booking_date

        result.append(
            PendingFileRow(
                sno=idx,
                date=report_date.strftime("%d/%m/%Y"),
                name=customer.name,
                pan=customer.pan_number or "",
                type=file_type,
            )
        )

    return result
