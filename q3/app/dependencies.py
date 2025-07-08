from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.auth import verify_token
from app.schemas import TokenData

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(credentials.credentials, credentials_exception)
    user = db.query(User).filter(User.username == token_data.username).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user with admin privileges."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def get_pharmacist_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user with pharmacist privileges."""
    if current_user.role not in [UserRole.PHARMACIST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pharmacist privileges required"
        )
    return current_user

def get_delivery_partner(current_user: User = Depends(get_current_user)) -> User:
    """Get current user with delivery partner privileges."""
    if current_user.role not in [UserRole.DELIVERY_PARTNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Delivery partner privileges required"
        )
    return current_user

def get_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user with verified phone number."""
    if not current_user.is_phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone verification required for this operation"
        )
    return current_user

def get_user_with_address(current_user: User = Depends(get_current_user)) -> User:
    """Get current user with delivery address."""
    if not current_user.address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery address required. Please update your profile."
        )
    return current_user 