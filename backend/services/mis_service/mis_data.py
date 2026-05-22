from datetime import date

from sqlalchemy import and_
from sqlmodel import Session, select
from rich import print

from db.models import (
    MISRecord,
    MISRecordType,
    Transaction,
    Customer,
    Outlet,
    Employee,
    Variant,
)


def get_ebd_data(
    session: Session,
    record_date: date,
    stage: MISRecordType,
    column: str,
    is_footer: bool,
    start_date: date | None,
    end_date: date | None,
    outlet_id: int | None = None,
    outlet_ids: list[int] | None = None,
    dealership_id: int | None = None,
):

    # =====================================================
    # SUB QUERIES
    # =====================================================

    transaction_created_at_sq = (
        select(Transaction.created_at)
        .where(Transaction.id == MISRecord.transaction_id)
        .scalar_subquery()
    )

    if stage == MISRecordType.BOOKING:
        transaction_incomplete = (
            select(Transaction.booking_file_incomplete)
            .where(Transaction.id == MISRecord.transaction_id)
            .scalar_subquery()
        )

        transaction_incomplete_remarks = (
            select(Transaction.booking_file_incomplete_remarks)
            .where(Transaction.id == MISRecord.transaction_id)
            .scalar_subquery()
        )

    else:
        transaction_incomplete = (
            select(Transaction.delivery_file_incomplete)
            .where(Transaction.id == MISRecord.transaction_id)
            .scalar_subquery()
        )

        transaction_incomplete_remarks = (
            select(Transaction.delivery_file_incomplete_remarks)
            .where(Transaction.id == MISRecord.transaction_id)
            .scalar_subquery()
        )

    # =====================================================
    # BASE QUERY
    # =====================================================

    stmt = select(
        MISRecord,
        transaction_created_at_sq.label("transaction_created_at"),
        transaction_incomplete.label("incomplete"),
        transaction_incomplete_remarks.label("incomplete_remarks"),
    ).where(
        MISRecord.type == stage,
    )

    # =====================================================
    # DATE FILTERING
    # =====================================================

    if is_footer:
        stmt = stmt.where(
            MISRecord.record_date.between(
                start_date,
                end_date,
            )
        )

    else:
        stmt = stmt.where(MISRecord.record_date == record_date)

    # =====================================================
    # OUTLET / DEALERSHIP FILTERING
    # =====================================================

    if dealership_id:
        stmt = stmt.where(MISRecord.dealership_id == dealership_id)

    elif outlet_ids:
        stmt = stmt.where(MISRecord.outlet_id.in_(outlet_ids))

    elif outlet_id:
        stmt = stmt.where(MISRecord.outlet_id == outlet_id)

    # =====================================================
    # COLUMN FILTER MAPPING
    # =====================================================

    column_filters = {
        # FILES RECEIVED
        "files_received": (MISRecord.received.is_(True)),
        # FILES PENDING
        "files_pending": and_(
            MISRecord.received.is_(False),
            MISRecord.approved.is_(False),
            MISRecord.rejected.is_(False),
            MISRecord.out_of_scope.is_(False),
        ),
        # FILES OUT OF SCOPE
        "files_out_of_scope": (MISRecord.out_of_scope.is_(True)),
        # FILES SCANNED
        "files_scanned": (MISRecord.received.is_(True)),
        # FILES APPROVED
        "files_approved": (MISRecord.approved.is_(True)),
        # FILES REJECTED
        "files_rejected": (MISRecord.rejected.is_(True)),
        # FILES NOT VERIFIED
        "files_not_verified": and_(
            MISRecord.received.is_(True),
            MISRecord.approved.is_(False),
            MISRecord.rejected.is_(False),
            MISRecord.out_of_scope.is_(False),
        ),
        # FILES TO BE VERIFIED
        "files_to_be_verified": and_(
            MISRecord.received.is_(True),
            MISRecord.out_of_scope.is_(False),
        ),
        # REJECTED BUT DELIVERED
        "rejected_files_delivered": and_(
            MISRecord.rejected.is_(True),
            MISRecord.type == MISRecordType.DELIVERY,
            MISRecord.received.is_(True),
            MISRecord.out_of_scope.is_(False),
        ),
    }

    # =====================================================
    # APPLY COLUMN FILTER
    # =====================================================

    condition = column_filters.get(column)

    if condition is not None:
        stmt = stmt.where(condition)

    # =====================================================
    # ORDERING
    # =====================================================

    stmt = stmt.order_by(
        MISRecord.record_date.asc(),
        MISRecord.customer_name.asc(),
    )

    # =====================================================
    # FETCH
    # =====================================================

    rows = session.exec(stmt).all()

    # RESPONSE

    data = [
        {
            "id": row.id,
            "date": (row.record_date.isoformat() if row.record_date else None),
            "customer_name": (row.customer_name),
            "customer_mobile": (row.customer_mobile),
            "car_model": row.car_model,
            "team_leader": (row.team_leader),
            "received": row.received,
            "receiving_date": (
                row.receiving_date.date().isoformat() if row.receiving_date else None
            ),
            "approved": row.approved,
            "rejected": row.rejected,
            "scanned": row.scanned,
            "scanning_date": (
                row.scanning_date.date().isoformat() if row.scanning_date else None
            ),
            "rejection_reason": (row.rejection_reason),
            "out_of_scope": (row.out_of_scope),
            "out_of_scope_reason": (row.out_of_scope_reason),
            "matching_status": (
                row.matching_status.value if row.matching_status else None
            ),
            "transaction_id": (row.transaction_id),
            "remarks": (row.out_of_scope_reason),
            "entry_date": (
                transaction_created_at.isoformat() if transaction_created_at else None
            ),
            "incomplete": incomplete,
            "incomplete_remarks": (incomplete_remarks),
        }
        for (
            row,
            transaction_created_at,
            incomplete,
            incomplete_remarks,
        ) in rows
    ]

    return data


