from db.models import DailyBooking, DailyDelivery, Transaction, Outlet, Dealership
from sqlmodel import Session, select
from datetime import date, datetime
from typing import List


def display_daily_report(
    session: Session,
    report_from: date,
    report_to: date,
    outlet_id: int | None,
    dealership_id: int | None,
):

    booking_stmt = select(DailyBooking).where(
        DailyBooking.date >= report_from,
        DailyBooking.date <= report_to,
    )

    delivery_stmt = select(DailyDelivery).where(
        DailyDelivery.date >= report_from,
        DailyDelivery.date <= report_to,
    )

    # =========================================
    # FILTERING
    # =========================================
    if dealership_id:
        outlets = session.exec(
            select(Outlet).where(Outlet.dealership_id == dealership_id)
        ).all()

        outlet_ids = [o.id for o in outlets]

        booking_stmt = booking_stmt.where(DailyBooking.outlet_id.in_(outlet_ids))

        delivery_stmt = delivery_stmt.where(DailyDelivery.outlet_id.in_(outlet_ids))

    elif outlet_id:
        booking_stmt = booking_stmt.where(DailyBooking.outlet_id == outlet_id)

        delivery_stmt = delivery_stmt.where(DailyDelivery.outlet_id == outlet_id)

    # =======
    # FETCH
    # =======
    bookings = session.exec(booking_stmt).all()

    deliveries = session.exec(delivery_stmt).all()

    # =========
    # RESPONSE
    # =========
    return {
        "bookings": [
            {
                "date": b.date.isoformat(),
                "outlet_id": b.outlet_id,
                "total_count": b.number_bookings,
                "files_received": b.file_received,
                "files_pending": b.files_pending,
                "files_out_of_scope": (b.files_out_of_scope or 0),
                "files_to_be_verified": (b.files_not_verified or 0),
                "files_incomplete": (b.files_incomplete or 0),
                "files_approved": (b.files_approved or 0),
                "files_rejected": (b.files_rejected or 0),
                "files_not_verified": (b.files_not_verified or 0),
            }
            for b in bookings
        ],
        "deliveries": [
            {
                "date": d.date.isoformat(),
                "outlet_id": d.outlet_id,
                "total_count": d.number_deliveries,
                "files_received": d.file_received,
                "files_pending": d.files_pending,
                "files_out_of_scope": (d.files_out_of_scope or 0),
                "files_to_be_verified": (d.files_verified or 0),
                "files_incomplete": (d.files_incomplete or 0),
                "files_approved": (d.files_approved or 0),
                "files_rejected": (d.files_rejected or 0),
                "rejected_files_delivered": (d.rejected_but_delivered or 0),
            }
            for d in deliveries
        ],
    }


def convert_to_date_type(val):
    return datetime.strptime(val, r"%d/%m/%Y").date()


def upsert_booking(session, data):
    stmt = select(DailyBooking).where(
        DailyBooking.date == data["date"],
        DailyBooking.outlet_id == data["outlet_id"],
    )
    existing = session.exec(stmt).first()

    if existing:
        if existing.is_locked:
            return  # 🔒 skip locked rows

        existing.number_bookings = data["number_bookings"]
        existing.file_received = data["file_received"]
        existing.files_pending = data["files_pending"]
        existing.files_verified = data["files_verified"]
        existing.is_locked = True
    else:
        session.add(DailyBooking(**data, is_locked=True))


def upsert_delivery(session, data):
    stmt = select(DailyDelivery).where(
        DailyDelivery.date == data["date"],
        DailyDelivery.outlet_id == data["outlet_id"],
    )
    existing = session.exec(stmt).first()

    if existing:
        if existing.is_locked:
            return

        existing.number_deliveries = data["number_deliveries"]
        existing.file_received = data["file_received"]
        existing.files_pending = data["files_pending"]
        existing.files_verified = data["files_verified"]
        existing.is_locked = True
    else:
        session.add(DailyDelivery(**data, is_locked=True))


def save_daily_report(session: Session, report_data: dict):
    try:
        for booking in report_data.get("bookings", []):
            upsert_booking(session, booking)

        for delivery in report_data.get("deliveries", []):
            upsert_delivery(session, delivery)

        session.commit()
        return True

    except Exception as e:
        session.rollback()
        print(f"Error saving daily report: {e}")
        return False


def get_pending_files(session, report_type: str, report_date: date) -> List[dict]:
    date_field = (
        Transaction.booking_date
        if report_type == "booking"
        else Transaction.delivery_date
    )

    stmt = select(Transaction).where(date_field == report_date)
    records = session.exec(stmt).all()

    result = []
    for record in records:
        # Example logic: pending = no file_received flag or similar
        if not record.file_received:
            result.append(
                {
                    "date": report_date.isoformat(),
                    "customer_name": record.customer_name,
                    "pan_number": record.pan_number,
                    "remarks": "File not received",
                }
            )

    return result


def get_incomplete_files(session, report_type: str, report_date: date) -> List[dict]:
    date_field = (
        Transaction.booking_date
        if report_type == "booking"
        else Transaction.delivery_date
    )

    stmt = select(Transaction).where(date_field == report_date)
    records = session.exec(stmt).all()

    result = []
    for record in records:
        if not record.pan_number or not record.customer_name:
            result.append(
                {
                    "date": report_date.isoformat(),
                    "customer_name": record.customer_name or "—",
                    "pan_number": record.pan_number or "—",
                    "remarks": "Incomplete details",
                }
            )

    return result
