# backend\services\reports\monthly\filters.py
from db.models import Outlet


def apply_dealership_filter(stmt, model, dealership_id: int | None):
    if dealership_id is None:
        return stmt

    return stmt.join(Outlet, Outlet.id == model.outlet_id).where(
        Outlet.dealership_id == dealership_id
    )
