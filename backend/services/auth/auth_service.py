# backend/auth/service.py
from sqlmodel import Session, select
from fastapi import HTTPException
from services.utils import get_ist_now

from db.models import User, UserRole
from services.auth.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE

from passlib.context import CryptContext
from jose import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return pwd_context.verify(password, hashed)

    @staticmethod
    def register(
        session: Session,
        name: str,
        username: str,
        password: str,
        role: str,
        outlet_id: int | None = None,
    ):
        existing = session.exec(select(User).where(User.name == name)).first()
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        hashed = AuthService.hash_password(password)

        user_role = UserRole(role)

        user = User(
            name=name,
            username=username,
            password_hash=hashed,
            role=user_role,
            outlet_id=outlet_id,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def login(session: Session, username: str, password: str):
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User Not Found")

        if not AuthService.verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = AuthService.create_access_token({"sub": str(user.id)})

        return {
            "access_token": token,
            "name": user.name,
            "outlet_id": user.outlet_id,
            "role": UserRole(user.role),
        }

    @staticmethod
    def create_access_token(data: dict):
        to_encode = data.copy()
        expire = get_ist_now() + ACCESS_TOKEN_EXPIRE
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
