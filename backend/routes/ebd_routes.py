# backend/api/routes/mis.py

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from sqlmodel import Session

from db.session import get_session
from services.ingestion.mis_record import MISUploadService
from services.complaints.query import get_dealership_by_outlet


router = APIRouter(
    prefix="/mis",
    tags=["MIS"],
)


@router.post("/upload-ebd")
async def upload_ebd_file(
    outlet_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):

    # -----------------------------------
    # VALIDATE FILE
    # -----------------------------------
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files are allowed",
        )
    print("Excel File confirm")
    temp_path = None

    try:
        # -----------------------------------
        # SAVE TEMP FILE
        # -----------------------------------
        suffix = Path(file.filename).suffix

        with NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
            content = await file.read()

            temp_file.write(content)

            temp_path = temp_file.name
            print("temp created and saved.")

        dealership = get_dealership_by_outlet(session, outlet_id)
        # -----------------------------------
        # PROCESS FILE
        # -----------------------------------
        result = MISUploadService.upload_file(
            session=session,
            file_path=temp_path,
            outlet_id=outlet_id,
            dealership_id=dealership.get("id", 0),
        )
        print("Ran uploaded service.")
        print(result)
        return result

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    finally:
        # -----------------------------------
        # CLEANUP
        # -----------------------------------
        try:
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink(missing_ok=True)
        except PermissionError:
            pass
