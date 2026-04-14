from sqlmodel import Session, select
from typing import Dict, Any, List, Optional
from db.models import (
    Transaction,
    TransactionItem,
    Customer,
    Variant,
    DiscountComponent,
    Employee,
    TransactionAccessoryLink,
    Accessory,
    User,
)
from services.discount.discount_service import DiscountService
from datetime import datetime


def normalize_conditions_delivery_checks(payload: dict) -> dict:
    payload["conditions"] = {
        k: bool(v) for k, v in payload.get("conditions", {}).items()
    }
    payload["delivery_checks"] = {
        k: bool(v) for k, v in payload.get("delivery_checks", {}).items()
    }
    return payload


def convert_date_fields(payload: dict, fields: List[str]) -> dict:
    for field in fields:
        if isinstance(payload.get(field), str):
            payload[field] = datetime.strptime(payload[field], "%Y-%m-%d").date()
    return payload


class TransactionService:
    @staticmethod
    def create_full_transaction(session: Session, payload: dict):

        # ─────────────────────────────
        # STEP 0: VALIDATION
        # ─────────────────────────────
        required = ["variant_id", "booking_date", "outlet_id", "sales_executive_id"]

        missing = [f for f in required if not payload.get(f)]
        if missing or not isinstance(payload.get("actual_amounts"), dict):
            raise ValueError(f"Missing fields: {', '.join(missing)}")

        # Normalize (convert to bool) for conditions and delivery checks to ensure consistent data types for logic processing. The API layer can also handle this, but we ensure it here for safety.)
        payload = normalize_conditions_delivery_checks(payload)

        # Convert dates (converts the dates from string to date objects, which is required for DB and logic processing. The API layer can also handle this, but we ensure it here for safety.)
        payload = convert_date_fields(payload, ["booking_date", "registration_date"])

        # Accessories variance
        # TODO: Check this part.
        acc = payload.get("accessories_details", {})
        if acc:
            charged = acc.get("charged_amount", 0)
            allowed = acc.get("allowed_amount", 0)
            acc["variance"] = charged - allowed
            payload["accessories_details"] = acc

        # ─────────────────────────────
        # STEP 1: RAW SAVE
        # Save all data as-is without any logic applied. This ensures we have a complete record of the original input for audit and debugging purposes.
        # ─────────────────────────────
        transaction = TransactionService.create_transaction_raw(session, payload)

        # ─────────────────────────────
        # STEP 2: AUDIT
        # ─────────────────────────────
        audit_result = DiscountService.calculate_discount(
            session,
            transaction.variant_id,
            transaction.id,
            transaction.booking_date,
            payload.get("actual_amounts", {}),
            transaction.conditions,
        )

        # ─────────────────────────────
        # STEP 3: APPLY AUDIT
        # ─────────────────────────────
        if transaction.id:
            transaction = TransactionService.update_transaction_with_audit(
                session, transaction.id, audit_result
            )

        # ─────────────────────────────
        # STEP 4: FUNDS RECONCILIATION
        # ─────────────────────────────
        TransactionService.apply_funds_reconciliation(
            session, transaction, payload, audit_result
        )

        session.commit()
        session.refresh(transaction)

        return {
            "id": transaction.id,
            "status": transaction.status,
            "summary": audit_result,
            "balance": transaction.balance_amount,
            "payment_status": transaction.payment_status,
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
        session.flush()  # get ID

        # ─────────────────────────────
        # 2. TRANSACTION CORE
        # ─────────────────────────────
        transaction = Transaction(
            customer_id=customer.id,
            variant_id=payload["variant_id"],
            outlet_id=payload["outlet_id"],
            sales_executive_id=payload["sales_executive_id"],
            created_by=payload.get("user_id", ""),
            booking_date=payload["booking_date"],
            # VEHICLE
            customer_file_number=payload.get("customer_file_number"),
            vin_number=payload.get("vin_number"),
            engine_number=payload.get("engine_number"),
            registration_number=payload.get("registration_number"),
            registration_date=payload.get("registration_date"),
            # CONDITIONS / CHECKS
            conditions=payload.get("conditions", {}),
            delivery_checks=payload.get("delivery_checks", {}),
            # JSON SECTIONS
            invoice_details=payload.get("invoice_details", {}),
            payment_details=payload.get("payment_details", {}),
            finance_details=payload.get("finance_details", {}),
            exchange_details=payload.get("exchange_details", {}),
            audit_info=payload.get("audit_info", {}),
        )
        session.add(transaction)
        session.flush()
        # ─────────────────────────────
        # 2. ACCESSORIES LINKING (NEW)
        # ─────────────────────────────
        accessory_ids = payload.get("accessory_ids", [])

        if accessory_ids:
            # validate accessories exist
            accessories = session.exec(
                select(Accessory).where(Accessory.id.in_(accessory_ids))
            ).all()

            valid_ids = {a.id for a in accessories}

            for acc_id in accessory_ids:
                if acc_id not in valid_ids:
                    continue  # or raise error if you want strict validation

                link = TransactionAccessoryLink(
                    transaction_id=transaction.id,
                    accessory_id=acc_id,
                )
                session.add(link)
        # ─────────────────────────────
        # 3. COMPONENT ITEMS (CRITICAL)
        # ─────────────────────────────
        actual_amounts = payload.get("actual_amounts", {})

        # Fetch all components
        components = session.exec(select(DiscountComponent)).all()

        comp_map = {comp.name: comp for comp in components}

        for name, actual in actual_amounts.items():
            comp = comp_map.get(name)
            if not comp:
                continue  # safety (validation already done in service)

            item = TransactionItem(
                transaction_id=transaction.id,
                component_id=comp.id,
                component_name=comp.name,
                component_type=comp.type,
                actual_amount=actual,
                allowed_amount=0,  # filled later
                difference=0,  # filled later
            )
            session.add(item)

        session.commit()
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
        user = (
            session.get(User, transaction.created_by)
            if transaction.created_by
            else None
        )
        if not transaction:
            return {}

        # 1. Start with metadata
        data = {
            "id": transaction.id,
            "status": transaction.status,
            "created_by": user.name if user else None,
            "created_at": transaction.created_at.isoformat()
            if transaction.created_at
            else None,
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
        data.update(
            {
                "car_name": variant.car.name if variant.car else None,
                "variant_name": variant.variant_name,
                "full_variant_name": variant.full_variant_name,
                "vin_number": transaction.vin_number,
                "engine_number": transaction.engine_number,
                "color": transaction.color,
                "model_year": variant.model_year,
                "registration_number": transaction.registration_number,
                "registration_date": transaction.registration_date.isoformat()
                if transaction.registration_date
                else None,
            }
        )

        # 4. Section 3: Transaction Core
        sales_exec = session.get(Employee, transaction.sales_executive_id)
        data.update(
            {
                "booking_date": transaction.booking_date.isoformat()
                if transaction.booking_date
                else None,
                "delivery_date": transaction.delivery_date.isoformat()
                if transaction.delivery_date
                else None,
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
            prefix = ""  # Could use section prefix if desired, but user wants MIS names
            data[f"{comp.name}_actual"] = item.actual_amount if item else 0.0
            data[f"{comp.name}_allowed"] = item.allowed_amount if item else 0.0
            data[f"{comp.name}_diff"] = item.difference if item else 0.0

        # 6. Section 5: Conditions
        for cond, val in transaction.conditions.items():
            data[f"cond_{cond}"] = val

        # 7. Section 6: Additional Sections (JSON)
        data.update(
            {f"exchange_{k}": v for k, v in transaction.exchange_details.items()}
        )
        data.update({f"finance_{k}": v for k, v in transaction.finance_details.items()})

        data.update(
            {f"checklist_{k}": v for k, v in transaction.delivery_checks.items()}
        )
        data.update({f"audit_{k}": v for k, v in transaction.audit_info.items()})
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
                "net_receivable": transaction.net_receivable,
                "total_received": transaction.total_received,
                "balance_amount": transaction.balance_amount,
            }
        )

        # 8. Totals
        data.update(
            {
                "total_allowed_discount": transaction.total_allowed_discount,
                "total_actual_discount": transaction.total_actual_discount,
                "total_excess_discount": transaction.total_excess_discount,
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
        # audit_result: Dict[str, Any],
    ):

        from sqlmodel import select
        from db.models import TransactionItem

        items = session.exec(
            select(TransactionItem).where(
                TransactionItem.transaction_id == transaction.id
            )
        ).all()

        ON_ROAD_COMPONENTS = {
            "ex showroom price",
            "insurance",
            "registration",
            "hyundai genuine acc kit",
            "tcs",
            "fastag",
            "ext warr",
            "shield of trust",
        }
        total_on_road = 0.0

        for item in items:
            if item.component_name.lower().strip() in ON_ROAD_COMPONENTS:
                total_on_road += item.actual_amount

        # accessory_total = sum(
        #     acc.listed_price for acc in transaction.accessories
        # )
        # total_on_road += accessory_total

        DISCOUNT_COMPONENTS = {
            "cash discount all customers",
            "additional discount from dealer",
            "extra kitty on tr cases",
            "additional for poi /corporate customers",
            "additional for exchange customers",
            "additional for scrappage customers",
            "additional for upward sales customers",
        }

        total_discount = 0.0

        for item in items:
            if item.component_name.lower().strip() in DISCOUNT_COMPONENTS:
                total_discount += item.actual_amount

        total_receivable = total_on_road - total_discount

        payments = payload.get("payment_details", {})

        total_received = (
            payments.get("bank", 0)
            + payments.get("cash", 0)
            + payments("finance", 0)
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

        session.add(transaction)
        session.flush()

    @staticmethod
    def update_transaction_with_audit(
        session: Session, transaction_id: int, audit_result: dict
    ):

        from db.models import Transaction, TransactionItem
        from sqlmodel import select

        # ─────────────────────────────
        # 1. FETCH TRANSACTION
        # ─────────────────────────────
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")

        # ─────────────────────────────
        # 2. UPDATE TOTALS
        # ─────────────────────────────
        transaction.total_actual_discount = audit_result["invoice_discount"]
        transaction.total_allowed_discount = audit_result["pricelist_discount"]
        transaction.total_excess_discount = audit_result["excess_discount"]
        transaction.status = audit_result["status"]
        # ─────────────────────────────
        # 3. FETCH EXISTING ITEMS
        # ─────────────────────────────
        items = session.exec(
            select(TransactionItem).where(
                TransactionItem.transaction_id == transaction_id
            )
        ).all()

        item_map = {item.component_id: item for item in items}

        # ─────────────────────────────
        # 4. UPDATE ITEMS FROM AUDIT
        # ─────────────────────────────
        transaction.total_actual_discount = audit_result["invoice_discount"]
        transaction.total_allowed_discount = audit_result["pricelist_discount"]
        transaction.total_excess_discount = audit_result["excess_discount"]
        transaction.status = audit_result["status"]

        # ─────────────────────────────
        # 5. SAVE
        # ─────────────────────────────
        session.add(transaction)
        session.flush()
        return transaction
