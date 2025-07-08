from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.models import User
from app.schemas import (
    UserCreate, UserLogin, TokenResponse, UserResponse, 
    RefreshTokenRequest, PasswordResetRequest, PasswordResetConfirm, MessageResponse
)
from app.auth import (
    get_password_hash, verify_password, create_access_token, create_token_response,
    create_refresh_token, store_refresh_token, verify_refresh_token, 
    revoke_refresh_token, revoke_all_user_tokens, create_password_reset_token,
    verify_password_reset_token, use_password_reset_token
)
from app.dependencies import get_current_active_user, security_middleware
from app.config import settings
from app.rate_limiting import (
    login_rate_limit, registration_rate_limit, 
    password_reset_rate_limit, check_rate_limit
)
from app.security import sanitize_string

router = APIRouter()

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@registration_rate_limit
async def register(
    user: UserCreate, 
    request: Request,
    db: Session = Depends(get_db),
    security: object = Depends(security_middleware)
):
    user.username = sanitize_string(user.username)
    user.email = sanitize_string(user.email)
    
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": db_user.username, "role": db_user.role.value},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token()
    store_refresh_token(db, db_user.id, refresh_token)
    
    return create_token_response(db_user, access_token, refresh_token)

@router.post("/login", response_model=TokenResponse)
@login_rate_limit
async def login(
    user_credentials: UserLogin, 
    request: Request,
    db: Session = Depends(get_db),
    security: object = Depends(security_middleware)
):
    user_credentials.username = sanitize_string(user_credentials.username)
    
    user = db.query(User).filter(User.username == user_credentials.username).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token()
    store_refresh_token(db, user.id, refresh_token)
    
    return create_token_response(user, access_token, refresh_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
    security: object = Depends(security_middleware)
):
    if not check_rate_limit(request, "refresh", 10, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"}
        )
    
    user = verify_refresh_token(db, refresh_request.refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    new_refresh_token = create_refresh_token()
    store_refresh_token(db, user.id, new_refresh_token)
    
    return create_token_response(user, access_token, new_refresh_token)

@router.post("/logout", response_model=MessageResponse)
async def logout(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    revoke_refresh_token(db, refresh_request.refresh_token)
    return MessageResponse(message="Successfully logged out")

@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    revoke_all_user_tokens(db, current_user.id)
    return MessageResponse(message="Successfully logged out from all devices")

@router.post("/forgot-password", response_model=MessageResponse)
@password_reset_rate_limit
async def forgot_password(
    reset_request: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    security: object = Depends(security_middleware)
):
    reset_request.email = sanitize_string(reset_request.email)
    
    user = db.query(User).filter(User.email == reset_request.email).first()
    
    if user:
        token = create_password_reset_token(db, user.id)
        print(f"Password reset token for {user.email}: {token}")
    
    return MessageResponse(message="If the email exists, a password reset link has been sent")

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    reset_confirm: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
    security: object = Depends(security_middleware)
):
    if not check_rate_limit(request, "reset_password", 3, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"}
        )
    
    user = verify_password_reset_token(db, reset_confirm.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )
    
    hashed_password = get_password_hash(reset_confirm.new_password)
    user.hashed_password = hashed_password
    
    use_password_reset_token(db, reset_confirm.token)
    revoke_all_user_tokens(db, user.id)
    
    db.commit()
    
    return MessageResponse(message="Password successfully reset")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    return current_user 