# backend/auth/schemas.py
from pydantic import BaseModel
from db.models import UserRole


class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    allowed_outlet_ids: list[int] = []
    role: str = "audit_assistant"


class UserLogin(BaseModel):
    name: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: int
    name: str
    role: str | UserRole
    allowed_outlet_ids: list[int]
