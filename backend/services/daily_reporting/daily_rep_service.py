from db.models import DailyBooking, DailyDelivery
from sqlmodel import Session, select
from datetime import date


def display_daily_report(session: Session, report_from: date, report_to: date):

    stmt = select(DailyBooking).where(
        DailyBooking.date >= report_from, DailyBooking.date <= report_to
    )
    bookings = session.exec(stmt).all()

    stmt = select(DailyDelivery).where(
        DailyDelivery.date >= report_from, DailyDelivery.date <= report_to
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


def save_daily_report(session: Session, report_data: dict):
    print("Saving daily report to database...")
    try:
        for booking in report_data.get("bookings", []):
            daily_booking = DailyBooking(
                date=booking["date"],
                outlet_id=booking["outlet_id"],
                number_bookings=booking["number_bookings"],
                file_received=booking["file_received"],
                files_pending=booking["files_pending"],
                files_verified=booking["files_verified"],
            )
            session.add(daily_booking)

        for delivery in report_data.get("deliveries", []):
            daily_delivery = DailyDelivery(
                date=delivery["date"],
                outlet_id=delivery["outlet_id"],
                number_deliveries=delivery["number_deliveries"],
                file_received=delivery["file_received"],
                files_pending=delivery["files_pending"],
                files_verified=delivery["files_verified"],
            )
            session.add(daily_delivery)

        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error saving daily report: {e}")
        return False
