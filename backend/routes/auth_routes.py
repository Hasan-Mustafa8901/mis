# backend/auth/routes.py
from fastapi import APIRouter, Depends
from db.session import get_session
from schemas.auth import UserCreate, UserLogin, TokenResponse
from services.auth.auth_service import AuthService
from services.auth.dependencies import get_current_user
from sqlmodel import Session, select
from db.models import User, Outlet

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/users")
def get_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    users = session.exec(select(User)).all()

    # FETCH ALL OUTLETS
    all_outlets = session.exec(select(Outlet)).all()

    outlet_map = {
        outlet.id: {
            "id": outlet.id,
            "name": outlet.name,
        }
        for outlet in all_outlets
    }

    # RESPONSE
    return [
        {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "role": (
                user.role.value if hasattr(user.role, "value") else str(user.role)
            ),
            "allowed_outlet_ids": (user.allowed_outlet_ids or []),
            "allowed_outlets": [
                outlet_map[outlet_id]
                for outlet_id in (user.allowed_outlet_ids or [])
                if outlet_id in outlet_map
            ],
            "is_active": user.is_active,
            "is_logged_in": user.is_logged_in,
            "created_at": user.created_at,
        }
        for user in users
    ]


@router.post("/register")
def register(
    payload: UserCreate,
    session: Session = Depends(get_session),
):
    print("\n\n\nREGISTER PAYLOAD: ", payload, "\n\n\n")
    user = AuthService.register(
        session=session,
        name=payload.name,
        username=payload.username,
        password=payload.password,
        role=payload.role,
        allowed_outlet_ids=payload.allowed_outlet_ids,
    )

    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "allowed_outlet_ids": (user.allowed_outlet_ids),
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, session: Session = Depends(get_session)):
    login_info = AuthService.login(session, payload.name, payload.password)
    return login_info


@router.post("/logout")
def logout():
    return {"message": "Logged Out Successfully."}
