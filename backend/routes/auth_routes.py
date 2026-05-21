# backend/auth/routes.py
from fastapi import APIRouter, Depends
from db.session import get_session
from schemas.auth import UserCreate, UserLogin, TokenResponse
from services.auth.auth_service import AuthService
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from db.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/users")
def get_users(session: Session = Depends(get_session)):

    users = session.exec(select(User).options(selectinload(User.outlet))).all()

    return [
        {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "role": (
                user.role.value if hasattr(user.role, "value") else str(user.role)
            ),
            "outlet": (
                {
                    "id": user.outlet.id,
                    "name": user.outlet.name,
                }
                if user.outlet
                else None
            ),
            "is_active": user.is_active,
            "is_logged_in": user.is_logged_in,
            "created_at": user.created_at,
        }
        for user in users
    ]


@router.post("/register")
def register(payload: UserCreate, session: Session = Depends(get_session)):
    user = AuthService.register(
        session,
        payload.name,
        payload.username,
        payload.password,
        payload.role,
        payload.outlet_id,
    )
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "outlet_id": user.outlet_id,
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, session: Session = Depends(get_session)):
    login_info = AuthService.login(session, payload.name, payload.password)
    return login_info


@router.post("/logout")
def logout():
    return {"message": "Logged Out Successfully."}
