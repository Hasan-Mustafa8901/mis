# test_mis_upload.py

from sqlmodel import Session
from db.session import engine

from services.ingestion.mis_record import MISUploadService


with Session(engine) as session:
    result = MISUploadService.upload_file(
        session=session,
        file_path=r"C:\Users\hasan\Downloads\Booking Data Format.xlsx",
        outlet_id=1,
        dealership_id=1,
    )

    print(result)
