from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config import settings
from app.schemas import TokenData
import secrets
import string

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str, credentials_exception) -> TokenData:
    """Verify JWT token and extract token data."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data

def create_token_response(user, access_token: str) -> dict:
    """Create token response with user info."""
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role.value,
            "is_active": user.is_active,
            "is_phone_verified": user.is_phone_verified,
            "age": user.age,
            "medical_conditions": user.medical_conditions,
            "allergies": user.allergies,
            "address": user.address,
            "city": user.city,
            "state": user.state,
            "zip_code": user.zip_code,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
    }

def generate_phone_verification_code() -> str:
    """Generate 6-digit verification code."""
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def generate_order_number() -> str:
    """Generate unique order number."""
    prefix = "ORD"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"{prefix}{timestamp}{random_suffix}"

def generate_tracking_number() -> str:
    """Generate unique tracking number."""
    prefix = "TRK"
    timestamp = datetime.now().strftime("%Y%m%d")
    random_suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    return f"{prefix}{timestamp}{random_suffix}"

def calculate_delivery_fee(distance: float, is_emergency: bool = False) -> float:
    """Calculate delivery fee based on distance and emergency status."""
    base_fee = 5.0
    distance_fee = distance * 0.5  # $0.50 per km
    emergency_fee = 10.0 if is_emergency else 0.0
    return base_fee + distance_fee + emergency_fee

def calculate_tax_amount(subtotal: float) -> float:
    """Calculate tax amount (8% tax rate)."""
    return subtotal * 0.08

def is_prescription_required(medicine_names: list) -> bool:
    """Check if any medicine in the list requires prescription."""
    # In a real implementation, this would check the database
    # For now, we'll use a simple heuristic
    prescription_keywords = ['antibiotic', 'insulin', 'morphine', 'oxycodone', 'adderall']
    for name in medicine_names:
        if any(keyword in name.lower() for keyword in prescription_keywords):
            return True
    return False

def validate_medical_profile(user_data: dict) -> bool:
    """Validate medical profile data."""
    required_fields = ['age', 'medical_conditions', 'allergies']
    return all(field in user_data and user_data[field] is not None for field in required_fields)

def calculate_delivery_time(distance: float, is_emergency: bool = False) -> int:
    """Calculate estimated delivery time in minutes."""
    if is_emergency:
        return settings.emergency_delivery_time
    
    base_time = 15  # 15 minutes base time
    distance_time = distance * 2  # 2 minutes per km
    return min(int(base_time + distance_time), settings.default_delivery_time)

def format_medicine_name(name: str) -> str:
    """Format medicine name for consistency."""
    return name.strip().title()

def extract_medicine_alternatives(medicine_name: str) -> list:
    """Extract alternative medicines (mock implementation)."""
    # In a real implementation, this would use a medical database
    alternatives = {
        "Paracetamol": ["Acetaminophen", "Tylenol", "Panadol"],
        "Ibuprofen": ["Advil", "Motrin", "Nurofen"],
        "Aspirin": ["Bayer Aspirin", "Bufferin", "Ecotrin"],
        "Amoxicillin": ["Augmentin", "Amoxil", "Trimox"]
    }
    return alternatives.get(medicine_name, [])

def is_valid_phone_number(phone: str) -> bool:
    """Validate phone number format."""
    # Simple validation - in production, use proper phone validation
    import re
    pattern = r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'
    return bool(re.match(pattern, phone))

def sanitize_input(input_string: str) -> str:
    """Sanitize user input to prevent XSS attacks."""
    if not input_string:
        return ""
    
    # Remove HTML tags and potentially dangerous characters
    import re
    cleaned = re.sub(r'<[^>]+>', '', input_string)
    cleaned = re.sub(r'[<>"\';]', '', cleaned)
    return cleaned.strip()

def is_emergency_medicine(medicine_name: str) -> bool:
    """Check if medicine is available for emergency delivery."""
    emergency_medicines = [
        'insulin', 'epinephrine', 'albuterol', 'nitroglycerin', 
        'aspirin', 'ibuprofen', 'paracetamol', 'acetaminophen'
    ]
    return any(med in medicine_name.lower() for med in emergency_medicines) 