# backend/auth/schemas.py
from pydantic import BaseModel
from db.models import UserRole


class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    outlet_id: int | None = None
    role: str = "auditor"


class UserLogin(BaseModel):
    name: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    role: str | UserRole
    outlet_id: int | None
