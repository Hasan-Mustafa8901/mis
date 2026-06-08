# services/auth/dependencies.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlmodel import Session, select

from db.session import get_session
from db.models import User
from services.auth.config import SECRET_KEY_TOKEN, ALGORITHM

security = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY_TOKEN, algorithms=[ALGORITHM])
        # IMPORTANT: your token uses "sub"
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

    except JWTError as e:
        print("=" * 50)
        print("JWT ERROR:", str(e))
        print("=" * 50)

        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = session.exec(select(User).where(User.id == int(user_id))).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    return user
