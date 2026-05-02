# backend/auth/routes.py
from fastapi import APIRouter, Depends
from sqlmodel import Session

from db.session import get_session
from schemas.auth import UserCreate, UserLogin, TokenResponse
from services.auth.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(payload: UserCreate, session: Session = Depends(get_session)):
    print(payload)
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
