# backend/auth/schemas.py
from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    password: str
    role: str = "auditor"


class UserLogin(BaseModel):
    name: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
