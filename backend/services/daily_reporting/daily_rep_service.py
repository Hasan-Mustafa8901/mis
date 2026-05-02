from db.models import DailyBooking, DailyDelivery, Transaction
from sqlmodel import Session, select
from datetime import date
from typing import List


def display_daily_report(
    session: Session, report_from: date, report_to: date, outlet_id
):

    stmt = select(DailyBooking).where(
        DailyBooking.date >= report_from,
        DailyBooking.date <= report_to,
        DailyBooking.outlet_id == outlet_id,
    )
    bookings = session.exec(stmt).all()

    stmt = select(DailyDelivery).where(
        DailyDelivery.date >= report_from,
        DailyDelivery.date <= report_to,
        DailyDelivery.outlet_id == outlet_id,
    )
    deliveries = session.exec(stmt).all()

    report = {
        "date": report_from.isoformat(),
        "bookings": [
            {
                "outlet_id": b.outlet_id,
                "number_bookings": b.number_bookings,
                "file_received": b.file_received,
                "files_pending": b.files_pending,
                "files_verified": b.files_verified,
            }
            for b in bookings
        ],
        "deliveries": [
            {
                "outlet_id": d.outlet_id,
                "number_deliveries": d.number_deliveries,
                "file_received": d.file_received,
                "files_pending": d.files_pending,
                "files_verified": d.files_verified,
            }
            for d in deliveries
        ],
    }
    return report


def convert_to_date_type(val):
    from datetime import datetime

    return datetime.strptime(val, r"%d/%m/%Y").date()


from sqlmodel import select


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
