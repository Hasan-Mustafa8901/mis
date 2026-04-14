from fastapi import HTTPException
from sqlmodel import Session
from datetime import date
from typing import Dict, Any

from services.price_list.price_list_service import PriceListService
from db.models import Transaction
from services.utils import normalize_component_name
from rich import print

import logging

logger = logging.getLogger(__name__)


class DiscountService:
    # =========================
    # 1. FETCH TRANSACTION
    # =========================
    @staticmethod
    def get_transaction(session: Session, transaction_id: int) -> Transaction:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            raise ValueError("Transaction not found")
        return transaction

    # =========================
    # 2. EXTRACT INVOICE VALUES
    # =========================
    @staticmethod
    def extract_invoice_values(transaction) -> Dict[str, float]:
        invoice = transaction.invoice_details or {}

        return {
            "taxable_value": invoice.get("taxable_value", 0.0),
            "cgst": invoice.get("cgst", 0.0),
            "sgst": invoice.get("sgst", 0.0),
            "igst": invoice.get("igst", 0.0),
            "cess": invoice.get("cess", 0.0),
        }

    # =========================
    # 3. GET PRICE LIST
    # =========================
    @staticmethod
    def get_price_list(session: Session, booking_date: date):
        price_list = PriceListService.get_active_price_list(session, booking_date)
        if not price_list:
            raise ValueError(f"No active price list found for date {booking_date}")
        return price_list

    # =========================
    # 4. GET ALLOWED MAP
    # =========================
    @staticmethod
    def get_allowed_map(session, price_list_id, variant_id, conditions):
        return PriceListService.get_allowed_amounts(
            session, price_list_id, variant_id, conditions
        )

    # =========================
    # 5. GET EX-SHOWROOM
    # =========================
    @staticmethod
    def get_ex_showroom_price(session, price_list_id, variant_id, conditions):
        allowed_map = DiscountService.get_allowed_map(
            session, price_list_id, variant_id, conditions
        )

        components = PriceListService.get_all_components(session)

        for comp in components:
            if comp.name.lower().strip() == "ex showroom price" and comp.id:
                return allowed_map.get(comp.id, 0.0)

        return 0.0

    # =========================
    # 6. NORMALIZE INPUT
    # =========================
    @staticmethod
    def normalize_actuals(actual_amounts: Dict[str, float]):
        return {normalize_component_name(k): v for k, v in actual_amounts.items()}

    # =========================
    # 7. VALIDATE INPUT KEYS
    # =========================
    @staticmethod
    def validate_components(all_components, actual_amounts):
        db_keys = {normalize_component_name(c.name) for c in all_components}
        input_keys = {normalize_component_name(k) for k in actual_amounts.keys()}

        unknown = input_keys - db_keys
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid component names: {', '.join(unknown)}",
            )

    # =========================
    # 8. CALCULATE INVOICE DISCOUNT
    # =========================
    @staticmethod
    def calculate_invoice_discount(
        ex_showroom, taxable_value, cgst=0.0, sgst=0.0, igst=0.0, cess=0.0
    ):
        # ✅ CORRECT BUSINESS LOGIC
        return round((ex_showroom - taxable_value - cgst - sgst - igst - cess), 2)

    # =========================
    # 9. CALCULATE PRICELIST DISCOUNT
    # =========================
    @staticmethod
    def calculate_pricelist_discount(allowed_map, components):
        discount_ids = []

        for comp in components:
            name = normalize_component_name(comp.name)

            if "discount" in name:
                discount_ids.append(comp.id)

        return sum(allowed_map.get(cid, 0.0) for cid in discount_ids if cid)

    # =========================
    # 10. CALCULATE PRICE VARIANCE
    # DO NOT DELETE THIS METHOD, EVEN WHEN IT IS BEING UNUSED
    # =========================
    @staticmethod
    def calculate_price_variance(normalized_actuals, allowed_map, components):
        variance = 0.0

        for comp in components:
            if comp.type != "price":
                continue

            comp_id = comp.id
            if not comp_id:
                continue

            # get actual using normalized name
            norm_name = normalize_component_name(comp.name)
            actual = normalized_actuals.get(norm_name, 0.0)

            allowed = allowed_map.get(comp_id, 0.0)

            variance += actual - allowed

        return variance

    # =========================
    # 11. MAIN CALCULATION
    # =========================
    @staticmethod
    def calculate_discount(
        session: Session,
        variant_id: int,
        transaction_id: int,
        booking_date: date,
        actual_amounts: Dict[str, float],
        conditions: Dict[str, bool],
    ) -> Dict[str, Any]:

        # STEP 1: Fetch core data
        transaction = DiscountService.get_transaction(session, transaction_id)
        price_list = DiscountService.get_price_list(session, booking_date)

        allowed_map = DiscountService.get_allowed_map(
            session, price_list.id, variant_id, conditions
        )
        print(f"calculate_discount : Allowed amounts map: {allowed_map=}\n")

        all_components = PriceListService.get_all_components(session)
        print(
            f"calculate_discount : Allowed amounts map: all_components: {[comp.name for comp in all_components]}\n"
        )

        # STEP 2: Validate + normalize
        DiscountService.validate_components(all_components, actual_amounts)
        normalized_actuals = DiscountService.normalize_actuals(actual_amounts)
        print(
            f"calculate_discount : Normalized actual amounts: {normalized_actuals=}\n"
        )

        # STEP 3: Extract invoice
        invoice_vals = DiscountService.extract_invoice_values(transaction)
        taxable = invoice_vals.get("taxable_value", 0.0)
        cgst = invoice_vals.get("cgst", 0.0)
        sgst = invoice_vals.get("sgst", 0.0)
        igst = invoice_vals.get("igst", 0.0)
        cess = invoice_vals.get("cess", 0.0)

        # STEP 4: Ex-showroom
        ex_showroom = DiscountService.get_ex_showroom_price(
            session, price_list.id, variant_id, conditions
        )

        # ==========================================
        # 🔥 FINAL BUSINESS LOGIC
        # ==========================================

        # 1. Invoice Discount
        invoice_discount = DiscountService.calculate_invoice_discount(
            ex_showroom, taxable, cgst, sgst, igst, cess
        )
        print(f"calculate_discount : Invoice discount: {invoice_discount=}\n")
        # 2. Pricelist Discount
        pricelist_discount = DiscountService.calculate_pricelist_discount(
            allowed_map, all_components
        )
        print(f"calculate_discount : Pricelist discount: {pricelist_discount=}\n")

        # 3. Price Variance
        # price_variance = DiscountService.calculate_price_variance(
        #     normalized_actuals, allowed_map, all_components
        # )

        # 4. Excess Discount
        excess_discount = invoice_discount - pricelist_discount
        print(f"calculate_discount : Excess discount: {excess_discount=}\n")

        # 5. Status
        status = "Excess Discount" if excess_discount > 0 else "No Excess Discount"
        print(f"calculate_discount : Status: {status=}\n")

        return {
            "invoice_discount": invoice_discount,
            "pricelist_discount": pricelist_discount,
            # "price_variance": price_variance,
            "excess_discount": excess_discount,
            "status": status,
        }
