from .discount_strategies import (
    DeliveryDiscountStrategy,
    BookingDiscountStrategy,
    DiscountStrategy,
)
from rich import print

import logging

logger = logging.getLogger(__name__)


class DiscountStrategyFactory:
    @staticmethod
    def get_strategy(stage: str) -> DiscountStrategy:
        print(f"DEBUG: DiscountStrategyFactory.get_strategy for stage='{stage}'")
        if stage == "booking":
            return BookingDiscountStrategy()

        elif stage == "delivery":
            return DeliveryDiscountStrategy()

        raise ValueError(f"Unsupported stage: {stage}")


class DiscountService:
    @staticmethod
    def calculate_discount(
        session,
        transaction,
        actual_amounts,
        conditions,
    ):
        print(__class__, "called")

        strategy = DiscountStrategyFactory.get_strategy(transaction.stage)

        return strategy.calculate(
            session=session,
            transaction=transaction,
            actual_amounts=actual_amounts,
            conditions=conditions,
        )
