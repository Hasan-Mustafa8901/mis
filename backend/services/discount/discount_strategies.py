from abc import ABC, abstractmethod
from typing import Dict, Any
from rich import print


class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(
        self,
        session,
        transaction,
        actual_amounts: Dict[str, float],
        conditions: Dict[str, bool],
    ) -> Dict[str, Any]:
        pass


class BookingDiscountStrategy(DiscountStrategy):
    def calculate(self, session, transaction, actual_amounts, conditions):
        from services.price_list.price_list_service import PriceListService

        price_list = PriceListService.get_active_price_list(
            session, transaction.booking_date
        )

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
        print(f"Price Offered: {price_offered}")
        print(f"Price Pricelist: {price_pricelist}")
        print(f"Discount Pricelist: {discount_pricelist}")

        total_discount = price_pricelist - price_offered

        excess = total_discount - discount_pricelist

        audit_result = {
            "total_discount": total_discount,
            "excess_discount": excess or 0.0,
            "status": "Excess" if excess > 0 else "No Excess Discount",
        }
        print(__class__, "BookingDiscount Summary:", audit_result)
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
        print(__class__, "called")
        from services.price_list.price_list_service import PriceListService

        price_list = PriceListService.get_active_price_list(
            session, transaction.booking_date
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
        print(f"{__class__} DeliveryDiscount Summary:\n{audit_result}")
        return audit_result
