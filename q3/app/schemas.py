from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    PHARMACIST = "pharmacist"
    DELIVERY_PARTNER = "delivery_partner"

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PrescriptionStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone: str
    full_name: str
    age: Optional[int] = None
    medical_conditions: Optional[str] = None
    allergies: Optional[str] = None

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    medical_conditions: Optional[str] = None
    allergies: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    is_phone_verified: bool
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class TokenData(BaseModel):
    username: Optional[str] = None

# Medicine schemas
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class MedicineBase(BaseModel):
    name: str
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    description: Optional[str] = None
    price: float
    dosage: Optional[str] = None
    form: Optional[str] = None
    strength: Optional[str] = None
    manufacturer: Optional[str] = None
    prescription_required: bool = False
    category_id: int

class MedicineCreate(MedicineBase):
    stock_quantity: int = 0
    low_stock_threshold: int = 10

class MedicineUpdate(BaseModel):
    name: Optional[str] = None
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    dosage: Optional[str] = None
    form: Optional[str] = None
    strength: Optional[str] = None
    manufacturer: Optional[str] = None
    prescription_required: Optional[bool] = None
    category_id: Optional[int] = None
    is_available: Optional[bool] = None

class MedicineResponse(MedicineBase):
    id: int
    stock_quantity: int
    low_stock_threshold: int
    is_available: bool
    is_emergency_available: bool
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True

class MedicineSearch(BaseModel):
    q: Optional[str] = None
    category: Optional[int] = None
    prescription_required: Optional[bool] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    in_stock: Optional[bool] = True

# Prescription schemas
class PrescriptionCreate(BaseModel):
    doctor_name: str
    hospital_name: Optional[str] = None
    prescription_date: datetime

class PrescriptionResponse(BaseModel):
    id: int
    user_id: int
    doctor_name: str
    hospital_name: Optional[str] = None
    prescription_date: datetime
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    status: PrescriptionStatus
    verification_notes: Optional[str] = None
    extracted_medicines: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PrescriptionVerify(BaseModel):
    status: PrescriptionStatus
    verification_notes: Optional[str] = None
    extracted_medicines: Optional[str] = None

# Cart schemas
class CartItemCreate(BaseModel):
    medicine_id: int
    quantity: int = 1
    prescription_id: Optional[int] = None

class CartItemUpdate(BaseModel):
    quantity: int

class CartItemResponse(BaseModel):
    id: int
    medicine_id: int
    quantity: int
    prescription_id: Optional[int] = None
    medicine: MedicineResponse
    created_at: datetime

    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total_amount: float
    prescription_required_items: int

# Order schemas
class OrderCreate(BaseModel):
    delivery_address: str
    delivery_phone: str
    payment_method: str
    is_emergency: bool = False
    delivery_notes: Optional[str] = None

class OrderItemResponse(BaseModel):
    id: int
    medicine_id: int
    quantity: int
    price: float
    prescription_id: Optional[int] = None
    medicine: MedicineResponse

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    order_number: str
    total_amount: float
    delivery_fee: float
    tax_amount: float
    discount_amount: float
    status: OrderStatus
    delivery_address: str
    delivery_phone: str
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    is_emergency: bool
    payment_method: str
    payment_status: str
    tracking_number: Optional[str] = None
    delivery_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    order_items: List[OrderItemResponse]

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    delivery_notes: Optional[str] = None

# Delivery schemas
class DeliveryEstimate(BaseModel):
    estimated_time: int  # minutes
    delivery_fee: float
    is_emergency_available: bool

class DeliveryPartnerResponse(BaseModel):
    id: int
    user_id: int
    vehicle_type: str
    is_available: bool
    rating: float
    distance: Optional[float] = None  # calculated distance

    class Config:
        from_attributes = True

class EmergencyDeliveryRequest(BaseModel):
    medicine_names: List[str]
    urgent_notes: str
    delivery_address: str
    delivery_phone: str

class PharmacyResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: str
    email: Optional[str] = None
    is_active: bool
    operating_hours: Optional[str] = None
    distance: Optional[float] = None

    class Config:
        from_attributes = True

class PhoneVerification(BaseModel):
    phone: str
    verification_code: str 