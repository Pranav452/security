from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.models import User, UserRole
from app.schemas import (
    UserCreate, UserResponse, UserLogin, Token, UserUpdate, 
    PhoneVerification, TokenData
)
from app.auth import (
    get_password_hash, verify_password, create_access_token,
    create_token_response, generate_phone_verification_code,
    is_valid_phone_number, sanitize_input
)
from app.dependencies import get_current_user, get_current_active_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user with medical profile."""
    # Check if user already exists
    db_user = db.query(User).filter(
        (User.username == user_data.username) | 
        (User.email == user_data.email) |
        (User.phone == user_data.phone)
    ).first()
    
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username, email, or phone already exists"
        )
    
    # Validate phone number
    if not is_valid_phone_number(user_data.phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=sanitize_input(user_data.username),
        email=user_data.email,
        phone=user_data.phone,
        full_name=sanitize_input(user_data.full_name),
        hashed_password=hashed_password,
        role=UserRole.USER,
        age=user_data.age,
        medical_conditions=sanitize_input(user_data.medical_conditions) if user_data.medical_conditions else None,
        allergies=sanitize_input(user_data.allergies) if user_data.allergies else None
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    
    return create_token_response(db_user, access_token)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """User login endpoint."""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return create_token_response(user, access_token)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile and delivery address."""
    # Update user fields
    if user_update.full_name is not None:
        current_user.full_name = sanitize_input(user_update.full_name)
    
    if user_update.phone is not None:
        if not is_valid_phone_number(user_update.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format"
            )
        
        # Check if phone is already taken by another user
        existing_user = db.query(User).filter(
            User.phone == user_update.phone,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already in use"
            )
        
        current_user.phone = user_update.phone
        current_user.is_phone_verified = False  # Reset verification status
    
    if user_update.age is not None:
        current_user.age = user_update.age
    
    if user_update.medical_conditions is not None:
        current_user.medical_conditions = sanitize_input(user_update.medical_conditions)
    
    if user_update.allergies is not None:
        current_user.allergies = sanitize_input(user_update.allergies)
    
    if user_update.address is not None:
        current_user.address = sanitize_input(user_update.address)
    
    if user_update.city is not None:
        current_user.city = sanitize_input(user_update.city)
    
    if user_update.state is not None:
        current_user.state = sanitize_input(user_update.state)
    
    if user_update.zip_code is not None:
        current_user.zip_code = sanitize_input(user_update.zip_code)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/verify-phone")
async def verify_phone(
    verification: PhoneVerification,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify phone number for delivery."""
    # In a real implementation, this would verify against a sent SMS code
    # For demo purposes, we'll accept any 6-digit code
    if len(verification.verification_code) != 6 or not verification.verification_code.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code format"
        )
    
    # Mock verification - in production, verify against sent SMS
    if verification.verification_code == "123456":
        current_user.is_phone_verified = True
        db.commit()
        
        return {
            "message": "Phone number verified successfully",
            "is_verified": True
        }
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid verification code"
    )

@router.post("/send-verification-code")
async def send_verification_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send verification code to user's phone."""
    if not current_user.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number not set. Please update your profile first."
        )
    
    # Generate verification code
    verification_code = generate_phone_verification_code()
    
    # In a real implementation, send SMS using Twilio/AWS SNS
    # For demo purposes, we'll just return the code
    return {
        "message": f"Verification code sent to {current_user.phone}",
        "verification_code": verification_code  # Remove in production
    } 