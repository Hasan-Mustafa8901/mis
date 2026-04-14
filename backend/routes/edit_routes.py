from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional

from db.session import get_session
from db.models import EditRequest
from services.edit_requests.edit_requests_service import EditRequestService
from schemas.edit_request import (
    CreateEditRequest,
    ApproveEditRequest,
    RejectEditRequest,
    EditRequestResponse,
)

router = APIRouter(prefix="/edit-requests", tags=["Edit Requests"])


@router.post("/", response_model=EditRequestResponse)
def create_edit_request(
    payload: CreateEditRequest,
    session: Session = Depends(get_session),
):
    try:
        edit = EditRequestService.create_edit_request(
            session=session,
            transaction_id=payload.transaction_id,
            requested_by=payload.requested_by,
            field=payload.field,
            old_value=payload.old_value,
            new_value=payload.new_value,
            remarks=payload.remarks,
        )
        return edit
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[EditRequestResponse])
def list_edit_requests(
    status: Optional[str] = None,
    transaction_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    query = select(EditRequest)

    if status:
        query = query.where(EditRequest.status == status)

    if transaction_id:
        query = query.where(EditRequest.transaction_id == transaction_id)

    results = session.exec(query).all()
    return results


@router.post("/{edit_request_id}/approve", response_model=EditRequestResponse)
def approve_edit_request(
    edit_request_id: int,
    payload: ApproveEditRequest,
    session: Session = Depends(get_session),
):
    try:
        edit = EditRequestService.approve_edit_request(
            session=session,
            edit_request_id=edit_request_id,
            reviewed_by=payload.reviewed_by,
        )
        return edit
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{edit_request_id}/reject", response_model=EditRequestResponse)
def reject_edit_request(
    edit_request_id: int,
    payload: RejectEditRequest,
    session: Session = Depends(get_session),
):
    try:
        edit = EditRequestService.reject_edit_request(
            session=session,
            edit_request_id=edit_request_id,
            reviewed_by=payload.reviewed_by,
            rejection_reason=payload.rejection_reason,
        )
        return edit
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
