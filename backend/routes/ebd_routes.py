# # backend/api/routes/mis.py
# from pathlib import Path
# from tempfile import NamedTemporaryFile

# from fastapi import (
#     APIRouter,
#     Depends,
#     File,
#     Form,
#     HTTPException,
#     UploadFile,
# )

# from sqlmodel import Session
# from datetime import date
# from db.session import get_session
# from db.models import MISRecordType
# from schemas.mis import MISRecordActionPayload
# from services.mis_service.mis_data import get_ebd_data, get_mis_transactions
# from services.mis_service.mis_update import MISUpdateService
# from services.ingestion.mis_record import MISUploadService
# from services.complaints.query import get_dealership_by_outlet


# router = APIRouter(prefix="/mis", tags=["MIS"])


# @router.get("/details")
# def get_mis_details(
#     stage: MISRecordType,
#     column: str,
#     is_footer: bool,
#     start_date: date | None,
#     end_date: date | None,
#     record_date: date | None = None,
#     outlet_id: int | None = None,
#     dealership_id: int | None = None,
#     session: Session = Depends(get_session),
# ):
#     if column == "files_incomplete":
#         response = get_mis_transactions(
#             session=session,
#             record_date=record_date,
#             stage=stage,
#             is_footer=is_footer,
#             start_date=start_date,
#             end_date=end_date,
#             outlet_id=outlet_id,
#             dealership_id=dealership_id,
#             incomplete=True,
#         )
#     elif column == "files_in_mis":
#         response = get_mis_transactions(
#             session=session,
#             record_date=record_date,
#             stage=stage,
#             is_footer=is_footer,
#             start_date=start_date,
#             end_date=end_date,
#             outlet_id=outlet_id,
#             dealership_id=dealership_id,
#             incomplete=False,
#         )
#     else:
#         response = get_ebd_data(
#             session,
#             record_date,
#             stage,
#             column,
#             is_footer,
#             start_date,
#             end_date,
#             outlet_id,
#             dealership_id,
#         )
#     return response


# @router.post("/toggle-received")
# def toggle_received(
#     payload: dict,
#     session: Session = Depends(get_session),
# ):

#     MISUpdateService.toggle_received(
#         session=session,
#         mis_record_id=payload["mis_record_id"],
#         receiving_date=payload["receiving_date"],
#         value=payload["value"],
#     )

#     return {
#         "status": "success",
#     }


# @router.post("/approve")
# def approve_record(
#     payload: MISRecordActionPayload,
#     session: Session = Depends(get_session),
# ):

#     try:
#         MISUpdateService.approve_record(
#             session=session,
#             mis_record_id=payload.mis_record_id,
#         )

#         return {
#             "status": "success",
#             "message": "Record approved",
#         }

#     except ValueError as e:
#         raise HTTPException(
#             status_code=404,
#             detail=str(e),
#         )


# @router.post("/reject")
# def reject_record(
#     payload: MISRecordActionPayload,
#     session: Session = Depends(get_session),
# ):

#     try:
#         MISUpdateService.reject_record(
#             session=session,
#             mis_record_id=payload.mis_record_id,
#             reason=payload.reason or "",
#         )

#         return {
#             "status": "success",
#             "message": "Record rejected",
#         }

#     except ValueError as e:
#         raise HTTPException(
#             status_code=404,
#             detail=str(e),
#         )


# @router.post("/toggle-oos")
# def toggle_out_of_scope(
#     payload: dict,
#     session: Session = Depends(get_session),
# ):

#     MISUpdateService.toggle_out_of_scope(
#         session=session,
#         mis_record_id=payload["mis_record_id"],
#         value=payload["value"],
#         reason=payload.get(
#             "reason",
#         ),
#     )

#     return {
#         "status": "success",
#     }


# @router.post("/toggle-approve")
# def toggle_approve(
#     payload: dict,
#     session: Session = Depends(get_session),
# ):

#     MISUpdateService.toggle_approve(
#         session=session,
#         mis_record_id=payload["mis_record_id"],
#         value=payload["value"],
#     )

#     return {
#         "status": "success",
#     }


# @router.post("/toggle-reject")
# def toggle_reject(
#     payload: dict,
#     session: Session = Depends(get_session),
# ):

#     MISUpdateService.toggle_reject(
#         session=session,
#         mis_record_id=payload["mis_record_id"],
#         value=payload["value"],
#         reason=payload.get(
#             "reason",
#         ),
#     )

#     return {
#         "status": "success",
#     }


# @router.post("/toggle-scanned")
# async def toggle_scanned(
#     payload: dict,
#     session: Session = Depends(get_session),
# ):
#     MISUpdateService.toggle_scanned_file(
#         session=session,
#         mis_record_id=payload["mis_record_id"],
#         value=payload["value"],
#         scanning_date=payload.get("scanning_date", None),
#     )
#     return {"status": "success"}


