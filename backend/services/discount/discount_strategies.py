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
        print(__class__, "Price List", price_list.name)

        allowed_map = PriceListService.get_allowed_amounts(
            session, price_list.id, transaction.variant_id, conditions
        )
        print(__class__, "Allowed Map", allowed_map)

        components = PriceListService.get_all_components(session)
        print(__class__, "Len(comp):", len(components))

        # actual discount
        actual_discount = sum(
            value
            for name, value in actual_amounts.items()
            if "discount" in name.lower()
        )

        # pricelist discount
        pricelist_discount = sum(
            allowed_map.get(comp.id, 0)
            for comp in components
            if "discount" in comp.name.lower()
        )

        excess = actual_discount - pricelist_discount

        for name, value in actual_amounts.items():
            if value is None:
                continue

            if "discount" in name.lower():
                actual_discount += float(value)

        audit_result = {
            "total_actual_discount": actual_discount or 0.0,
            "pricelist_discount": pricelist_discount or 0.0,
            "invoice_discount": None,
            "excess_discount": excess or 0.0,
            "status": "Excess" if excess > 0 else "No Excess Discount",
        }
        print(__class__, "Summary:", audit_result)
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
        print(f"{__class__} :\n{audit_result}")
        return audit_result
