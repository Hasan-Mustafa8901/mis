from fastapi import HTTPException
from sqlmodel import Session
from datetime import date
from typing import Dict, Any
from services.price_list.price_list_service import PriceListService
from db.models import Transaction
from services.utils import normalize_component_name
import logging

from rich import print

logger = logging.getLogger(__name__)


class DiscountService:
    @staticmethod
    def extract_invoice_values(transaction) -> Dict[str, float]:
        invoice = transaction.invoice_details or {}
        print(f"extract_invoice_values : Extracted invoice details: {invoice=}\n")

        return {
            "taxable_value": invoice.get("taxable_value", 0.0),
            "cgst": invoice.get("cgst", 0.0),
            "sgst": invoice.get("sgst", 0.0),
            "igst": invoice.get("igst", 0.0),
            "cess": invoice.get("cess", 0.0),
        }

    @staticmethod
    def get_ex_showroom_price(session, price_list_id, variant_id, conditions):
        print(
            f"get_ex_showroom_price : Fetching ex-showroom price for price_list_id={price_list_id}, variant_id={variant_id}, conditions={conditions}\n"
        )
        allowed_map = PriceListService.get_allowed_amounts(
            session, price_list_id, variant_id, conditions
        )

        components = PriceListService.get_all_components(session)

        for comp in components:
            if comp.name.lower().strip() == "ex showroom price" and comp.id is not None:
                return allowed_map.get(comp.id, 0.0)

        return 0.0

    @staticmethod
    def calculate_discount(
        session: Session,
        variant_id: int,
        transaction_id: int,
        booking_date: date,
        actual_amounts: Dict[str, float],  # Key: component name (MIS name)
        conditions: Dict[str, bool],
    ) -> Dict[str, Any]:
        """
        Main calculation engine for MIS Audit. (PURE LOGIC ONLY)
        """
        # STEP 1: Fetch Price List
        price_list = PriceListService.get_active_price_list(session, booking_date)
        if not price_list:
            raise ValueError(f"No active price list found for date {booking_date}")
        print(
            f"calculate_discount : Using price list '{price_list.name}' (ID: {price_list.id}) for booking date {booking_date}\n"
        )
        print(f"calculate_discount : Using price list {price_list=}\n")

        # STEP 2: Fetch Allowed Values
        if price_list.id:
            allowed_map = PriceListService.get_allowed_amounts(
                session, price_list.id, variant_id, conditions
            )
            print(f"calculate_discount : Allowed amounts map: {allowed_map=}\n")

        # STEP 3: Iterate ALL components
        all_components = PriceListService.get_all_components(session)
        print(
            f"calculate_discount : Allowed amounts map: all_components: {[comp.name for comp in all_components]}\n"
        )

        audit_items = []
        total_actual_discount = 0.0
        total_allowed_discount = 0.0

        # STEP 3.5: Validate Component Keys
        # here there can be a bug !!!
        db_component_names = {
            normalize_component_name(comp.name) for comp in all_components
        }
        print(f"calculate_discount : DB component names: {db_component_names}\n")
        input_component_names = {
            normalize_component_name(k) for k in actual_amounts.keys()
        }
        print(f"calculate_discount : Input component names: {input_component_names}\n")

        unknown_keys = input_component_names - db_component_names
        print(f"calculate_discount : Unknown component keys in input: {unknown_keys}\n")
        if unknown_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid component names in input: {', '.join(unknown_keys)}",
            )

        normalized_actuals = {
            normalize_component_name(k): v for k, v in actual_amounts.items()
        }
        print(
            f"calculate_discount : Normalized actual amounts: {normalized_actuals=}\n"
        )

        # Highlight in code using comments the space where you're calculating the discount I will review the discount logic.
        # ==========================================
        # NEW DISCOUNT LOGIC (INVOICE BASED)
        # ==========================================

        # STEP 1: Get transaction (needed for invoice details)
        transaction = session.get(
            Transaction, transaction_id
        )  # Here we can pass transaction_id as parameter if needed
        if not transaction:
            raise ValueError("Transaction not found for discount calculation")

        # STEP 2: Extract invoice values
        invoice_vals = DiscountService.extract_invoice_values(transaction)

        taxable = invoice_vals["taxable_value"]
        cgst = invoice_vals["cgst"]
        sgst = invoice_vals["sgst"]
        igst = invoice_vals["igst"]
        cess = invoice_vals["cess"]

        # STEP 3: Get Ex-showroom price
        ex_showroom = DiscountService.get_ex_showroom_price(
            session, price_list.id, variant_id, conditions
        )

        # STEP 4: Compute Discount
        calculated_discount = ex_showroom - (taxable + cgst + sgst + igst + cess)

        # STEP 5: Get actual discounts from input
        normalized_actuals = {
            normalize_component_name(k): v for k, v in actual_amounts.items()
        }
        # TODO: Don't hardcode these keys, instead we should have a mapping in DB for which components are considered "base discount"
        # and which are "additional discounts"
        base_discount = normalized_actuals.get("cashdiscountallcustomers", 0.0)

        additional_discount = sum(
            [
                normalized_actuals.get("additionaldiscountfromdealer", 0.0),
                normalized_actuals.get("extrakittyontrcases", 0.0),
                normalized_actuals.get("additionalforpoicorporatecustomers", 0.0),
                normalized_actuals.get("additionalforexchangecustomers", 0.0),
                normalized_actuals.get("additionalforscrappagecustomers", 0.0),
                normalized_actuals.get("additionalforupwardsalescustomers", 0.0),
            ]
        )

        total_actual_discount = base_discount + additional_discount
        total_allowed_discount = calculated_discount

        # STEP 6: Excess
        total_excess_discount = total_actual_discount - total_allowed_discount

        # STEP 7: Status
        status = "Excess" if total_excess_discount > 0 else "UnderLimit"

        # OPTIONAL: Keep items for compatibility (minimal)
        audit_items = {
            "component_name": "Calculated Discount",
            "actual_discount": total_actual_discount,
            "allowed_discount": total_allowed_discount,
            "excess_discount": total_excess_discount,
            "status": status,
        }

        return audit_items
