# backend\services\reports\daily\filters.py
from db.models import Outlet


def apply_outlet_filter(
    stmt,
    model,
    outlet_id: int | None = None,
):
    if outlet_id is not None:
        stmt = stmt.where(model.outlet_id == outlet_id)

    return stmt


def apply_dealership_filter(
    stmt,
    model,
    dealership_id: int | None = None,
):
    if dealership_id is not None:
        stmt = stmt.join(
            Outlet,
            Outlet.id == model.outlet_id,
        ).where(Outlet.dealership_id == dealership_id)

    return stmt


def apply_scope_filters(
    stmt,
    model,
    dealership_id: int | None = None,
    outlet_id: int | None = None,
):
    """
    outlet_id takes precedence over dealership_id
    """

    if outlet_id is not None:
        return apply_outlet_filter(
            stmt=stmt,
            model=model,
            outlet_id=outlet_id,
        )

    if dealership_id is not None:
        return apply_dealership_filter(
            stmt=stmt,
            model=model,
            dealership_id=dealership_id,
        )

    return stmt
