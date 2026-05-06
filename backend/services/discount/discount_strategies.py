from abc import ABC, abstractmethod
from typing import Dict, Any
from db.models import PriceList, Transaction
from services.price_list.price_list_service import PriceListService
from rich import print


class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(
        self,
        session,
        transaction: Transaction,
        actual_amounts: dict[str, int | float],
        conditions: dict[str, bool],
    ) -> Dict[str, Any]:
        pass


class BookingDiscountStrategy(DiscountStrategy):
    def calculate(self, session, transaction, actual_amounts, conditions):

        price_list: PriceList = PriceListService.get_active_price_list(
            session, transaction.booking_date, transaction.model_year
        )
        if price_list.id:
            allowed_map = PriceListService.get_allowed_amounts(
                session, price_list.id, transaction.variant_id, conditions
            )

        components = PriceListService.get_all_components(session)

        # actual discount
        price_offered = transaction.booking_price_offered

        # pricelist discount
        price_pricelist = sum(
            allowed_map.get(comp.id, 0)
            for comp in components
            if "price" in comp.name.lower()
        )
        discount_pricelist = sum(
            allowed_map.get(comp.id, 0)
            for comp in components
            if "discount" in comp.name.lower()
        )

        total_discount = price_pricelist - price_offered

        excess = total_discount - discount_pricelist

        audit_result = {
            "total_actual_discount": total_discount,
            "pricelist_discount": discount_pricelist,
            "excess_discount": excess or 0.0,
            "status": "Excess" if excess > 0 else "No Excess Discount",
        }
        return audit_result


class DeliveryDiscountStrategy(DiscountStrategy):
    @staticmethod
    def total_invoice_value(transaction) -> float:
        invoice = transaction.invoice_details or {}

        invoice_values = {
            "taxable_value": invoice.get("taxable_value", 0.0),
            "cgst": invoice.get("cgst", 0.0),
            "sgst": invoice.get("sgst", 0.0),
            "igst": invoice.get("igst", 0.0),
            "cess": invoice.get("cess", 0.0),
        }
        sum = 0
        for value in invoice_values.values():
            sum += value
        return sum

    def calculate(self, session, transaction, actual_amounts, conditions):

        price_list = PriceListService.get_active_price_list(
            session,
            transaction.booking_date,
            transaction.model_year,
        )

        allowed_map = PriceListService.get_allowed_amounts(
            session, price_list.id, transaction.variant_id, conditions
        )

        components = PriceListService.get_all_components(session)

        total_invoice_value = self.total_invoice_value(transaction)

        actual_ex_showroom = actual_amounts.get("Ex Showroom Price", 0)

        invoice_discount = actual_ex_showroom - total_invoice_value

        pricelist_discount = sum(
            allowed_map.get(comp.id, 0)
            for comp in components
            if "discount" in comp.name.lower()
        )
        excess = invoice_discount - pricelist_discount

        audit_result = {
            "total_actual_discount": sum(
                v for k, v in actual_amounts.items() if "discount" in k.lower()
            ),
            "pricelist_discount": pricelist_discount,
            "invoice_discount": invoice_discount,
            "excess_discount": excess,
            "status": "Excess" if excess > 0 else "Excess Discount",
        }
        return audit_result
