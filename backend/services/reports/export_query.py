# backend\services\reports\export_query.py
import json
from datetime import date
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from sqlalchemy import func

from db.models import (
    Transaction,
    Customer,
    Variant,
    Car,
    Employee,
    Outlet,
    Dealership,
    User,
    TransactionItem,
    TransactionAccessoryLink,
    Accessory,
)


def _apply_export_filters(
    stmt,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    outlet_id: Optional[int] = None,
    dealership_id: Optional[int] = None,
    stage: Optional[str] = None,
    allowed_outlet_ids: Optional[List[int]] = None,
):
    if start_date:
        if stage == "booking":
            stmt = stmt.where(Transaction.booking_date >= start_date)
        elif stage == "delivery":
            stmt = stmt.where(Transaction.delivery_date >= start_date)
        else:
            stmt = stmt.where(Transaction.booking_date >= start_date)

    if end_date:
        if stage == "booking":
            stmt = stmt.where(Transaction.booking_date <= end_date)
        elif stage == "delivery":
            stmt = stmt.where(Transaction.delivery_date <= end_date)
        else:
            stmt = stmt.where(Transaction.booking_date <= end_date)

    if stage:
        stmt = stmt.where(Transaction.stage == stage)

    if outlet_id:
        stmt = stmt.where(Transaction.outlet_id == outlet_id)
    elif dealership_id:
        stmt = stmt.where(Outlet.dealership_id == dealership_id)

    if allowed_outlet_ids is not None:
        stmt = stmt.where(Transaction.outlet_id.in_(allowed_outlet_ids))

    return stmt


def _flatten_dict(data: dict | None, prefix: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}

    result = {}

    for key, value in data.items():
        flat_key = f"{prefix}_{key}"

        if isinstance(value, (dict, list)):
            result[flat_key] = json.dumps(value, ensure_ascii=False)
        else:
            result[flat_key] = value

    return result


def get_export_transactions_count(
    session: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    outlet_id: Optional[int] = None,
    dealership_id: Optional[int] = None,
    stage: Optional[str] = None,
    allowed_outlet_ids: Optional[List[int]] = None,
) -> int:
    """
    Get the total count of transactions matching filters to validate limit.
    """
    stmt = select(func.count(Transaction.id))
    stmt = stmt.join(Outlet, Outlet.id == Transaction.outlet_id)

    if allowed_outlet_ids == []:
        return 0

    stmt = _apply_export_filters(
        stmt,
        start_date=start_date,
        end_date=end_date,
        outlet_id=outlet_id,
        dealership_id=dealership_id,
        stage=stage,
        allowed_outlet_ids=allowed_outlet_ids,
    )

    return session.exec(stmt).one()


