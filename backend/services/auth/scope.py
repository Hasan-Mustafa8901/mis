from fastapi import HTTPException

from db.models import User, UserRole


def is_admin(user: User) -> bool:

    return user.role == UserRole.ADMIN


def get_allowed_outlets(user: User):

    # ADMIN = unrestricted
    if is_admin(user):
        return None

    return user.allowed_outlet_ids or []


def apply_outlet_scope(
    stmt,
    model,
    user: User,
):

    allowed = get_allowed_outlets(user)

    # ADMIN
    if allowed is None:
        return stmt

    # NO ACCESS
    if not allowed:
        return stmt.where(False)

    return stmt.where(model.outlet_id.in_(allowed))


def validate_outlet_access(
    user: User,
    outlet_id: int,
):

    allowed = get_allowed_outlets(user)

    # ADMIN
    if allowed is None:
        return

    if outlet_id not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Outlet access denied",
        )
