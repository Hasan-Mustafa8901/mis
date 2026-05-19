# backend/services/mis_matching.py
from sqlmodel import Session, select

from db.models import (
    MISRecord,
    MISMatchingStatus,
    MISRecordType,
    Transaction,
    Customer,
)


class MISMatchingService:
    @staticmethod
    def sync_existing_transactions(
        session: Session,
        outlet_id: int | None = None,
    ):

        stmt = select(Transaction)

        if outlet_id:
            stmt = stmt.where(Transaction.outlet_id == outlet_id)

        transactions = session.exec(stmt).all()

        print(f"FOUND {len(transactions)} TRANSACTIONS TO MATCH")

        for txn in transactions:
            try:
                MISMatchingService.match_transaction(
                    session=session,
                    transaction=txn,
                )

            except Exception as e:
                print(
                    f"FAILED MATCHING TRANSACTION {txn.id}",
                    e,
                )

        session.commit()

    @staticmethod
    def match_transaction(
        session: Session,
        transaction: Transaction,
    ):
        print("MATCHING SERVICE")
        # -----------------------------------
        # CUSTOMER
        # -----------------------------------
        customer = session.get(
            Customer,
            transaction.customer_id,
        )

        if not customer:
            return

        if not customer.mobile_number:
            return

        mobile = "".join(filter(str.isdigit, customer.mobile_number))[-10:]
        if not mobile:
            return

        # -----------------------------------
        # STAGES TO MATCH
        # -----------------------------------
        stages: list[tuple[MISRecordType, date]] = []

        if transaction.booking_date:
            stages.append(
                (
                    MISRecordType.BOOKING,
                    transaction.booking_date,
                )
            )

        if transaction.delivery_date:
            stages.append(
                (
                    MISRecordType.DELIVERY,
                    transaction.delivery_date,
                )
            )

        # -----------------------------------
        # MATCH EACH STAGE
        # -----------------------------------

        for record_type, match_date in stages:
            records = session.exec(
                select(MISRecord).where(
                    MISRecord.transaction_id.is_(None),
                    MISRecord.outlet_id == transaction.outlet_id,
                    MISRecord.type == record_type,
                )
            ).all()

            for record in records:
                record_mobile = "".join(
                    filter(str.isdigit, str(record.customer_mobile or ""))
                )[-10:]

                if record_mobile != mobile:
                    continue
                # -------------------------------
                # DATE WINDOW CHECK
                # -------------------------------
                delta = abs((record.record_date - match_date).days)

                if delta > 2:
                    continue

                # -------------------------------
                # LINK RECORD
                # -------------------------------
                record.transaction_id = transaction.id

                record.matching_status = MISMatchingStatus.MATCHED

                record.matched_automatically = True

                session.add(record)

        session.flush()