# @router.post("/upload-ebd")
# async def upload_ebd_file(
#     outlet_id: int = Form(...),
#     file: UploadFile = File(...),
#     session: Session = Depends(get_session),
# ):

#     # -----------------------------------
#     # VALIDATE FILE
#     # -----------------------------------
#     if not file.filename.endswith((".xlsx", ".xls")):
#         raise HTTPException(
#             status_code=400,
#             detail="Only Excel files are allowed",
#         )
#     print("Excel File confirm")
#     temp_path = None

#     try:
#         # -----------------------------------
#         # SAVE TEMP FILE
#         # -----------------------------------
#         suffix = Path(file.filename).suffix

#         with NamedTemporaryFile(
#             delete=False,
#             suffix=suffix,
#         ) as temp_file:
#             content = await file.read()

#             temp_file.write(content)

#             temp_path = temp_file.name
#             print("temp created and saved.")

#         dealership = get_dealership_by_outlet(session, outlet_id)
#         # -----------------------------------
#         # PROCESS FILE
#         # -----------------------------------
#         result = MISUploadService.upload_file(
#             session=session,
#             file_path=temp_path,
#             outlet_id=outlet_id,
#             dealership_id=dealership.get("id", 0),
#         )
#         print("Ran uploaded service.")
#         print(result)
#         return result

#     except Exception as e:
#         print(e)
#         raise HTTPException(
#             status_code=500,
#             detail=str(e),
#         )

#     finally:
#         # -----------------------------------
#         # CLEANUP
#         # -----------------------------------
#         try:
#             if temp_path and Path(temp_path).exists():
#                 Path(temp_path).unlink(missing_ok=True)
#         except PermissionError:
#             pass
# backend/api/routes/mis.py
# REVIEW THIS
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import date
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session
from db.session import get_session
from db.models import MISRecordType, User, UserRole, MISRecord
from schemas.mis import MISRecordActionPayload
from services.auth.dependencies import get_current_user
from services.auth.scope import validate_outlet_access, get_allowed_outlets
from services.auth.rbac import require_roles
from services.mis_service.mis_data import get_ebd_data, get_mis_transactions
from services.mis_service.mis_update import MISUpdateService
from services.ingestion.mis_record import MISUploadService
from services.complaints.query import get_dealership_by_outlet

router = APIRouter(prefix="/mis", tags=["MIS"])


# HELPERS
def validate_mis_record_access(
    session: Session,
    current_user: User,
    mis_record_id: int,
):

    mis_record = session.get(
        MISRecord,
        mis_record_id,
    )

    if not mis_record:
        raise HTTPException(
            status_code=404,
            detail="MIS record not found",
        )

    validate_outlet_access(
        current_user,
        mis_record.outlet_id,
    )

    return mis_record


