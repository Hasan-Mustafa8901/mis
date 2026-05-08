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

                record_date = MISUploadService.parse_date(row.get("record_date"))

                if not record_date:
                    continue

                customer_mobile = MISUploadService.clean_mobile(
                    row.get("customer_mobile")
                )

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

                session.add(record)

                total_created += 1

        # -----------------------------------
        # SAVE
        # -----------------------------------
        session.commit()

        # -----------------------------------
        # SYNC DAILY SUMMARY
        # -----------------------------------
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

        # -------------------------------------------------
        # UPDATE DAILY TABLES
        # -------------------------------------------------
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

        records = session.exec(
            select(MISRecord).where(
                MISRecord.outlet_id == outlet_id,
                MISRecord.record_date == record_date,
                MISRecord.type == record_type,
            )
        ).all()

        total = len(records)

        received = sum(1 for r in records if r.received)

        verified = sum(1 for r in records if r.approved)

        pending = sum(
            1
            for r in records
            if (not r.approved and not r.rejected and not r.out_of_scope)
        )

        # ----------------------------------------
        # BOOKING
        # ----------------------------------------
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

            daily.number_bookings = total
            daily.file_received = received
            daily.files_verified = verified
            daily.files_pending = pending

        # ----------------------------------------
        # DELIVERY
        # ----------------------------------------
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

            daily.number_deliveries = total
            daily.file_received = received
            daily.files_verified = verified
            daily.files_pending = pending

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

        return mobile[-10:]

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
