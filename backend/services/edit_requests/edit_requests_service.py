from sqlmodel import Session

from typing import Optional
from services.utils import get_ist_now
from db.models import EditRequest, Transaction
from services.discount.discount_service import DiscountService


class EditRequestService:
    # =========================
    # CONFIG: MONEY FIELDS
    # =========================
    MONEY_FIELDS = {
        "ex showroom price",
        "insurance",
        "registration",
        "cash discount all customers",
        "additional discount from dealer",
        "extra kitty on tr cases",
        "hyundai genuine acc kit",
    }

    # =========================
    # 1. CREATE REQUEST
    # =========================
    @staticmethod
    def create_edit_request(
        session: Session,
        transaction_id: int,
        requested_by: int,
        field: str,
        old_value: Optional[str],
        new_value: Optional[str],
        remarks: Optional[str] = None,
    ) -> EditRequest:

        edit = EditRequest(
            transaction_id=transaction_id,
            requested_by=requested_by,
            field=field,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            remarks=remarks,
            status="pending",
        )

        session.add(edit)
        session.commit()
        session.refresh(edit)

        return edit

    # =========================
    # 2. APPROVE REQUEST
    # =========================
    @staticmethod
    def approve_edit_request(
        session: Session,
        edit_request_id: int,
        reviewed_by: int,
    ) -> EditRequest:

        edit = session.get(EditRequest, edit_request_id)
        if not edit:
            raise ValueError("Edit request not found")

        if edit.status != "pending":
            raise ValueError("Edit request already processed")

        transaction = session.get(Transaction, edit.transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")

        # APPLY CHANGE
        EditRequestService.apply_edit(transaction, edit)

        # CONDITIONAL AUDIT RECALCULATION
        if EditRequestService.is_money_field(edit.field):
            EditRequestService.recalculate_audit(session, transaction)

        # UPDATE STATUS
        edit.status = "approved"
        edit.reviewed_by = reviewed_by
        edit.reviewed_at = get_ist_now()

        session.add(transaction)
        session.add(edit)
        session.commit()
        session.refresh(edit)

        return edit

    # =========================
    # 3. REJECT REQUEST
    # =========================
    @staticmethod
    def reject_edit_request(
        session: Session,
        edit_request_id: int,
        reviewed_by: int,
        rejection_reason: str,
    ) -> EditRequest:

        edit = session.get(EditRequest, edit_request_id)
        if not edit:
            raise ValueError("Edit request not found")

        if edit.status != "pending":
            raise ValueError("Edit request already processed")

        edit.status = "rejected"
        edit.reviewed_by = reviewed_by
        edit.reviewed_at = get_ist_now()
        edit.rejection_reason = rejection_reason

        session.add(edit)
        session.commit()
        session.refresh(edit)

        return edit

    # =========================
    # 4. APPLY EDIT LOGIC
    # =========================
    @staticmethod
    def apply_edit(transaction: Transaction, edit: EditRequest):

        field = edit.field.lower().strip()

        # CASE 1: CUSTOMER FIELDS
        if hasattr(transaction, field):
            setattr(transaction, field, EditRequestService.cast_value(edit.new_value))
            return

        # CASE 2: INVOICE DETAILS
        if transaction.invoice_details and field in transaction.invoice_details:
            transaction.invoice_details[field] = EditRequestService.cast_value(
                edit.new_value
            )
            return

        # CASE 3: COMPONENT (actual_amounts)
        actuals = transaction.actual_amounts or {}

        actuals[field] = float(edit.new_value)
        transaction.actual_amounts = actuals

    # =========================
    # 5. CHECK MONEY FIELD
    # =========================
    @staticmethod
    def is_money_field(field: str) -> bool:
        return field.lower().strip() in EditRequestService.MONEY_FIELDS

    # =========================
    # 6. RE-CALCULATE AUDIT
    # =========================
    @staticmethod
    def recalculate_audit(session: Session, transaction: Transaction):

        audit_result = DiscountService.calculate_discount(
            session=session,
            variant_id=transaction.variant_id,
            transaction_id=transaction.id,
            booking_date=transaction.booking_date,
            actual_amounts=transaction.actual_amounts or {},
            conditions=transaction.conditions or {},
        )

        transaction.total_actual_discount = audit_result["actual_discount"]
        transaction.total_allowed_discount = audit_result["pricelist_discount"]
        transaction.total_excess_discount = audit_result["excess_discount"]
        transaction.status = audit_result["status"]

    # =========================
    # 7. SAFE TYPE CAST
    # =========================
    @staticmethod
    def cast_value(value: Optional[str]):
        if value is None:
            return None

        try:
            if "." in value:
                return float(value)
            return int(value)
        except Exception:
            return value
