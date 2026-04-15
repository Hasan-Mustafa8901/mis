# backend/auth/routes.py
from fastapi import APIRouter, Depends
from sqlmodel import Session

from db.session import get_session
from schemas.auth import UserCreate, UserLogin, TokenResponse
from services.auth.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
def register(payload: UserCreate, session: Session = Depends(get_session)):
    user = AuthService.register(session, payload.name, payload.password, payload.role)
    return {"id": user.id, "name": user.name, "role": user.role}


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, session: Session = Depends(get_session)):
    token = AuthService.login(session, payload.name, payload.password)
    return {"access_token": token}


@router.post("/logout")
def logout():
    return {"message": "Logged Out Successfully."}
