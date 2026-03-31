from sqlmodel import Session, select, desc, col
from datetime import date
from typing import Dict, Optional
from db.models import PriceList, PriceListItem, DiscountComponent
from rich import print

import logging

logger = logging.getLogger(__name__)


class PriceListService:
    @staticmethod
    def get_active_price_list(
        session: Session, booking_date: date
    ) -> Optional[PriceList]:
        """
        Finds the price list valid for the given date.
        Historical support: looks for a list where valid_from <= date <= valid_to.
        If multiple, the one with the latest valid_from is preferred (most specific).
        """
        statement = (
            select(PriceList)
            .where(PriceList.valid_from <= booking_date)
            .order_by(desc(PriceList.valid_from))
        )

        all_pricelists = session.exec(statement).all()
        print(
            f"get_active_price_list : Found {len(all_pricelists)} price lists for date {booking_date}\n{all_pricelists=}"
        )
        for active_pricelist in all_pricelists:
            if (
                active_pricelist.valid_to is None
                or active_pricelist.valid_to >= booking_date
            ):
                return active_pricelist
        return None

    @staticmethod
    def get_all_components(session: Session) -> list[DiscountComponent]:
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
        print(
            f"get_allowed_amounts : Found {len(items)} price list items for price_list_id {price_list_id} and variant_id {variant_id}\n{items=}\n"
        )

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
        print(f"get_allowed_amounts : Computed allowed amounts map: {allowed_map=}")

        return allowed_map
