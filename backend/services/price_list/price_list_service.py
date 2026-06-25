from sqlmodel import Session, select, desc, col
from datetime import date
from typing import Dict, Optional
from sqlalchemy.orm import selectinload
from db.models import PriceList, PriceListItem, DiscountComponent, Transaction

import logging

logger = logging.getLogger(__name__)


class PriceListService:
    @staticmethod
    def get_active_price_list(
        session: Session, booking_date: date, model_year: int
    ) -> Optional[PriceList]:
        """
        Finds the price list valid for the given date.
        Historical support: looks for a list where valid_from <= date <= valid_to.
        If multiple, the one with the latest valid_from is preferred (most specific).
        """
        statement = (
            select(PriceList)
            .where(
                PriceList.valid_from <= booking_date, PriceList.model_year == model_year
            )
            .order_by(desc(PriceList.valid_from))
        )

        all_pricelists = session.exec(statement).all()

        for active_pricelist in all_pricelists:
            if (
                active_pricelist.valid_to is None
                or active_pricelist.valid_to >= booking_date
            ):
                return active_pricelist
        return None

    @staticmethod
    def get_all_components(session: Session) -> list[DiscountComponent]:
        """
        Retrieves all discount components ordered by their display order.
        """
        return list(
            session.exec(
                select(DiscountComponent).order_by(col(DiscountComponent.order))
            ).all()
        )

    @staticmethod
    def get_allowed_amounts(
        session: Session,
        price_list_id: int,
        variant_id: int,
        conditions: Dict[str, bool],
    ) -> Dict[int, float]:
        """
        Fetches allowed amounts for all components for a variant.
        Handles condition-based logic stored in PriceListItem.conditions.
        Returns a dict of {component_id: allowed_amount}.
        """
        statement = select(PriceListItem).where(
            PriceListItem.price_list_id == price_list_id,
            PriceListItem.variant_id == variant_id,
        )
        items = session.exec(statement).all()

        allowed_map = {}
        for item in items:
            # Multi-condition logic: if item has conditions, all must be met by the input 'conditions'
            # Example condition: {"corporate": True}
            meets_conditions = True
            if item.conditions:
                for key, val in item.conditions.items():
                    if conditions.get(key) != val:
                        meets_conditions = False
                        break

            if meets_conditions:
                if item.component_id in allowed_map:
                    logger.warning(
                        f"Overwriting allowed value for component_id {item.component_id} in price list {price_list_id}"
                    )
                allowed_map[item.component_id] = item.allowed_amount

        return allowed_map

    @staticmethod
    def update_allowed_amounts(session: Session, price_list: PriceList) -> int:
        """
        Updates stored transaction item allowed amounts for transactions covered by
        the given price list interval and model year.
        """
        if not price_list.id:
            return 0

        statement = (
            select(Transaction)
            .where(
                Transaction.booking_date >= price_list.valid_from,
                Transaction.model_year == price_list.model_year,
            )
            .options(selectinload(Transaction.items))  # type: ignore
        )

        if price_list.valid_to is not None:
            statement = statement.where(Transaction.booking_date <= price_list.valid_to)

        components = PriceListService.get_all_components(session)
        discount_component_ids = {
            component.id for component in components if component.type == "discount"
        }
        transactions = session.exec(statement).all()
        updated_count = 0

        for transaction in transactions:
            allowed_map = PriceListService.get_allowed_amounts(
                session,
                price_list.id,
                transaction.variant_id,
                transaction.conditions or {},
            )

            transaction_updated = False
            allowed_discount_total = sum(
                allowed_map.get(component_id, 0.0)
                for component_id in discount_component_ids
            )

            for item in transaction.items:
                allowed_amount = float(allowed_map.get(item.component_id, 0.0))

                if item.allowed_amount != allowed_amount:
                    item.allowed_amount = allowed_amount
                    transaction_updated = True

                difference = allowed_amount - (item.actual_amount or 0.0)
                if item.difference != difference:
                    item.difference = difference
                    transaction_updated = True

            if transaction.stage == "delivery":
                transaction.total_allowed_discount = allowed_discount_total
                transaction.total_excess_discount = (
                    transaction.total_actual_discount - allowed_discount_total
                )
                transaction.status = (
                    "Excess Discount"
                    if transaction.total_excess_discount > 0
                    else "No Excess Discount"
                )
                transaction_updated = True
            elif transaction.stage == "booking":
                transaction.excess_booking = (
                    transaction.total_discount_booking - allowed_discount_total
                )
                transaction.status = (
                    "Excess Discount"
                    if transaction.excess_booking > 0
                    else "No Excess Discount"
                )
                transaction_updated = True

            if transaction_updated:
                session.add(transaction)
                updated_count += 1

        session.flush()
        return updated_count
