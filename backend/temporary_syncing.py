from sqlmodel import Session, select

from db.session import engine
from db.models import Outlet

from services.ingestion.mis_record import MISUploadService
from services.mis_service.matching_service import MISMatchingService


with Session(engine) as session:
    outlet_ids = session.exec(select(Outlet.id)).all()

    for outlet_id in outlet_ids:
        print(f"SYNCING OUTLET {outlet_id}")

        # STEP 1: MATCH EXISTING TRANSACTIONS
        MISMatchingService.sync_existing_transactions(
            session=session,
            outlet_id=outlet_id,
        )

        # STEP 2: REBUILD DAILY SUMMARY
        MISUploadService.sync_daily_summary(
            session=session,
            outlet_id=outlet_id,
        )

    print("DONE")
