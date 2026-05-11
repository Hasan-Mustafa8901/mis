from sqlmodel import Session
from db.models import MISRecord
from services.ingestion.mis_record import MISUploadService
from services.utils import get_ist_now


class MISUpdateService:
    @staticmethod
    def toggle_received(
        session: Session,
        mis_record_id: int,
        value: bool,
    ):

        record = session.get(
            MISRecord,
            mis_record_id,
        )

        if not record:
            raise ValueError("MISRecord not found")

        # =====================================
        # CHECKED
        # =====================================
        if value:
            record.received = True

            record.receiving_date = get_ist_now()

        # =====================================
        # UNCHECKED
        # =====================================
        else:
            record.received = False

            record.receiving_date = None

            record.approved = False
            record.approved_date = None

            record.rejected = False
            record.rejection_reason = None

            record.out_of_scope = False
            record.out_of_scope_reason = None

        session.add(record)

        session.commit()

        MISUploadService.sync_single_daily_summary(
            session=session,
            outlet_id=record.outlet_id,
            record_date=record.record_date,
            record_type=record.type,
        )

    @staticmethod
    def approve_record(
        session: Session,
        mis_record_id: int,
    ):

        record = session.get(MISRecord, mis_record_id)

        if not record:
            raise ValueError("MISRecord not found")

        # Cannot approve rejected
        record.rejected = False
        record.rejection_reason = None

        record.out_of_scope = False
        record.out_of_scope_reason = None

        record.approved = True
        record.approved_date = get_ist_now()

        session.add(record)
        session.commit()

        MISUploadService.sync_single_daily_summary(
            session=session,
            outlet_id=record.outlet_id,
            record_date=record.record_date,
            record_type=record.type,
        )

    @staticmethod
    def reject_record(
        session: Session,
        mis_record_id: int,
        reason: str,
    ):

        record = session.get(MISRecord, mis_record_id)

        if not record:
            raise ValueError("MISRecord not found")

        record.approved = False
        record.approved_date = None

        record.out_of_scope = False
        record.out_of_scope_reason = None

        record.rejected = True
        record.rejection_reason = reason

        session.add(record)
        session.commit()

        MISUploadService.sync_single_daily_summary(
            session=session,
            outlet_id=record.outlet_id,
            record_date=record.record_date,
            record_type=record.type,
        )

    @staticmethod
    def toggle_approve(
        session: Session,
        mis_record_id: int,
        value: bool,
    ):

        record = session.get(
            MISRecord,
            mis_record_id,
        )

        if not record:
            raise ValueError("MISRecord not found")

        if value:
            record.approved = True

            record.approved_date = get_ist_now()

            # mutually exclusive
            record.rejected = False
            record.rejection_reason = None

        else:
            record.approved = False
            record.approved_date = None

        session.add(record)

        session.commit()

        MISUploadService.sync_single_daily_summary(
            session=session,
            outlet_id=record.outlet_id,
            record_date=record.record_date,
            record_type=record.type,
        )

    @staticmethod
    def toggle_reject(
        session: Session,
        mis_record_id: int,
        value: bool,
        reason: str | None = None,
    ):

        record = session.get(
            MISRecord,
            mis_record_id,
        )

        if not record:
            raise ValueError("MISRecord not found")

        if value:
            record.rejected = True

            record.rejection_reason = reason.strip() if reason else None

            # mutually exclusive
            record.approved = False
            record.approved_date = None

        else:
            record.rejected = False

            record.rejection_reason = None

        session.add(record)

        session.commit()

        MISUploadService.sync_single_daily_summary(
            session=session,
            outlet_id=record.outlet_id,
            record_date=record.record_date,
            record_type=record.type,
        )

    @staticmethod
    def toggle_out_of_scope(
        session: Session,
        mis_record_id: int,
        value: bool,
        reason: str | None = None,
    ):

        record = session.get(
            MISRecord,
            mis_record_id,
        )

        if not record:
            raise ValueError("MISRecord not found")

        if value:
            record.out_of_scope = True

            record.out_of_scope_reason = reason.strip() if reason else None

        else:
            record.out_of_scope = False

            record.out_of_scope_reason = None

        session.add(record)

        session.commit()

        MISUploadService.sync_single_daily_summary(
            session=session,
            outlet_id=record.outlet_id,
            record_date=record.record_date,
            record_type=record.type,
        )
