from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import secrets
import string
from app.config import settings
from app.schemas import TokenData
from app.models import User, RefreshToken, PasswordResetToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def create_refresh_token() -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(64))

def store_refresh_token(db: Session, user_id: int, refresh_token: str) -> None:
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"is_revoked": True})
    
    expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    db_refresh_token = RefreshToken(
        user_id=user_id,
        token=refresh_token,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    db.commit()

def verify_refresh_token(db: Session, refresh_token: str) -> Optional[User]:
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
        return None
    
    user = db.query(User).filter(User.id == db_token.user_id).first()
    return user

def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
    db_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if db_token:
        db_token.is_revoked = True
        db.commit()
        return True
    return False

def revoke_all_user_tokens(db: Session, user_id: int) -> None:
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"is_revoked": True})
    db.commit()

def create_password_reset_token(db: Session, user_id: int) -> str:
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.is_used == False
    ).update({"is_used": True})
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.password_reset_expire_minutes)
    
    db_token = PasswordResetToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    
    return token

def verify_password_reset_token(db: Session, token: str) -> Optional[User]:
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.is_used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
        return None
    
    user = db.query(User).filter(User.id == db_token.user_id).first()
    return user

def use_password_reset_token(db: Session, token: str) -> bool:
    db_token = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    if db_token:
        db_token.is_used = True
        db.commit()
        return True
    return False

def verify_token(token: str, credentials_exception) -> TokenData:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data

def create_token_response(user, access_token: str, refresh_token: str) -> dict:
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
    } 