# MIS DETAILS
@router.get("/details")
def get_mis_details(
    stage: MISRecordType,
    column: str,
    is_footer: bool,
    start_date: date | None,
    end_date: date | None,
    record_date: date | None = None,
    outlet_id: int | None = None,
    dealership_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    # ADMIN
    if current_user.role == UserRole.ADMIN:
        if column == "files_incomplete":
            return get_mis_transactions(
                session=session,
                record_date=record_date,
                stage=stage,
                is_footer=is_footer,
                start_date=start_date,
                end_date=end_date,
                outlet_id=outlet_id,
                dealership_id=dealership_id,
                incomplete=True,
            )

        elif column == "files_in_mis":
            return get_mis_transactions(
                session=session,
                record_date=record_date,
                stage=stage,
                is_footer=is_footer,
                start_date=start_date,
                end_date=end_date,
                outlet_id=outlet_id,
                dealership_id=dealership_id,
                incomplete=False,
            )

        else:
            return get_ebd_data(
                session=session,
                record_date=record_date,
                stage=stage,
                column=column,
                is_footer=is_footer,
                start_date=start_date,
                end_date=end_date,
                outlet_id=outlet_id,
                dealership_id=dealership_id,
            )

    # NON ADMIN USERS
    allowed_outlets = get_allowed_outlets(current_user)

    # validate requested outlet if provided
    if outlet_id:
        validate_outlet_access(
            current_user,
            outlet_id,
        )

        scoped_outlet_ids = [outlet_id]

    else:
        scoped_outlet_ids = allowed_outlets

    if column == "files_incomplete":
        return get_mis_transactions(
            session=session,
            record_date=record_date,
            stage=stage,
            is_footer=is_footer,
            start_date=start_date,
            end_date=end_date,
            outlet_ids=scoped_outlet_ids,
            incomplete=True,
        )

    elif column == "files_in_mis":
        return get_mis_transactions(
            session=session,
            record_date=record_date,
            stage=stage,
            is_footer=is_footer,
            start_date=start_date,
            end_date=end_date,
            outlet_ids=scoped_outlet_ids,
            incomplete=False,
        )

    return get_ebd_data(
        session=session,
        record_date=record_date,
        stage=stage,
        column=column,
        is_footer=is_footer,
        start_date=start_date,
        end_date=end_date,
        outlet_ids=scoped_outlet_ids,
    )


# TOGGLE RECEIVED
@router.post("/toggle-received")
def toggle_received(
    payload: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    validate_mis_record_access(
        session=session,
        current_user=current_user,
        mis_record_id=payload["mis_record_id"],
    )

    MISUpdateService.toggle_received(
        session=session,
        mis_record_id=payload["mis_record_id"],
        receiving_date=payload["receiving_date"],
        value=payload["value"],
    )

    return {
        "status": "success",
    }


# APPROVE
@router.post("/approve")
def approve_record(
    payload: MISRecordActionPayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.AUDIT_ASST,
        )
    ),
):

    validate_mis_record_access(
        session=session,
        current_user=current_user,
        mis_record_id=payload.mis_record_id,
    )

    try:
        MISUpdateService.approve_record(
            session=session,
            mis_record_id=payload.mis_record_id,
        )

        return {
            "status": "success",
            "message": "Record approved",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


# REJECT
@router.post("/reject")
def reject_record(
    payload: MISRecordActionPayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.AUDIT_ASST,
        )
    ),
):

    validate_mis_record_access(
        session=session,
        current_user=current_user,
        mis_record_id=payload.mis_record_id,
    )

    try:
        MISUpdateService.reject_record(
            session=session,
            mis_record_id=payload.mis_record_id,
            reason=payload.reason or "",
        )

        return {
            "status": "success",
            "message": "Record rejected",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


# TOGGLE OUT OF SCOPE
@router.post("/toggle-oos")
def toggle_out_of_scope(
    payload: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    validate_mis_record_access(
        session=session,
        current_user=current_user,
        mis_record_id=payload["mis_record_id"],
    )

    MISUpdateService.toggle_out_of_scope(
        session=session,
        mis_record_id=payload["mis_record_id"],
        value=payload["value"],
        reason=payload.get("reason"),
    )

    return {
        "status": "success",
    }


# TOGGLE APPROVE
@router.post("/toggle-approve")
def toggle_approve(
    payload: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    validate_mis_record_access(
        session=session,
        current_user=current_user,
        mis_record_id=payload["mis_record_id"],
    )

    MISUpdateService.toggle_approve(
        session=session,
        mis_record_id=payload["mis_record_id"],
        value=payload["value"],
    )

    return {
        "status": "success",
    }


# TOGGLE REJECT
@router.post("/toggle-reject")
def toggle_reject(
    payload: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    validate_mis_record_access(
        session=session,
        current_user=current_user,
        mis_record_id=payload["mis_record_id"],
    )

    MISUpdateService.toggle_reject(
        session=session,
        mis_record_id=payload["mis_record_id"],
        value=payload["value"],
        reason=payload.get("reason"),
    )

    return {
        "status": "success",
    }


# TOGGLE SCANNED
@router.post("/toggle-scanned")
async def toggle_scanned(
    payload: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    validate_mis_record_access(
        session=session,
        current_user=current_user,
        mis_record_id=payload["mis_record_id"],
    )

    MISUpdateService.toggle_scanned_file(
        session=session,
        mis_record_id=payload["mis_record_id"],
        value=payload["value"],
        scanning_date=payload.get("scanning_date", None),
    )

    return {
        "status": "success",
    }


@router.delete("/bulk-delete")
def bulk_delete_mis_records(
    payload: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.AUDIT_ASST,
        )
    ),
):

    record_ids = payload.get("record_ids", [])

    if not record_ids:
        raise HTTPException(
            status_code=400,
            detail="No record ids provided",
        )

    # FETCH RECORDS
    records = session.exec(select(MISRecord).where(MISRecord.id.in_(record_ids))).all()

    if not records:
        raise HTTPException(
            status_code=404,
            detail="No records found",
        )

    # SECURITY VALIDATION
    for record in records:
        validate_outlet_access(
            current_user,
            record.outlet_id,
        )

    # DELETE
    result = MISUpdateService.delete_records(
        session=session,
        record_ids=record_ids,
    )

    return result


# UPLOAD EBD
@router.post("/upload-ebd")
async def upload_ebd_file(
    outlet_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.AUDIT_ASST,
        )
    ),
):

    validate_outlet_access(
        current_user,
        outlet_id,
    )

    # VALIDATE FILE
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files are allowed",
        )
    temp_path = None

    try:
        # SAVE TEMP FILE
        suffix = Path(file.filename).suffix
        with NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        dealership = get_dealership_by_outlet(
            session,
            outlet_id,
        )

        # PROCESS FILE
        result = MISUploadService.upload_file(
            session=session,
            file_path=temp_path,
            outlet_id=outlet_id,
            dealership_id=dealership.get(
                "id",
                0,
            ),
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
    finally:
        try:
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink(missing_ok=True)
        except PermissionError:
            pass