def get_mis_transactions(
    session: Session,
    record_date: date,
    stage: MISRecordType,
    is_footer: bool,
    start_date: date | None,
    end_date: date | None,
    outlet_id: int | None = None,
    outlet_ids: list[int] | None = None,
    dealership_id: int | None = None,
    incomplete: bool = False,
):

    # =====================================================
    # BASE QUERY
    # =====================================================

    stmt = (
        select(
            Transaction,
            Customer,
            Employee,
            Variant,
            MISRecord,
        )
        .join(
            Customer,
            Customer.id == Transaction.customer_id,
        )
        .join(
            Employee,
            Employee.id == Transaction.sales_executive_id,
        )
        .join(
            Variant,
            Variant.id == Transaction.variant_id,
        )
        .join(
            MISRecord,
            MISRecord.transaction_id == Transaction.id,
        )
    )

    # =====================================================
    # DATE FILTERING
    # =====================================================

    if is_footer:
        stmt = stmt.where(
            MISRecord.record_date.between(
                start_date,
                end_date,
            )
        )

    else:
        stmt = stmt.where(MISRecord.record_date == record_date)

    # =====================================================
    # INCOMPLETE FILTERING
    # =====================================================

    if incomplete:
        if stage == MISRecordType.BOOKING:
            stmt = stmt.where(Transaction.booking_file_incomplete.is_(True))

        else:
            stmt = stmt.where(Transaction.delivery_file_incomplete.is_(True))

    # =====================================================
    # OUTLET / DEALERSHIP FILTERING
    # =====================================================

    # DEALERSHIP
    if dealership_id:
        stmt = stmt.join(
            Outlet,
            Outlet.id == Transaction.outlet_id,
        ).where(Outlet.dealership_id == dealership_id)

    # MULTI OUTLET
    elif outlet_ids:
        stmt = stmt.where(Transaction.outlet_id.in_(outlet_ids))

    # SINGLE OUTLET
    elif outlet_id:
        stmt = stmt.where(Transaction.outlet_id == outlet_id)

    # =====================================================
    # FETCH
    # =====================================================

    rows = session.exec(stmt).all()

    # =====================================================
    # RESPONSE
    # =====================================================

    response = []

    for (
        txn,
        customer,
        employee,
        variant,
        mis_record,
    ) in rows:
        remarks = (
            txn.booking_file_incomplete_remarks
            if stage == MISRecordType.BOOKING
            else txn.delivery_file_incomplete_remarks
        )

        response.append(
            {
                "id": txn.id,
                "date": (
                    mis_record.record_date.isoformat()
                    if mis_record.record_date
                    else None
                ),
                "customer_name": (customer.name),
                "customer_mobile": (customer.mobile_number),
                "team_leader": (employee.name),
                "car_model": (variant.variant_name),
                "entry_date": (
                    txn.created_at.date().isoformat() if txn.created_at else None
                ),
                "remarks": remarks,
                "received": (mis_record.received),
                "receiving_date": (mis_record.receiving_date),
                "out_of_scope_reason": (mis_record.out_of_scope_reason),
                "approved": (mis_record.approved),
                "rejection_reason": (mis_record.rejection_reason),
                "scanning_date": (mis_record.scanning_date),
            }
        )

    return response
