from fastapi import Depends, HTTPException

from db.models import User

from services.auth.dependencies import (
    get_current_user,
)


def require_roles(*allowed_roles):

    def checker(
        current_user: User = Depends(get_current_user),
    ):

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

        return current_user

    return checker
