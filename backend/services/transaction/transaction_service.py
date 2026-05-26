from sqlmodel import Session, select
from fastapi import HTTPException
from functools import lru_cache
from typing import Dict, Any, List, Optional, Tuple
from db.session import engine
from sqlalchemy.orm import joinedload, selectinload
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
import logging
import time

logger = logging.getLogger(__name__)


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
    def create_transaction_raw(session: Session, payload: dict) -> Transaction:
        """
        this function creates the customers, transactions objects and saves them to the database.
        It also links the accessories and creates transaction items with actual amounts.
        It does not perform any logic or calculations, it just saves the raw data as-is.
        """
        # 1. CUSTOMER (CREATE ALWAYS)
        # Create customer object saves customer in the DB.
        cust_data = payload.get("customer", {})

        customer = customer = TransactionService.create_or_update_customer(
            session, cust_data
        )

        payload = convert_date_fields(
            payload, ["booking_date", "registration_date", "delivery_date"]
        )

        # 2. TRANSACTION CORE
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

        # STEP 1: Decide data source
        use_booking_data = payload.get("use_booking_data", True)

        if not use_booking_data:
            # update items (override)
            TransactionService.create_transaction_items(
                session, transaction.id, payload
            )

        # STEP 2: Update customer (edge case)
        if "customer" in payload:
            customer = TransactionService.create_or_update_customer(
                session, payload["customer"]
            )
            transaction.customer_id = customer.id

        # STEP 3: Add delivery data
        transaction.delivery_checklist = payload.get("delivery_checklist", {})
        # accessories
        if "accessory_ids" in payload:
            TransactionService.update_transaction_accessories(
                session, transaction, payload["accessory_ids"]
            )

        # STEP 4: Recalculate discount (if needed)
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

        # STEP 5: Reconciliation

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

    # FIXED: Cache primitive data, not ORM objects
    @staticmethod
    @lru_cache(maxsize=1)
    def get_discount_component_metadata() -> List[Tuple[int, str, int]]:
        """
        Returns list of (id, name, order) tuples for discount components.
        Cached as primitives to avoid detached session issues.
        """
        try:
            with Session(engine) as session:
                components = session.exec(
                    select(
                        DiscountComponent.id,
                        DiscountComponent.name,
                        DiscountComponent.order,
                    ).order_by(DiscountComponent.order)
                ).all()

                return [
                    (comp_id, comp_name, comp_order)
                    for comp_id, comp_name, comp_order in components
                ]
        except Exception as e:
            logger.error(f"Error fetching discount components: {e}", exc_info=True)
            return []

    @staticmethod
    def get_transaction_reconstruction(
        session: Session,
        transaction_id: int,
    ) -> Dict[str, Any]:
        """
        Reconstructs complete transaction data with optimized eager loading.

        Performance: 1 main query + 2 targeted lookups = 3 total queries.

        Args:
            session: Active database session
            transaction_id: Transaction ID to reconstruct

        Returns:
            Dictionary with complete transaction data, or empty dict if not found
        """

        try:
            # start = time.perf_counter()
            # SINGLE OPTIMIZED QUERY - loads all relationships upfront
            transaction = session.exec(
                select(Transaction)
                .where(Transaction.id == transaction_id)
                .options(
                    joinedload(Transaction.customer),  # type: ignore
                    joinedload(Transaction.outlet).joinedload(Outlet.dealership),  # type: ignore
                    joinedload(Transaction.variant).joinedload(Variant.car),  # type: ignore
                    joinedload(Transaction.sales_executive),  # type: ignore
                    joinedload(Transaction.user),  # type: ignore
                    selectinload(Transaction.items),  # type: ignore
                    selectinload(Transaction.accessories).joinedload(  # type: ignore
                        TransactionAccessoryLink.accessory  # type: ignore
                    ),
                )
            ).first()

            if not transaction:
                logger.info(f"Transaction {transaction_id} not found")
                return {}

            # PRE-EXTRACT relationships to avoid repeated attribute access
            sales_exec = transaction.sales_executive
            user = transaction.user
            outlet = transaction.outlet
            dealership = outlet.dealership if outlet else None
            variant = transaction.variant
            car = variant.car if variant else None
            customer = transaction.customer

            # BUILD RESPONSE DICTIONARY
            data = {
                # META
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
                "dealership_id": dealership.id if dealership else None,
                "dealership_name": dealership.name if dealership else None,
            }

            # CUSTOMER DETAILS
            if customer:
                data.update(
                    {
                        "customer_name": customer.name,
                        "mobile_number": customer.mobile_number,
                        "alternate_mobile": customer.alternate_mobile,
                        "email": customer.email,
                        "pan_number": customer.pan_number,
                        "aadhar_number": customer.aadhar_number,
                        "address": customer.address,
                        "city": customer.city,
                        "pin_code": customer.pin_code,
                    }
                )

            # VEHICLE DETAILS
            if variant:
                data.update(
                    {
                        "car_id": variant.car_id,
                        "variant_id": variant.id,
                        "car_name": car.name if car else None,
                        "variant_name": variant.variant_name,
                        "full_variant_name": variant.full_variant_name,
                    }
                )

            # TRANSACTION DETAILS
            data.update(
                {
                    "vin_number": transaction.vin_number,
                    "engine_number": transaction.engine_number,
                    "color": transaction.color,
                    "registration_number": transaction.registration_number,
                    "registration_date": (
                        transaction.registration_date.isoformat()
                        if transaction.registration_date
                        else None
                    ),
                    "model_year": transaction.model_year,
                    "booking_date": (
                        transaction.booking_date.isoformat()
                        if transaction.booking_date
                        else None
                    ),
                    "booking_amt": transaction.booking_amt,
                    "booking_receipt_num": transaction.booking_receipt_num,
                    "delivery_date": (
                        transaction.delivery_date.isoformat()
                        if transaction.delivery_date
                        else None
                    ),
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

            # DISCOUNT COMPONENTS - using cached metadata
            component_metadata = TransactionService.get_discount_component_metadata()

            # Build lookup from preloaded transaction_items (no additional queries)
            item_lookup = {item.component_id: item for item in transaction.items}

            # Populate component amounts - all in-memory operations
            for comp_id, comp_name, _ in component_metadata:
                item = item_lookup.get(comp_id)
                data[f"{comp_name}_actual"] = item.actual_amount if item else 0.0
                data[f"{comp_name}_allowed"] = item.allowed_amount if item else 0.0

            # JSON FIELD EXPANSIONS - using helper function
            TransactionService._expand_json_field(
                data, transaction.conditions, prefix="cond_"
            )
            TransactionService._expand_json_field(data, transaction.invoice_details)
            TransactionService._expand_json_field(
                data, transaction.exchange_details, prefix="exchange_"
            )
            TransactionService._expand_json_field(
                data, transaction.finance_details, prefix="finance_"
            )
            TransactionService._expand_json_field(
                data, transaction.delivery_checklist, prefix="del_checks_"
            )
            TransactionService._expand_json_field(
                data, transaction.booking_checklist, prefix="bk_checks_"
            )
            TransactionService._expand_json_field(
                data, transaction.audit_info, prefix="audit_"
            )
            TransactionService._expand_json_field(
                data, transaction.payment_details, prefix="payment_"
            )

            # ACCESSORIES - already loaded via selectinload
            data["accessories"] = [
                {
                    "id": link.accessory.id,
                    "name": link.accessory.name,
                    "listed_price": link.accessory.listed_price,
                }
                for link in transaction.accessories
                if link.accessory
            ]

            # FINANCIAL SUMMARY
            data.update(
                {
                    "net_receivable": transaction.total_receivable,
                    "total_received": transaction.total_received,
                    "balance_amount": transaction.balance,
                    "discount_booking": transaction.discount_booking,
                    "total_discount_booking": transaction.total_discount_booking,
                    "price_offered_booking": transaction.price_offered_booking,
                    "excess_booking": transaction.excess_booking,
                    "adjustment_booking": transaction.adjustment_booking,
                    "total_allowed_discount": transaction.total_allowed_discount,
                    "total_actual_discount": transaction.total_actual_discount,
                    "total_excess_discount": transaction.total_excess_discount,
                    "other_discount_delivery": transaction.other_discount_delivery,
                    "adjustment_delivery": transaction.adjustment_delivery,
                }
            )
            # elapsed = start - time.perf_counter()
            # print(
            #     f"Transaction reconstruction "
            #     f"took {elapsed:.4f}s "
            #     f"for transaction_id={transaction_id}"
            # )
            return data

        except Exception as e:
            logger.error(
                f"Error reconstructing transaction {transaction_id}: {e}", exc_info=True
            )
            return {}

    @staticmethod
    def _expand_json_field(
        target_dict: Dict[str, Any],
        source_dict: Optional[Dict[str, Any]],
        prefix: str = "",
    ) -> None:
        """
        Merge JSON field contents into target dictionary with optional prefix.

        Args:
            target_dict: Dictionary to update
            source_dict: Source JSON data (can be None)
            prefix: Optional prefix for keys
        """
        if source_dict:
            for key, value in source_dict.items():
                target_dict[f"{prefix}{key}"] = value

    @staticmethod
    def list_transactions(session: Session) -> List[Transaction]:
        return list(session.exec(select(Transaction)).all())

    @staticmethod
    def serialize_transaction_row(tx: Transaction):

        customer = tx.customer
        variant = tx.variant
        outlet = tx.outlet
        sales_exec = tx.sales_executive
        user = tx.user

        car = variant.car if variant else None

        return {
            "id": tx.id,
            "status": tx.status,
            "stage": tx.stage,
            "mode": tx.mode,
            "customer_name": customer.name if customer else None,
            "mobile_number": customer.mobile_number if customer else None,
            "pan_number": customer.pan_number if customer else None,
            "car_name": car.name if car else None,
            "variant_name": variant.variant_name if variant else None,
            "outlet_name": outlet.name if outlet else None,
            "sales_executive_name": (sales_exec.name if sales_exec else None),
            "booking_date": tx.booking_date.isoformat() if tx.booking_date else None,
            "delivery_date": tx.delivery_date.isoformat() if tx.delivery_date else None,
            "booking_amt": tx.booking_amt,
            "invoice_number": tx.invoice_number,
            "registration_number": tx.registration_number,
            "price_offered_booking": tx.price_offered_booking,
            "total_discount_booking": tx.total_discount_booking,
            "total_actual_discount": tx.total_actual_discount,
            "total_allowed_discount": tx.total_allowed_discount,
            "total_excess_discount": tx.total_excess_discount,
            "payment_status": tx.payment_status,
            "audit_observations": tx.audit_info.get("observations", ""),
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
            "created_by": user.name if user else None,
        }

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
                setattr(transaction, field, payload[field])

        # MODEL YEAR
        transaction.model_year = (
            int(payload["model_year"]) if payload.get("model_year") else None
        )

        # JSON FIELDS
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
                setattr(transaction, field, payload.get(field) or {})

        # ITEMS
        TransactionService.create_transaction_items(session, transaction.id, payload)

        # ACCESSORIES
        if "accessory_ids" in payload:
            TransactionService.update_transaction_accessories(
                session, transaction, payload["accessory_ids"]
            )

        # RECONCILIATION
        TransactionService.apply_funds_reconciliation(session, transaction, payload)

        # UPDATED TIMESTAMP
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

        # Delete related TransactionItems
        items = session.exec(
            select(TransactionItem).where(
                TransactionItem.transaction_id == transaction_id
            )
        ).all()

        for item in items:
            session.delete(item)

        # Delete accessory links
        links = session.exec(
            select(TransactionAccessoryLink).where(
                TransactionAccessoryLink.transaction_id == transaction_id
            )
        ).all()

        for link in links:
            session.delete(link)

        # Delete main transaction
        session.delete(transaction)
        session.commit()
        return {"message": "Transaction deleted successfully", "id": transaction_id}
