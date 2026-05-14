from datetime import date, datetime

from sqlalchemy import and_
from sqlmodel import Session, select

from db.models import MISRecord, MISRecordType, Transaction, Customer, Outlet


def get_mis_data(
    session: Session,
    record_date: date,
    stage: MISRecordType,
    column: str,
    outlet_id: int | None = None,
    dealership_id: int | None = None,
):

    # =====================================================
    # BASE QUERY
    # =====================================================
    stmt = select(MISRecord).where(
        MISRecord.record_date == record_date,
        MISRecord.type == stage,
    )

    # =====================================================
    # OPTIONAL FILTERS
    # =====================================================
    if outlet_id:
        stmt = stmt.where(MISRecord.outlet_id == outlet_id)

    if dealership_id:
        stmt = stmt.where(MISRecord.dealership_id == dealership_id)

    # =====================================================
    # COLUMN FILTER MAPPING
    # =====================================================
    column_filters = {
        # ---------------------------------------------
        # FILES RECEIVED
        # ---------------------------------------------
        "files_received": (MISRecord.received.is_(True)),
        # ---------------------------------------------
        # FILES PENDING
        # ---------------------------------------------
        "files_pending": and_(
            MISRecord.received.is_(False),
            MISRecord.approved.is_(False),
            MISRecord.rejected.is_(False),
            MISRecord.out_of_scope.is_(False),
        ),
        # ---------------------------------------------
        # FILES OUT OF SCOPE
        # ---------------------------------------------
        "files_out_of_scope": (MISRecord.out_of_scope.is_(True)),
        # ---------------------------------------------
        # FILES INCOMPLETE
        # ---------------------------------------------
        # "files_incomplete": (Transaction.incomplete.is_(True)),
        # ---------------------------------------------
        # FILES APPROVED
        # ---------------------------------------------
        "files_approved": (MISRecord.approved.is_(True)),
        # ---------------------------------------------
        # FILES REJECTED
        # ---------------------------------------------
        "files_rejected": (MISRecord.rejected.is_(True)),
        # ---------------------------------------------
        # FILES NOT VERIFIED
        # ---------------------------------------------
        "files_not_verified": and_(
            MISRecord.received.is_(True),
            MISRecord.approved.is_(False),
            MISRecord.rejected.is_(False),
            MISRecord.out_of_scope.is_(False),
        ),
        # ---------------------------------------------
        # FILES TO BE VERIFIED
        # ---------------------------------------------
        "files_to_be_verified": and_(
            MISRecord.received.is_(True),
            MISRecord.out_of_scope.is_(False),
        ),
        # ---------------------------------------------
        # REJECTED BUT DELIVERED
        # ---------------------------------------------
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
    stmt = stmt.order_by(MISRecord.customer_name.asc())

    # =====================================================
    # FETCH
    # =====================================================
    rows = session.exec(stmt).all()

    return [
        {
            "id": row.id,
            "date": (row.record_date.isoformat() if row.record_date else None),
            "customer_name": row.customer_name,
            "customer_mobile": row.customer_mobile,
            "car_model": row.car_model,
            "team_leader": row.team_leader,
            "received": row.received,
            "receiving_date": (
                row.receiving_date.date().isoformat() if row.receiving_date else None
            ),
            "approved": row.approved,
            "rejected": row.rejected,
            "rejection_reason": row.rejection_reason,
            "out_of_scope": row.out_of_scope,
            "out_of_scope_reason": row.out_of_scope_reason,
            "matching_status": (
                row.matching_status.value if row.matching_status else None
            ),
            "transaction_id": row.transaction_id,
            "remarks": row.out_of_scope_reason,
        }
        for row in rows
    ]


def get_incomplete_transactions(
    session: Session,
    record_date: date,
    stage: MISRecordType,
    outlet_id: int | None = None,
    dealership_id: int | None = None,
):

    # =====================================================
    # BASE QUERY
    # =====================================================
    stmt = select(
        Transaction,
        Customer,
    ).join(
        Customer,
        Customer.id == Transaction.customer_id,
    )

    # =====================================================
    # BOOKING
    # =====================================================
    if stage == MISRecordType.BOOKING:
        stmt = stmt.where(
            Transaction.booking_date == record_date,
            Transaction.booking_file_incomplete.is_(True),
        )

    # =====================================================
    # DELIVERY
    # =====================================================
    else:
        stmt = stmt.where(
            Transaction.delivery_date == record_date,
            Transaction.delivery_file_incomplete.is_(True),
        )

    # =====================================================
    # OUTLET FILTER
    # =====================================================
    if outlet_id:
        stmt = stmt.where(Transaction.outlet_id == outlet_id)

    # =====================================================
    # DEALERSHIP FILTER
    # =====================================================
    elif dealership_id:
        stmt = stmt.join(
            Outlet,
            Outlet.id == Transaction.outlet_id,
        ).where(Outlet.dealership_id == dealership_id)

    # =====================================================
    # FETCH
    # =====================================================
    rows = session.exec(stmt).all()

    # =====================================================
    # RESPONSE
    # =====================================================
    response = []

    for txn, customer in rows:
        remarks = (
            txn.booking_file_incomplete_remarks
            if stage == MISRecordType.BOOKING
            else txn.delivery_file_incomplete_remarks
        )

        response.append(
            {
                "id": txn.id,
                "date": (record_date.isoformat() if record_date else None),
                "customer_name": customer.name,
                "customer_mobile": customer.mobile_number,
                "team_leader": txn.team_leader,
                "remarks": remarks,
            }
        )

    return response
