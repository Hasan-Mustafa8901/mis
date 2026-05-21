# backend/services/mis_upload.py

import pandas as pd

from datetime import datetime, date
from sqlmodel import Session, select, func
from services.complaints.query import get_outlet_id_by_name

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
        affected_outlets: set[int] = set()
        total_created = 0

        for sheet_name in excel_file.sheet_names:
            # INFER RECORD TYPE
            record_type = MISUploadService.infer_record_type(sheet_name)
            # LOAD SHEET
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
            )

            df.columns = df.columns.str.lower().str.strip()

            df = normalize_columns(df)

            print(f"\nProcessing Sheet: {sheet_name}")
            print("Normalized Columns:", df.columns)

            # ITERATE ROWS

            for _, row in df.iterrows():
                customer_name = MISUploadService.clean_str(row.get("customer_name"))

                if not customer_name:
                    continue

                record_date = MISUploadService.parse_date(row.get("date"))

                if not record_date:
                    continue
                print(row.get("location"))
                customer_mobile = MISUploadService.clean_mobile(row.get("mobile"))
                car_model = MISUploadService.clean_str(row.get("car_model"))
                team_leader = MISUploadService.clean_str(row.get("team_leader"))
                resolved_outlet_id = get_outlet_id_by_name(
                    session=session,
                    name=row.get("location"),
                )
                if not outlet_id:
                    print(f"{row.get('location')} not found.")
                    continue
                affected_outlets.add(resolved_outlet_id)

                print(outlet_id)

                # DUPLICATE CHECK

                existing = session.exec(
                    select(MISRecord).where(
                        MISRecord.record_date == record_date,
                        MISRecord.type == record_type,
                        MISRecord.outlet_id == resolved_outlet_id,
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

                # CREATE RECORD

                record = MISRecord(
                    record_date=record_date,
                    type=record_type,
                    outlet_id=resolved_outlet_id,
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

        # SAVE
        session.commit()

        # SYNC DAILY SUMMARY
        for affected_outlet_id in affected_outlets:
            print("OUTLET ID: ", affected_outlet_id)
            MISUploadService.sync_daily_summary(
                session=session,
                outlet_id=affected_outlet_id,
            )

        return {
            "status": "success",
            "records_created": total_created,
        }

    # DAILY SUMMARY SYNC

    @staticmethod
    def sync_daily_summary(
        session: Session,
        outlet_id: int,
    ):

        records = session.exec(
            select(
                MISRecord.record_date,
                MISRecord.type,
            )
            .where(
                MISRecord.outlet_id == outlet_id,
            )
            .distinct()
        ).all()

        for (
            record_date,
            record_type,
        ) in records:
            MISUploadService.sync_single_daily_summary(
                session=session,
                outlet_id=outlet_id,
                record_date=record_date,
                record_type=record_type,
            )

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
        files_scanned = len([r for r in records if r.scanned])
        files_in_mis = len([r for r in records if r.transaction_id])

        # INCOMPLETE FILES

        files_incomplete = 0

        for r in records:
            if not r.transaction_id:
                continue

            txn = session.get(
                Transaction,
                r.transaction_id,
            )

            if not txn:
                continue

            if record_type == MISRecordType.BOOKING and txn.booking_file_incomplete:
                files_incomplete += 1

            elif record_type == MISRecordType.DELIVERY and txn.delivery_file_incomplete:
                files_incomplete += 1

        # VERIFIED LOGIC
        # BOOKING
        # verified = approved + rejected
        if record_type == MISRecordType.BOOKING:
            files_verified = files_approved + files_rejected

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

        # DELIVERY
        # verified =
        # received - out_of_scope - incomplete
        else:
            files_to_be_verified = len(
                [r for r in records if (r.received and not r.out_of_scope)]
            )

            files_verified = files_to_be_verified - files_incomplete

            files_not_verified = 0

        # REJECTED BUT DELIVERED

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

            daily.files_scanned = files_scanned

            daily.files_in_mis = files_in_mis

        # DELIVERY SUMMARY

        else:
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

            daily.files_scanned = files_scanned

            daily.files_in_mis = files_in_mis

        session.commit()

    @staticmethod
    def sync_transaction_daily_summary(
        session: Session,
        transaction: Transaction,
    ):
        """
        Sync daily booking/delivery summaries
        after transaction create/update.

        Handles:
        - incomplete files
        - delivery stage transitions
        - booking updates
        """

        # BOOKING SYNC

        if transaction.booking_date:
            MISUploadService.sync_single_daily_summary(
                session=session,
                outlet_id=transaction.outlet_id,
                record_date=transaction.booking_date,
                record_type=MISRecordType.BOOKING,
            )

        # DELIVERY SYNC

        if transaction.delivery_date:
            MISUploadService.sync_single_daily_summary(
                session=session,
                outlet_id=transaction.outlet_id,
                record_date=transaction.delivery_date,
                record_type=MISRecordType.DELIVERY,
            )

    # HELPERS

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

        if isinstance(data, dict):
            return {str(k): MISUploadService.make_json_safe(v) for k, v in data.items()}

        elif isinstance(data, list):
            return [MISUploadService.make_json_safe(v) for v in data]

        elif isinstance(data, tuple):
            return tuple(MISUploadService.make_json_safe(v) for v in data)

        # PANDAS TIMESTAMP / DATETIME
        elif isinstance(
            data,
            (
                datetime,
                pd.Timestamp,
            ),
        ):
            return data.isoformat()

        # DATE
        elif isinstance(data, date):
            return data.isoformat()
        # NUMPY TYPES
        # elif isinstance(data, np.integer):

        #     return int(data)

        # elif isinstance(data, np.floating):

        #     return float(data)

        # elif isinstance(data, np.bool_):

        #     return bool(data)
        # NaN
        elif pd.isna(data):
            return None

        return data
