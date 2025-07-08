from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    PHARMACIST = "pharmacist"
    DELIVERY_PARTNER = "delivery_partner"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PrescriptionStatus(enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    is_phone_verified = Column(Boolean, default=False)
    
    # Medical profile
    age = Column(Integer)
    medical_conditions = Column(Text)
    allergies = Column(Text)
    
    # Delivery address
    address = Column(Text)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prescriptions = relationship("Prescription", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")
    orders = relationship("Order", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    medicines = relationship("Medicine", back_populates="category")

class Medicine(Base):
    __tablename__ = "medicines"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    generic_name = Column(String)
    brand_name = Column(String)
    description = Column(Text)
    price = Column(Float)
    stock_quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10)
    
    # Medical information
    dosage = Column(String)
    form = Column(String)  # tablet, capsule, syrup, etc.
    strength = Column(String)
    manufacturer = Column(String)
    expiry_date = Column(DateTime)
    
    # Prescription requirements
    prescription_required = Column(Boolean, default=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    # Availability
    is_available = Column(Boolean, default=True)
    is_emergency_available = Column(Boolean, default=False)
    
    # SEO
    search_keywords = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("Category", back_populates="medicines")
    cart_items = relationship("CartItem", back_populates="medicine")
    order_items = relationship("OrderItem", back_populates="medicine")

class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    doctor_name = Column(String)
    hospital_name = Column(String)
    prescription_date = Column(DateTime)
    
    # File information
    file_path = Column(String)
    file_name = Column(String)
    
    # Verification
    status = Column(Enum(PrescriptionStatus), default=PrescriptionStatus.PENDING)
    verified_by = Column(Integer, ForeignKey("users.id"))
    verification_notes = Column(Text)
    
    # Extracted medicines
    extracted_medicines = Column(Text)  # JSON string of medicine names
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="prescriptions", foreign_keys=[user_id])

class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    medicine_id = Column(Integer, ForeignKey("medicines.id"))
    quantity = Column(Integer, default=1)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="cart_items")
    medicine = relationship("Medicine", back_populates="cart_items")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_number = Column(String, unique=True, index=True)
    
    # Order details
    total_amount = Column(Float)
    delivery_fee = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    
    # Status
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    
    # Delivery information
    delivery_address = Column(Text)
    delivery_phone = Column(String)
    estimated_delivery_time = Column(DateTime)
    actual_delivery_time = Column(DateTime)
    delivery_partner_id = Column(Integer, ForeignKey("users.id"))
    
    # Emergency order
    is_emergency = Column(Boolean, default=False)
    
    # Payment
    payment_method = Column(String)
    payment_status = Column(String, default="pending")
    
    # Tracking
    tracking_number = Column(String)
    delivery_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="orders", foreign_keys=[user_id])
    order_items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    medicine_id = Column(Integer, ForeignKey("medicines.id"))
    quantity = Column(Integer)
    price = Column(Float)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    medicine = relationship("Medicine", back_populates="order_items")

class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    vehicle_type = Column(String)
    license_number = Column(String)
    is_available = Column(Boolean, default=True)
    current_latitude = Column(Float)
    current_longitude = Column(Float)
    rating = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Pharmacy(Base):
    __tablename__ = "pharmacies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    address = Column(Text)
    phone = Column(String)
    email = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    is_active = Column(Boolean, default=True)
    operating_hours = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow) 