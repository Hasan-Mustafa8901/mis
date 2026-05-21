from sqlmodel import Session, select
from fastapi import HTTPException
from typing import Dict, Any, List, Optional
from db.models import (
    Transaction,
    Outlet,
    Dealership,
    TransactionItem,
    Customer,
    Variant,
    DiscountComponent,
    Employee,
    TransactionAccessoryLink,
    Accessory,
    User,
)
from services.ingestion.mis_record import MISUploadService
from services.mis_service.matching_service import MISMatchingService

# from services.discount.discount_service import DiscountService
from datetime import datetime, date
from services.utils import get_ist_now
from rich import print


def normalize_conditions_delivery_checks(payload: dict) -> dict:
    payload["conditions"] = {
        k: bool(v) for k, v in payload.get("conditions", {}).items()
    }
    payload["delivery_checks"] = {
        k: bool(v) for k, v in payload.get("delivery_checks", {}).items()
    }
    return payload


def convert_date_fields(payload: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    for field in fields:
        value = payload.get(field)

        if value is None:
            continue

        if isinstance(value, date):
            continue

        if not value:
            payload[field] = None
            continue

        if isinstance(value, str) and value.strip():
            payload[field] = datetime.strptime(value, "%Y-%m-%d").date()

    return payload


class TransactionService:
    @staticmethod
    def create_transaction_items(
        session: Session,
        transaction_id: int,
        payload: Dict[str, Any],
    ):
        """
        Creates or replaces transaction items from actual_amounts.
        """

        actual_amounts = payload.get("actual_amounts", {})
        allowed_amounts = payload.get("allowed_amounts", {})

        # DELETE existing items (important for override case)
        existing_items = session.exec(
            select(TransactionItem).where(
                TransactionItem.transaction_id == transaction_id
            )
        ).all()

        for item in existing_items:
            session.delete(item)

        session.flush()

        # Fetch components
        components = session.exec(select(DiscountComponent)).all()
        comp_map = {comp.name: comp for comp in components}

        # Create new items
        for name, actual in actual_amounts.items():
            comp = comp_map.get(name)
            if not comp:
                continue

            item = TransactionItem(
                transaction_id=transaction_id,
                component_id=comp.id,
                component_name=comp.name,
                component_type=comp.type,
                actual_amount=int(actual),
                allowed_amount=int(allowed_amounts.get(name, 0)),
                difference=int(allowed_amounts.get(name, 0) - actual),
            )
            session.add(item)

        session.flush()

    @staticmethod
    def create_or_update_customer(session: Session, cust_data: Dict[str, Any]):

        if not cust_data:
            raise ValueError("Customer data required")

        # Try find existing (based on mobile)
        existing = session.exec(
            select(Customer).where(
                Customer.mobile_number == cust_data.get("mobile_number")
            )
        ).first()

        if existing:
            # Update fields
            for field in [
                "name",
                "email",
                "pan_number",
                "aadhar_number",
                "address",
                "city",
                "pin_code",
            ]:
                if cust_data.get(field):
                    setattr(existing, field, cust_data[field])

            session.add(existing)
            session.flush()
            return existing

        # Create new
        customer = Customer(
            name=cust_data.get("name"),
            mobile_number=cust_data.get("mobile_number"),
            email=cust_data.get("email"),
            pan_number=cust_data.get("pan_number"),
            aadhar_number=cust_data.get("aadhar_number"),
            address=cust_data.get("address"),
            city=cust_data.get("city"),
            pin_code=cust_data.get("pin_code"),
        )

        session.add(customer)
        session.flush()

        return customer

    @staticmethod
    def update_transaction_accessories(
        session: Session,
        transaction: Transaction,
        accessory_ids: List[int],
    ):
        """
        Replace accessories for a transaction
        """

        # delete old links
        existing_links = session.exec(
            select(TransactionAccessoryLink).where(
                TransactionAccessoryLink.transaction_id == transaction.id
            )
        ).all()

        for link in existing_links:
            session.delete(link)

        session.flush()

        if not accessory_ids:
            return

        # validate accessories
        accessories = session.exec(
            select(Accessory).where(Accessory.id.in_(accessory_ids))
        ).all()

        valid_ids = {a.id for a in accessories}

        for acc_id in accessory_ids:
            if acc_id not in valid_ids:
                continue

            link = TransactionAccessoryLink(
                transaction_id=transaction.id,
                accessory_id=acc_id,
            )
            session.add(link)

        session.flush()

    @staticmethod
    def convert_to_delivery(
        session: Session,
        transaction_id: int,
        payload: Dict[str, Any],
    ):

        transaction = session.get(Transaction, transaction_id)
        payload = convert_date_fields(
            payload, ["booking_date", "registration_date", "delivery_date"]
        )

        if not transaction:
            raise ValueError("Transaction not found")

        if transaction.stage == "delivery":
            raise ValueError("Already delivered")

        # =========================
        # STEP 1: Decide data source
        # =========================
        use_booking_data = payload.get("use_booking_data", True)

        if not use_booking_data:
            # update items (override)
            TransactionService.create_transaction_items(
                session, transaction.id, payload
            )

        # =========================
        # STEP 2: Update customer (edge case)
        # =========================
        if "customer" in payload:
            customer = TransactionService.create_or_update_customer(
                session, payload["customer"]
            )
            transaction.customer_id = customer.id

        # =========================
        # STEP 3: Add delivery data
        # =========================
        transaction.delivery_checklist = payload.get("delivery_checklist", {})
        # accessories
        if "accessory_ids" in payload:
            TransactionService.update_transaction_accessories(
                session, transaction, payload["accessory_ids"]
            )

        # =========================
        # STEP 4: Recalculate discount (if needed)
        # =========================
        transaction.stage = "delivery"  # Set stage BEFORE calculation
        transaction.vin_number = payload.get("vin_number", "")
        transaction.engine_number = payload.get("engine_number", "")
        transaction.model_year = payload.get("model_year", "")
        transaction.color = payload.get("color", "")
        transaction.registration_number = payload.get("registration_number", "")
        transaction.registration_date = payload.get("registration_date", None)
        transaction.delivery_date = payload.get("delivery_date", None)
        transaction.booking_date = payload.get("booking_date", transaction.booking_date)

        # # Replace this with Frontend Sent Discount
        transaction.total_actual_discount = int(
            payload.get("total_actual_discount") or 0
        )
        transaction.total_allowed_discount = int(payload.get("pricelist_discount") or 0)
        transaction.total_excess_discount = int(payload.get("excess_discount") or 0)
        transaction.adjustment_delivery = int(payload.get("adjustment_delivery") or 0)
        transaction.status = (
            "Excess Discount"
            if payload.get("excess_discount", 0) > 0
            else "No Excess Discount"
        )

        audit_result = {
            "actual_discount": transaction.total_actual_discount,
            "pricelist_discount": transaction.total_allowed_discount,
            "excess_discount": transaction.total_excess_discount,
            "status": transaction.status,
        }

        # =========================
        # STEP 5: Reconciliation
        # =========================
        TransactionService.apply_funds_reconciliation(session, transaction, payload)

        session.add(transaction)
        session.commit()
        # Match this record with ebd
        MISMatchingService.match_transaction(session=session, transaction=transaction)
        session.refresh(transaction)
        # sync the dalily delivery table
        MISUploadService.sync_transaction_daily_summary(
            session=session, transaction=transaction
        )

        return {
            "id": transaction.id,
            "stage": transaction.stage,
            "status": transaction.status,
            "balance": transaction.balance,
            "payment_status": transaction.payment_status,
            "summary": audit_result,
        }

    @staticmethod
    def create_delivery_transaction(session: Session, payload: Dict[str, Any]):

        # STEP 1: Create transaction
        transaction = TransactionService.create_transaction_raw(session, payload)

        # STEP 2: Stage + mode
        transaction.stage = "delivery"
        transaction.mode = "book_and_delivery"

        # STEP 3: Save checklists
        transaction.delivery_checklist = payload.get("delivery_checklist", {})

        # Most Important
        transaction.invoice_details = payload.get("invoice_details", {})

        # STEP 4: Items
        if transaction.id:
            TransactionService.create_transaction_items(
                session, transaction.id, payload
            )

        # STEP 5: Discount
        transaction.total_actual_discount = payload.get("total_actual_discount", 0)
        transaction.total_allowed_discount = payload.get("total_allowed_discount", 0)
        transaction.total_excess_discount = payload.get("total_excess_discount", 0)
        transaction.adjustment_delivery = int(payload.get("adjustment_delivery") or 0)
        transaction.status = (
            "Excess Discount"
            if payload.get("excess_discount", 0) > 0
            else "No Excess Discount"
        )

        audit_result = {
            "actual_discount": transaction.total_actual_discount,
            "pricelist_discount": transaction.total_allowed_discount,
            "excess_discount": transaction.total_excess_discount,
            "status": transaction.status,
        }

        # STEP 6: Reconciliation (IMPORTANT)
        TransactionService.apply_funds_reconciliation(session, transaction, payload)

        session.add(transaction)
        session.commit()

        # Match with EBD Data
        MISMatchingService.match_transaction(session=session, transaction=transaction)
        session.refresh(transaction)
        # sync with the daily delivery table
        MISUploadService.sync_transaction_daily_summary(
            session=session, transaction=transaction
        )

        return {
            "id": transaction.id,
            "stage": transaction.stage,
            "status": transaction.status,
            "balance": transaction.balance,
            "payment_status": transaction.payment_status,
            "summary": audit_result,
        }

    @staticmethod
    def create_booking_transaction(session: Session, payload: Dict[str, Any]):
        # STEP 1: Create base transaction
        transaction = TransactionService.create_transaction_raw(session, payload)

        # STEP 2: Set stage + mode
        transaction.stage = "booking"
        transaction.mode = "booking"

        # STEP 3: Save checklist
        transaction.booking_checklist = payload.get("booking_checklist", {})

        # STEP 4: Save transaction items
        if transaction.id:
            TransactionService.create_transaction_items(
                session, transaction.id, payload
            )
        transaction.booking_file_incomplete = payload.get(
            "booking_file_incomplete", False
        )
        transaction.booking_file_incomplete_remarks = payload.get(
            "booking_file_incomplete_remarks", ""
        )
        transaction.discount_booking = payload.get("discount_booking", 0.0)
        transaction.total_discount_booking = payload.get("total_discount_booking", 0.0)
        transaction.price_offered_booking = payload.get("price_offered_booking", 0.0)
        transaction.excess_booking = payload.get("excess_booking", 0.0)
        transaction.adjustment_booking = int(payload.get("adjustment_booking") or 0)

        transaction.status = (
            "Excess Discount"
            if transaction.excess_booking > 0
            else "No Excess Discount"
        )

        session.add(transaction)
        session.commit()

        # Match with ebd record
        MISMatchingService.match_transaction(session=session, transaction=transaction)

        session.refresh(transaction)
        # sync with the daily booking table
        MISUploadService.sync_transaction_daily_summary(
            session=session, transaction=transaction
        )

        return {
            "id": transaction.id,
            "stage": transaction.stage,
            "status": transaction.status,
        }

    @staticmethod
    def create_transaction_raw(session: Session, payload: dict) -> Transaction:
        """
        this function creates the customers, transactions objects and saves them to the database.
        It also links the accessories and creates transaction items with actual amounts.
        It does not perform any logic or calculations, it just saves the raw data as-is.
        """
        # ─────────────────────────────
        # 1. CUSTOMER (CREATE ALWAYS)
        # Create customer object saves customer in the DB.
        # ─────────────────────────────
        cust_data = payload.get("customer", {})

        customer = customer = TransactionService.create_or_update_customer(
            session, cust_data
        )

        payload = convert_date_fields(
            payload, ["booking_date", "registration_date", "delivery_date"]
        )

        # ─────────────────────────────
        # 2. TRANSACTION CORE
        # ─────────────────────────────
        transaction = Transaction(
            customer_id=customer.id,
            variant_id=payload["variant_id"],
            outlet_id=payload["outlet_id"],
            sales_executive_id=payload["sales_executive_id"],
            created_by=payload.get("user_id"),
            stage=payload.get("stage", "booking"),
            booking_date=payload.get("booking_date", None),
            booking_amt=payload.get("booking_amt", 0.0),
            booking_receipt_num=payload.get("booking_receipt_num", None),
            delivery_date=payload.get("delivery_date", None),
            delivery_file_incomplete=payload.get("delivery_file_incomplete"),
            delivery_file_incomplete_remarks=payload.get(
                "delivery_file_incomplete_remarks", ""
            ),
            # VEHICLE
            customer_file_number=payload.get("customer_file_number"),
            vin_number=payload.get("vin_number"),
            engine_number=payload.get("engine_number", None),
            registration_number=payload.get("registration_number"),
            registration_date=payload.get("registration_date"),
            color=payload.get("color"),
            model_year=int(payload.get("model_year", ""))
            if payload.get("model_year")
            else None,
            # CONDITIONS
            conditions=payload.get("conditions", {}),
            # JSON SECTIONS
            invoice_details=payload.get("invoice_details", {}),
            invoice_number=payload.get("invoice_details", {}).get("invoice_number"),
            payment_details=payload.get("payment_details", {}),
            finance_details=payload.get("finance_details", {}),
            exchange_details=payload.get("exchange_details", {}),
            audit_info=payload.get("audit_info", {}),
        )
        session.add(transaction)
        session.flush()
        session.refresh(transaction)

        return transaction

    @staticmethod
    def get_transaction_reconstruction(
        session: Session, transaction_id: int
    ) -> Dict[str, Any]:
        """
        Reconstructs the full MIS data for a transaction in a flat format.
        This allows full fidelity to the original Excel MIS template.
        """
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            return {}
        user = (
            session.get(User, transaction.created_by)
            if transaction.created_by
            else None
        )
        # ── FETCH OUTLET ─────────────────────────
        outlet = (
            session.get(Outlet, transaction.outlet_id)
            if transaction.outlet_id
            else None
        )

        # ── FETCH DEALERSHIP ─────────────────────
        dealership = (
            session.get(Dealership, outlet.dealership_id)
            if outlet and outlet.dealership_id
            else None
        )

        # 1. Start with metadata
        data = {
            "id": transaction.id,
            "status": transaction.status,
            "stage": transaction.stage,
            "mode": transaction.mode,
            "created_by": user.name if user else None,
            "created_at": transaction.created_at.isoformat()
            if transaction.created_at
            else None,
            "outlet_id": transaction.outlet_id,
            "outlet_name": outlet.name if outlet else None,
            "dealership_id": outlet.dealership_id if outlet else None,
            "dealership_name": dealership.name if dealership else None,
        }

        # 2. Section 1: Customer Details
        cust = transaction.customer
        data.update(
            {
                "customer_name": cust.name,
                "mobile_number": cust.mobile_number,
                "alternate_mobile": cust.alternate_mobile,
                "email": cust.email,
                "pan_number": cust.pan_number,
                "aadhar_number": cust.aadhar_number,
                "address": cust.address,
                "city": cust.city,
                "pin_code": cust.pin_code,
            }
        )

        # 3. Section 2: Vehicle Details
        variant = session.get(Variant, transaction.variant_id)
        if variant is None:
            raise ValueError(f"Variant with ID {transaction.variant_id} not found.")
        data.update(
            {
                "car_id": variant.car_id if variant.car_id else None,
                "variant_id": variant.id if variant.id else None,
                "car_name": variant.car.name if variant.car else None,
                "variant_name": variant.variant_name,
                "full_variant_name": variant.full_variant_name,
                "vin_number": transaction.vin_number,
                "engine_number": transaction.engine_number,
                "color": transaction.color,
                "registration_number": transaction.registration_number,
                "registration_date": transaction.registration_date.isoformat()
                if transaction.registration_date
                else None,
                "model_year": transaction.model_year,
            }
        )

        # 4. Section 3: Transaction Core
        sales_exec = session.get(Employee, transaction.sales_executive_id)
        data.update(
            {
                "booking_date": transaction.booking_date.isoformat()
                if transaction.booking_date
                else None,
                "booking_amt": transaction.booking_amt,
                "booking_receipt_num": transaction.booking_receipt_num,
                "delivery_date": transaction.delivery_date.isoformat()
                if transaction.delivery_date
                else None,
                "booking_file_incomplete": transaction.booking_file_incomplete,
                "booking_file_incomplete_remarks": transaction.booking_file_incomplete_remarks,
                "delivery_file_incomplete": transaction.delivery_file_incomplete,
                "delivery_file_incomplete_remarks": transaction.delivery_file_incomplete_remarks,
                "invoice_number": transaction.invoice_number,
                "showroom_id": transaction.outlet_id,
                "sales_executive_id": transaction.sales_executive_id,
                "sales_executive_name": sales_exec.name if sales_exec else None,
                "team_leader": transaction.team_leader,
                "customer_file_number": transaction.customer_file_number,
            }
        )

        # 5. Section 4: Price & Discount Components (MOST IMPORTANT)
        # Fetch all components in correct order
        all_components = session.exec(
            select(DiscountComponent).order_by(DiscountComponent.order)
        ).all()
        # Fetch actual items for this transaction
        items = session.exec(
            select(TransactionItem).where(
                TransactionItem.transaction_id == transaction.id
            )
        ).all()
        item_map = {item.component_id: item for item in items}

        for comp in all_components:
            item = item_map.get(comp.id)
            # prefix = ""  # Could use section prefix if desired, but user wants MIS names
            data[f"{comp.name}_actual"] = item.actual_amount if item else 0.0
            data[f"{comp.name}_allowed"] = item.allowed_amount if item else 0.0

        # 6. Section 5: Conditions
        for cond, val in transaction.conditions.items():
            data[f"cond_{cond}"] = val

        # 7. Section 6: Additional Sections (JSON)

        data.update({f"{k}": v for k, v in transaction.invoice_details.items()})
        data.update(
            {f"exchange_{k}": v for k, v in transaction.exchange_details.items()}
        )
        data.update({f"finance_{k}": v for k, v in transaction.finance_details.items()})

        data.update(
            {f"del_checks_{k}": v for k, v in transaction.delivery_checklist.items()}
        )
        data.update(
            {f"bk_checks_{k}": v for k, v in transaction.booking_checklist.items()}
        )
        data.update({f"audit_{k}": v for k, v in transaction.audit_info.items()})
        data.update({f"payment_{k}": v for k, v in transaction.payment_details.items()})
        # 7.5 Accessories (NEW)
        links = session.exec(
            select(TransactionAccessoryLink).where(
                TransactionAccessoryLink.transaction_id == transaction.id
            )
        ).all()

        accessories_data = []
        for link in links:
            acc = link.accessory
            if acc:
                accessories_data.append(
                    {"id": acc.id, "name": acc.name, "listed_price": acc.listed_price}
                )

        data["accessories"] = accessories_data
        data.update(
            {
                "net_receivable": transaction.total_receivable,
                "total_received": transaction.total_received,
                "balance_amount": transaction.balance,
            }
        )
        data.update(
            {
                "discount_booking": transaction.discount_booking,  # Discount Quoted on the Booking File
                "total_discount_booking": transaction.total_discount_booking,
                "price_offered_booking": transaction.price_offered_booking,
                "excess_booking": transaction.excess_booking,
                "adjustment_booking": transaction.adjustment_booking,
            }
        )

        # 8. Totals
        data.update(
            {
                "total_allowed_discount": transaction.total_allowed_discount,
                "total_actual_discount": transaction.total_actual_discount,
                "total_excess_discount": transaction.total_excess_discount,
                "other_discount_delivery": transaction.other_discount_delivery,
                "adjustment_delivery": transaction.adjustment_delivery,
            }
        )

        return data

    @staticmethod
    def list_transactions(session: Session) -> List[Transaction]:
        return list(session.exec(select(Transaction)).all())

    @staticmethod
    def get_transaction_by_id(
        session: Session, transaction_id: int
    ) -> Optional[Transaction]:
        return session.get(Transaction, transaction_id)

    @staticmethod
    def apply_funds_reconciliation(
        session: Session,
        transaction: Transaction,
        payload: Dict[str, Any],
    ):

        # from sqlmodel import select
        from db.models import TransactionItem

        items = session.exec(
            select(TransactionItem).where(
                TransactionItem.transaction_id == transaction.id
            )
        ).all()

        total_on_road = 0.0

        for item in items:
            if item.component_type == "price":
                total_on_road += item.actual_amount

        total_discount = 0.0

        for item in items:
            if item.component_type == "discount":
                total_discount += item.actual_amount

        total_receivable = total_on_road - total_discount

        payments = payload.get("payment_details", {})

        total_received = (
            payments.get("bank", 0)
            + payments.get("cash", 0)
            + payments.get("finance", 0)
            + payments.get("exchange", 0)
        )

        balance = total_received - total_receivable

        if balance == 0:
            payment_status = "Settled"
        elif balance > 0:
            payment_status = "Excess"
        else:
            payment_status = "Short"

        transaction.balance = balance
        transaction.payment_status = payment_status
        print(f"{balance=}\n{payment_status=}")
        session.add(transaction)
        session.flush()

    @staticmethod
    def update_transaction(
        session: Session,
        transaction_id: int,
        payload: Dict[str, Any],
    ):

        transaction = session.get(Transaction, transaction_id)

        if not transaction:
            raise HTTPException(
                status_code=404,
                detail="Transaction not found",
            )

        payload = convert_date_fields(
            payload,
            [
                "booking_date",
                "delivery_date",
                "registration_date",
            ],
        )

        # CUSTOMER
        if payload.get("customer"):
            customer = TransactionService.create_or_update_customer(
                session,
                payload["customer"],
            )

            transaction.customer_id = customer.id

        # CORE FIELDS
        CORE_FIELDS = [
            "variant_id",
            "outlet_id",
            "sales_executive_id",
            "bank_id",
            "booking_date",
            "booking_amt",
            "booking_receipt_num",
            "booking_file_incomplete",
            "delivery_file_incomplete",
            "booking_file_incomplete_remarks",
            "delivery_file_incomplete_remarks",
            "delivery_date",
            "invoice_number",
            "customer_file_number",
            "stage",
            "mode",
            "vin_number",
            "engine_number",
            "color",
            "registration_number",
            "registration_date",
            "team_leader",
            "total_receivable",
            "total_received",
            "balance",
            "price_offered_booking",
            "discount_booking",
            "total_discount_booking",
            "excess_booking",
            "adjustment_booking",
            "status",
            "total_actual_discount",
            "total_allowed_discount",
            "total_excess_discount",
            "other_discount_delivery",
            "adjustment_delivery",
            "payment_status",
        ]

        for field in CORE_FIELDS:
            if field in payload:
                setattr(
                    transaction,
                    field,
                    payload[field],
                )

        # ─────────────────────────────
        # MODEL YEAR
        # ─────────────────────────────
        transaction.model_year = (
            int(payload["model_year"]) if payload.get("model_year") else None
        )

        # ─────────────────────────────
        # JSON FIELDS
        # ─────────────────────────────
        JSON_FIELDS = [
            "conditions",
            "invoice_details",
            "payment_details",
            "finance_details",
            "exchange_details",
            "audit_info",
            "booking_checklist",
            "delivery_checklist",
        ]

        for field in JSON_FIELDS:
            if field in payload:
                setattr(
                    transaction,
                    field,
                    payload.get(field) or {},
                )

        # ─────────────────────────────
        # ITEMS
        # ─────────────────────────────
        TransactionService.create_transaction_items(
            session,
            transaction.id,
            payload,
        )

        # ─────────────────────────────
        # ACCESSORIES
        # ─────────────────────────────
        if "accessory_ids" in payload:
            TransactionService.update_transaction_accessories(
                session,
                transaction,
                payload["accessory_ids"],
            )

        # ─────────────────────────────
        # RECONCILIATION
        # ─────────────────────────────
        TransactionService.apply_funds_reconciliation(
            session,
            transaction,
            payload,
        )

        # ─────────────────────────────
        # UPDATED TIMESTAMP
        # ─────────────────────────────
        transaction.updated_at = get_ist_now()

        session.add(transaction)

        session.commit()

        session.refresh(transaction)

        return {
            "id": transaction.id,
            "stage": transaction.stage,
            "mode": transaction.mode,
            "status": transaction.status,
            "updated_at": transaction.updated_at.isoformat()
            if transaction.updated_at
            else None,
        }

    @staticmethod
    def delete_transaction(session: Session, transaction_id: int) -> dict:
        transaction = session.get(Transaction, transaction_id)

        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # ── Delete related TransactionItems ─────────────────
        items = session.exec(
            select(TransactionItem).where(
                TransactionItem.transaction_id == transaction_id
            )
        ).all()

        for item in items:
            session.delete(item)

        # ── Delete accessory links ──────────────────────────
        links = session.exec(
            select(TransactionAccessoryLink).where(
                TransactionAccessoryLink.transaction_id == transaction_id
            )
        ).all()

        for link in links:
            session.delete(link)

        # ── Delete main transaction ─────────────────────────
        session.delete(transaction)

        session.commit()

        return {"message": "Transaction deleted successfully", "id": transaction_id}
