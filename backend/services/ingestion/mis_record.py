# backend/services/mis_upload.py

import pandas as pd

from datetime import datetime, date
from sqlmodel import Session, select

from db.models import (
    MISRecord,
    MISRecordType,
    MISMatchingStatus,
    DailyBooking,
    DailyDelivery,
    Transaction,
)

from services.ingestion.excel_parser import (
    load_excel,
    normalize_columns,
)

from services.utils import get_ist_now
from rich import print


class MISUploadService:
    @staticmethod
    def upload_file(
        session: Session,
        file_path: str,
        outlet_id: int,
        dealership_id: int,
    ):

        excel_file = pd.ExcelFile(file_path)

        total_created = 0

        for sheet_name in excel_file.sheet_names:
            # -----------------------------------
            # INFER RECORD TYPE
            # -----------------------------------
            record_type = MISUploadService.infer_record_type(sheet_name)

            # -----------------------------------
            # LOAD SHEET
            # -----------------------------------
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
            )

            df.columns = df.columns.str.lower().str.strip()

            df = normalize_columns(df)

            print(f"\nProcessing Sheet: {sheet_name}")
            print("Normalized Columns:", df.columns)

            # -----------------------------------
            # ITERATE ROWS
            # -----------------------------------
            for _, row in df.iterrows():
                customer_name = MISUploadService.clean_str(row.get("customer_name"))

                if not customer_name:
                    continue

                record_date = MISUploadService.parse_date(row.get("date"))

                if not record_date:
                    continue

                customer_mobile = MISUploadService.clean_mobile(row.get("mobile"))
                car_model = MISUploadService.clean_str(row.get("car_model"))
                team_leader = MISUploadService.clean_str(row.get("team_leader"))
                # -----------------------------------
                # DUPLICATE CHECK
                # -----------------------------------
                existing = session.exec(
                    select(MISRecord).where(
                        MISRecord.record_date == record_date,
                        MISRecord.type == record_type,
                        MISRecord.outlet_id == outlet_id,
                        MISRecord.customer_name == customer_name,
                        MISRecord.car_model == car_model,
                    )
                ).first()

                if existing:
                    print(
                        "Duplicate:",
                        record_date,
                        record_type,
                        customer_name,
                        car_model,
                    )
                    continue

                # -----------------------------------
                # CREATE RECORD
                # -----------------------------------
                record = MISRecord(
                    record_date=record_date,
                    type=record_type,
                    outlet_id=outlet_id,
                    dealership_id=dealership_id,
                    customer_name=customer_name,
                    customer_mobile=customer_mobile,
                    car_model=car_model,
                    team_leader=team_leader,
                    matching_status=MISMatchingStatus.UNMATCHED,
                    raw_data=MISUploadService.make_json_safe(row.to_dict()),
                    created_at=get_ist_now(),
                )
                print(record)
                session.add(record)

                total_created += 1

        # SAVE
        session.commit()

        # SYNC DAILY SUMMARY
        MISUploadService.sync_daily_summary(
            session=session,
            outlet_id=outlet_id,
        )

        return {
            "status": "success",
            "records_created": total_created,
        }

    # =====================================================
    # DAILY SUMMARY SYNC
    # =====================================================

    @staticmethod
    def sync_daily_summary(
        session: Session,
        outlet_id: int,
    ):

        records = session.exec(
            select(MISRecord).where(
                MISRecord.outlet_id == outlet_id,
            )
        ).all()

        grouped = {}

        for record in records:
            group_key = (record.record_date, record.type)

            if group_key not in grouped:
                grouped[group_key] = {
                    "total": 0,
                    "received": 0,
                    "verified": 0,
                    "pending": 0,
                }

            grouped[group_key]["total"] += 1

            if record.received:
                grouped[group_key]["received"] += 1

            if record.approved:
                grouped[group_key]["verified"] += 1

            if not record.approved and not record.rejected and not record.out_of_scope:
                grouped[group_key]["pending"] += 1

        # UPDATE DAILY TABLES
        for (record_date, record_type), counts in grouped.items():
            if record_type == MISRecordType.BOOKING:
                daily = session.exec(
                    select(DailyBooking).where(
                        DailyBooking.date == record_date,
                        DailyBooking.outlet_id == outlet_id,
                    )
                ).first()

                if not daily:
                    daily = DailyBooking(
                        date=record_date,
                        outlet_id=outlet_id,
                        number_bookings=0,
                        file_received=0,
                        files_pending=0,
                        files_verified=0,
                    )
                    session.add(daily)

                daily.number_bookings = counts["total"]
                daily.file_received = counts["received"]
                daily.files_verified = counts["verified"]
                daily.files_pending = counts["pending"]

            elif record_type == MISRecordType.DELIVERY:
                daily = session.exec(
                    select(DailyDelivery).where(
                        DailyDelivery.date == record_date,
                        DailyDelivery.outlet_id == outlet_id,
                    )
                ).first()

                if not daily:
                    daily = DailyDelivery(
                        date=record_date,
                        outlet_id=outlet_id,
                        number_deliveries=0,
                        file_received=0,
                        files_pending=0,
                        files_verified=0,
                    )
                    session.add(daily)

                daily.number_deliveries = counts["total"]
                daily.file_received = counts["received"]
                daily.files_verified = counts["verified"]
                daily.files_pending = counts["pending"]

        session.commit()

    ## Optimized Version
    @staticmethod
    def sync_single_daily_summary(
        session: Session,
        outlet_id: int,
        record_date: date,
        record_type: MISRecordType,
    ):

        # FETCH MIS RECORDS
        records = session.exec(
            select(MISRecord).where(
                MISRecord.outlet_id == outlet_id,
                MISRecord.record_date == record_date,
                MISRecord.type == record_type,
            )
        ).all()

        # COUNTS
        total = len(records)

        files_received = len([r for r in records if r.received])

        files_pending = len([r for r in records if not r.received])

        files_out_of_scope = len([r for r in records if r.out_of_scope])

        files_approved = len([r for r in records if r.approved])
        files_rejected = len([r for r in records if r.rejected])

        files_not_verified = len(
            [
                r
                for r in records
                if (
                    r.received
                    and not r.out_of_scope
                    and not r.approved
                    and not r.rejected
                )
            ]
        )

        files_verified = files_approved + files_rejected

        # INCOMPLETE FILES
        if record_type == MISRecordType.BOOKING:
            files_incomplete = session.exec(
                select(Transaction).where(
                    Transaction.outlet_id == outlet_id,
                    Transaction.booking_date == record_date,
                    Transaction.booking_file_incomplete.is_(True),
                )
            ).all()

        else:
            files_incomplete = session.exec(
                select(Transaction).where(
                    Transaction.outlet_id == outlet_id,
                    Transaction.delivery_date == record_date,
                    Transaction.delivery_file_incomplete.is_(True),
                )
            ).all()

        files_incomplete = len(files_incomplete)

        rejected_but_delivered = len(
            [
                r
                for r in records
                if (r.rejected and record_type == MISRecordType.DELIVERY)
            ]
        )

        # BOOKING SUMMARY
        if record_type == MISRecordType.BOOKING:
            daily = session.exec(
                select(DailyBooking).where(
                    DailyBooking.date == record_date,
                    DailyBooking.outlet_id == outlet_id,
                )
            ).first()

            if not daily:
                daily = DailyBooking(
                    date=record_date,
                    outlet_id=outlet_id,
                    number_bookings=0,
                    file_received=0,
                    files_pending=0,
                    files_verified=0,
                    files_out_of_scope=0,
                    files_incomplete=0,
                    files_approved=0,
                    files_rejected=0,
                    files_not_verified=0,
                )

                session.add(daily)

            daily.number_bookings = total

            daily.file_received = files_received

            daily.files_pending = files_pending

            daily.files_verified = files_verified

            daily.files_out_of_scope = files_out_of_scope

            daily.files_incomplete = files_incomplete

            daily.files_approved = files_approved

            daily.files_rejected = files_rejected

            daily.files_not_verified = files_not_verified

        # DELIVERY SUMMARY
        elif record_type == MISRecordType.DELIVERY:
            daily = session.exec(
                select(DailyDelivery).where(
                    DailyDelivery.date == record_date,
                    DailyDelivery.outlet_id == outlet_id,
                )
            ).first()

            if not daily:
                daily = DailyDelivery(
                    date=record_date,
                    outlet_id=outlet_id,
                    number_deliveries=0,
                    file_received=0,
                    files_pending=0,
                    files_verified=0,
                    files_out_of_scope=0,
                    files_incomplete=0,
                    files_approved=0,
                    files_rejected=0,
                    rejected_but_delivered=0,
                )

                session.add(daily)

            daily.number_deliveries = total

            daily.file_received = files_received

            daily.files_pending = files_pending

            daily.files_verified = files_verified

            daily.files_out_of_scope = files_out_of_scope

            daily.files_incomplete = files_incomplete

            daily.files_approved = files_approved

            daily.files_rejected = files_rejected

            daily.rejected_but_delivered = rejected_but_delivered

        # SAVE
        session.commit()

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def clean_str(value):

        if pd.isna(value):
            return None

        return str(value).strip()

    @staticmethod
    def clean_mobile(value):

        if pd.isna(value):
            return None

        mobile = "".join(filter(str.isdigit, str(value)))

        if len(mobile) < 10:
            return None
        if mobile.startswith(("+91", "0")):
            return mobile[-10:]
        return mobile

    @staticmethod
    def parse_date(value):

        if pd.isna(value):
            return None

        if isinstance(value, datetime):
            return value.date()

        try:
            return pd.to_datetime(value).date()
        except Exception:
            return None

    @staticmethod
    def infer_record_type(sheet_name: str) -> MISRecordType:

        normalized = sheet_name.lower().strip()

        if "booking" in normalized:
            return MISRecordType.BOOKING

        if "delivery" in normalized:
            return MISRecordType.DELIVERY

        if "enquiry" in normalized:
            return MISRecordType.ENQUIRY

        raise ValueError(
            f"Could not infer MIS record type from sheet name: {sheet_name}"
        )

    @staticmethod
    def make_json_safe(data):

        cleaned = {}

        for key, value in data.items():
            if pd.isna(value):
                cleaned[key] = None

            elif isinstance(value, pd.Timestamp):
                cleaned[key] = value.isoformat()

            else:
                cleaned[key] = value

        return cleaned