def query_export_transactions_batch(
    session: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    outlet_id: Optional[int] = None,
    dealership_id: Optional[int] = None,
    stage: Optional[str] = None,
    allowed_outlet_ids: Optional[List[int]] = None,
    last_id: int | None = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """
    Query database in a flattened format selecting only specific columns needed for MIS Export.
    """
    stmt = select(
        Transaction.id,
        Transaction.status,
        Transaction.stage,
        Transaction.mode,
        Transaction.created_at,
        Transaction.booking_date,
        Transaction.booking_amt,
        Transaction.booking_receipt_num,
        Transaction.booking_file_incomplete,
        Transaction.booking_file_incomplete_remarks,
        Transaction.delivery_date,
        Transaction.delivery_file_incomplete,
        Transaction.delivery_file_incomplete_remarks,
        Transaction.invoice_number,
        Transaction.customer_file_number,
        Transaction.vin_number,
        Transaction.engine_number,
        Transaction.color,
        Transaction.registration_number,
        Transaction.registration_date,
        Transaction.model_year,
        Transaction.team_leader,
        Transaction.total_receivable,
        Transaction.total_received,
        Transaction.balance,
        Transaction.discount_booking,
        Transaction.total_discount_booking,
        Transaction.price_offered_booking,
        Transaction.excess_booking,
        Transaction.adjustment_booking,
        Transaction.total_allowed_discount,
        Transaction.total_actual_discount,
        Transaction.total_excess_discount,
        Transaction.other_discount_booking,
        Transaction.other_discount_delivery,
        Transaction.adjustment_booking,
        Transaction.adjustment_delivery,
        Transaction.payment_status,
        Transaction.invoice_details,
        Transaction.delivery_checklist,
        Transaction.booking_checklist,
        Transaction.audit_info,
        Transaction.payment_details,
        Customer.name.label("customer_name"),
        Customer.mobile_number.label("customer_mobile_number"),
        Customer.alternate_mobile.label("customer_alternate_mobile"),
        Customer.email.label("customer_email"),
        Customer.pan_number.label("customer_pan_number"),
        Customer.aadhar_number.label("customer_aadhar_number"),
        Customer.address.label("customer_address"),
        Customer.city.label("customer_city"),
        Customer.pin_code.label("customer_pin_code"),
        Variant.variant_name,
        Variant.full_variant_name,
        Car.name.label("car_name"),
        Employee.name.label("sales_executive_name"),
        Outlet.name.label("outlet_name"),
        Outlet.dealership_id,
        Dealership.name.label("dealership_name"),
        User.name.label("created_by_name"),
    )

    # Joins
    stmt = stmt.join(Customer, Customer.id == Transaction.customer_id)
    stmt = stmt.join(Variant, Variant.id == Transaction.variant_id)
    stmt = stmt.join(Car, Car.id == Variant.car_id)
    stmt = stmt.join(
        Employee, Employee.id == Transaction.sales_executive_id, isouter=True
    )
    stmt = stmt.join(Outlet, Outlet.id == Transaction.outlet_id)
    stmt = stmt.join(Dealership, Dealership.id == Outlet.dealership_id)
    stmt = stmt.join(User, User.id == Transaction.created_by, isouter=True)

    if allowed_outlet_ids == []:
        return []

    stmt = _apply_export_filters(
        stmt,
        start_date=start_date,
        end_date=end_date,
        outlet_id=outlet_id,
        dealership_id=dealership_id,
        stage=stage,
        allowed_outlet_ids=allowed_outlet_ids,
    )

    if last_id is not None:
        stmt = stmt.where(Transaction.id > last_id)

    stmt = stmt.order_by(Transaction.id.asc())
    stmt = stmt.limit(limit)
    results = session.exec(stmt).all()

    # Convert rows to dicts
    batch_data = [dict(row._mapping) for row in results]
    tx_ids = [d["id"] for d in batch_data]

    if not tx_ids:
        return []

    # Batch retrieve TransactionItems
    items_stmt = select(
        TransactionItem.transaction_id,
        TransactionItem.component_name,
        TransactionItem.actual_amount,
        TransactionItem.allowed_amount,
    ).where(TransactionItem.transaction_id.in_(tx_ids))

    items_result = session.exec(items_stmt).all()

    items_map: Dict[int, Dict[str, Dict[str, float]]] = {}
    for item in items_result:
        tx_id = item.transaction_id
        if tx_id not in items_map:
            items_map[tx_id] = {}
        items_map[tx_id][item.component_name] = {
            "actual": item.actual_amount,
            "allowed": item.allowed_amount,
        }

    # Batch retrieve Accessories
    acc_stmt = (
        select(TransactionAccessoryLink.transaction_id, Accessory.name)
        .join(Accessory, Accessory.id == TransactionAccessoryLink.accessory_id)
        .where(TransactionAccessoryLink.transaction_id.in_(tx_ids))
    )

    acc_result = session.exec(acc_stmt).all()

    acc_map: Dict[int, List[str]] = {}
    for tx_id, acc_name in acc_result:
        if tx_id not in acc_map:
            acc_map[tx_id] = []
        acc_map[tx_id].append(acc_name)

    for row_dict in batch_data:
        tx_id = row_dict["id"]

        row_dict["items"] = items_map.get(tx_id, {})
        row_dict["accessories"] = acc_map.get(tx_id, [])

        row_dict.update(_flatten_dict(row_dict.pop("invoice_details", None), "invoice"))
        row_dict.update(_flatten_dict(row_dict.pop("payment_details", None), "payment"))
        row_dict.update(_flatten_dict(row_dict.pop("audit_info", None), "audit"))

        row_dict.update(
            _flatten_dict(row_dict.pop("booking_checklist", None), "booking_checklist")
        )

        row_dict.update(
            _flatten_dict(
                row_dict.pop("delivery_checklist", None), "delivery_checklist"
            )
        )

    return batch_data
