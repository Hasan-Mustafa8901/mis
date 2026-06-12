# backend\services\reports\monthly\queries.py
from sqlalchemy import func
from sqlmodel import select
from db.models import (
    Dealership,
    Outlet,
    DailyBooking,
    DailyDelivery,
    Transaction,
    TransactionItem,
    Car,
    Variant,
)
from .filters import apply_dealership_filter


def get_dealership_name(session, dealership_id):

    stmt = select(Dealership.name).where(Dealership.id == dealership_id)
    return session.exec(stmt).one()


def get_monthly_reconciliation(session, start_date, end_date, dealership_id):
    booking_stmt = select(
        func.coalesce(func.sum(DailyBooking.number_bookings), 0)
    ).where(DailyBooking.date.between(start_date, end_date))

    booking_stmt = apply_dealership_filter(booking_stmt, DailyBooking, dealership_id)

    delivery_stmt = select(
        func.coalesce(func.sum(DailyDelivery.number_deliveries), 0),
        func.coalesce(func.sum(DailyDelivery.files_out_of_scope), 0),
        func.coalesce(func.sum(DailyDelivery.files_pending), 0),
    ).where(DailyDelivery.date.between(start_date, end_date))

    delivery_stmt = apply_dealership_filter(delivery_stmt, DailyDelivery, dealership_id)

    booking_total = session.exec(booking_stmt).one()

    (delivered, out_of_scope, pending) = session.exec(delivery_stmt).one()

    to_be_verified = delivered - out_of_scope
    verified = to_be_verified - pending

    return {
        "total_vehicle_booked": booking_total,
        "total_vehicle_delivered": delivered,
        "total_out_of_audit_purview": out_of_scope,
        "total_delivery_cases_to_be_verified": to_be_verified,
        "files_pending_verification": pending,
        "total_delivery_cases_verified": verified,
    }


def get_category_discounts(session, start_date, end_date, dealership_id):
    stmt = (
        select(TransactionItem.component_name, func.sum(TransactionItem.actual_amount))
        .join(Transaction, Transaction.id == TransactionItem.transaction_id)
        .where(
            Transaction.stage == "delivery",
            Transaction.delivery_date.between(start_date, end_date),
            TransactionItem.component_type == "discount",
        )
        .group_by(TransactionItem.component_name)
    )
    stmt = apply_dealership_filter(stmt, Transaction, dealership_id)
    rows = session.exec(stmt).all()

    return {name: amount or 0 for name, amount in rows}


def get_discount_summary(session, start_date, end_date, dealership_id):
    stmt = select(
        func.coalesce(func.sum(Transaction.total_actual_discount), 0),
        func.coalesce(func.sum(Transaction.total_allowed_discount), 0),
        func.coalesce(func.sum(Transaction.total_excess_discount), 0),
        func.count(Transaction.id),
    ).where(
        Transaction.stage == "delivery",
        Transaction.delivery_date.between(start_date, end_date),
    )

    stmt = apply_dealership_filter(stmt, Transaction, dealership_id)

    (total_discount, allowable_discount, excess_discount, count_txn) = session.exec(
        stmt
    ).one()

    avg_discount = total_discount / count_txn if count_txn else 0
    avg_excess_discount = excess_discount / count_txn if count_txn else 0

    return {
        "total_discount_given": total_discount,
        "maximum_allowable_discount": allowable_discount,
        "excess_discount_given": excess_discount,
        "average_discount": avg_discount,
        "average_excess_discount": avg_excess_discount,
    }


def get_model_discount_analysis(session, start_date, end_date, dealership_id):
    stmt = (
        select(
            Car.name,
            Variant.fuel_type,
            func.count(Transaction.id),
            func.coalesce(func.sum(Transaction.total_actual_discount), 0),
            func.coalesce(func.sum(Transaction.total_excess_discount), 0),
        )
        .join(Variant, Variant.id == Transaction.variant_id)
        .join(Car, Car.id == Variant.car_id)
        .where(
            Transaction.stage == "delivery",
            Transaction.delivery_date.is_not(None),
            Transaction.delivery_date.between(start_date, end_date),
        )
        .group_by(Car.name, Variant.fuel_type)
        .order_by(Car.name, Variant.fuel_type)
    )
    stmt = apply_dealership_filter(stmt, Transaction, dealership_id)
    rows = session.exec(stmt).all()
    return rows


def get_showroom_model_analysis(session, start_date, end_date, dealership_id):
    stmt = (
        select(
            Car.name,
            Variant.fuel_type,
            Outlet.name,
            func.count(Transaction.id),
            func.coalesce(func.sum(Transaction.total_actual_discount), 0),
            func.coalesce(func.sum(Transaction.total_excess_discount), 0),
        )
        .join(Variant, Variant.id == Transaction.variant_id)
        .join(Car, Car.id == Variant.car_id)
        .join(Outlet, Outlet.id == Transaction.outlet_id)
        .where(
            Transaction.stage == "delivery",
            Transaction.delivery_date.is_not(None),
            Transaction.delivery_date.between(start_date, end_date),
        )
        .group_by(Car.name, Variant.fuel_type, Outlet.name)
        .order_by(Car.name, Variant.fuel_type, Outlet.name)
    )

    if dealership_id is not None:
        stmt = stmt.where(Outlet.dealership_id == dealership_id)

    return session.exec(stmt).all()
