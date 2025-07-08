from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.database import get_db
from app.models import (
    Order, OrderItem, CartItem, User, Medicine, 
    OrderStatus, DeliveryPartner, Pharmacy
)
from app.schemas import (
    OrderCreate, OrderResponse, OrderStatusUpdate, 
    DeliveryEstimate, DeliveryPartnerResponse, 
    EmergencyDeliveryRequest, PharmacyResponse
)
from app.dependencies import (
    get_current_user, get_user_with_address, 
    get_delivery_partner, get_pharmacist_user
)
from app.auth import (
    generate_order_number, generate_tracking_number,
    calculate_delivery_fee, calculate_tax_amount, 
    calculate_delivery_time, is_emergency_medicine
)

router = APIRouter(prefix="/orders", tags=["orders"])
delivery_router = APIRouter(prefix="/delivery", tags=["delivery"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_user_with_address),
    db: Session = Depends(get_db)
):
    """Create order from cart with delivery details."""
    # Get cart items
    cart_items = db.query(CartItem).filter(
        CartItem.user_id == current_user.id
    ).all()
    
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )
    
    # Calculate totals
    subtotal = 0.0
    order_items_data = []
    
    for cart_item in cart_items:
        medicine = db.query(Medicine).filter(Medicine.id == cart_item.medicine_id).first()
        
        if not medicine or not medicine.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Medicine {medicine.name if medicine else 'unknown'} is not available"
            )
        
        if medicine.stock_quantity < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {medicine.name}. Available: {medicine.stock_quantity}"
            )
        
        item_total = medicine.price * cart_item.quantity
        subtotal += item_total
        
        order_items_data.append({
            "medicine_id": cart_item.medicine_id,
            "quantity": cart_item.quantity,
            "price": medicine.price,
            "prescription_id": cart_item.prescription_id
        })
    
    # Calculate fees
    delivery_distance = 5.0  # Mock distance - in production, calculate from user location
    delivery_fee = calculate_delivery_fee(delivery_distance, order_data.is_emergency)
    tax_amount = calculate_tax_amount(subtotal)
    total_amount = subtotal + delivery_fee + tax_amount
    
    # Calculate delivery time
    estimated_delivery_minutes = calculate_delivery_time(delivery_distance, order_data.is_emergency)
    estimated_delivery_time = datetime.utcnow() + timedelta(minutes=estimated_delivery_minutes)
    
    # Create order
    order = Order(
        user_id=current_user.id,
        order_number=generate_order_number(),
        total_amount=total_amount,
        delivery_fee=delivery_fee,
        tax_amount=tax_amount,
        status=OrderStatus.PENDING,
        delivery_address=order_data.delivery_address,
        delivery_phone=order_data.delivery_phone,
        estimated_delivery_time=estimated_delivery_time,
        is_emergency=order_data.is_emergency,
        payment_method=order_data.payment_method,
        tracking_number=generate_tracking_number(),
        delivery_notes=order_data.delivery_notes
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Create order items and update stock
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=order.id,
            medicine_id=item_data["medicine_id"],
            quantity=item_data["quantity"],
            price=item_data["price"],
            prescription_id=item_data["prescription_id"]
        )
        db.add(order_item)
        
        # Update medicine stock
        medicine = db.query(Medicine).filter(Medicine.id == item_data["medicine_id"]).first()
        medicine.stock_quantity -= item_data["quantity"]
        
        # Auto-disable if out of stock
        if medicine.stock_quantity <= 0:
            medicine.is_available = False
    
    # Clear cart
    for cart_item in cart_items:
        db.delete(cart_item)
    
    db.commit()
    
    # Load order items with medicine details
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    for item in order_items:
        item.medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
    
    order.order_items = order_items
    
    return order

@router.get("/", response_model=List[OrderResponse])
async def get_user_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's orders with delivery status."""
    orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(Order.created_at.desc()).all()
    
    # Load order items with medicine details
    for order in orders:
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        for item in order_items:
            item.medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
        order.order_items = order_items
    
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific order details."""
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns this order or is authorized to view it
    if (order.user_id != current_user.id and 
        current_user.role.value not in ['pharmacist', 'admin', 'delivery_partner']):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order"
        )
    
    # Load order items with medicine details
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    for item in order_items:
        item.medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
    
    order.order_items = order_items
    
    return order

@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(get_pharmacist_user),
    db: Session = Depends(get_db)
):
    """Update order status (pharmacy/delivery partner)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update status
    order.status = status_update.status
    
    if status_update.delivery_notes:
        order.delivery_notes = status_update.delivery_notes
    
    # Set delivery time if delivered
    if status_update.status == OrderStatus.DELIVERED:
        order.actual_delivery_time = datetime.utcnow()
    
    # Assign delivery partner if status is out for delivery
    if status_update.status == OrderStatus.OUT_FOR_DELIVERY:
        if current_user.role.value == "delivery_partner":
            order.delivery_partner_id = current_user.id
    
    db.commit()
    db.refresh(order)
    
    # Load order items
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    for item in order_items:
        item.medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
    
    order.order_items = order_items
    
    return order

@router.get("/{order_id}/track")
async def track_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Real-time order tracking."""
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns this order
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to track this order"
        )
    
    # Calculate progress percentage
    status_progress = {
        OrderStatus.PENDING: 10,
        OrderStatus.CONFIRMED: 25,
        OrderStatus.PROCESSING: 50,
        OrderStatus.READY: 75,
        OrderStatus.OUT_FOR_DELIVERY: 90,
        OrderStatus.DELIVERED: 100,
        OrderStatus.CANCELLED: 0
    }
    
    # Get delivery partner info if assigned
    delivery_partner = None
    if order.delivery_partner_id:
        partner_user = db.query(User).filter(User.id == order.delivery_partner_id).first()
        if partner_user:
            delivery_partner = {
                "name": partner_user.full_name,
                "phone": partner_user.phone
            }
    
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status.value,
        "progress_percentage": status_progress.get(order.status, 0),
        "tracking_number": order.tracking_number,
        "estimated_delivery_time": order.estimated_delivery_time,
        "actual_delivery_time": order.actual_delivery_time,
        "delivery_partner": delivery_partner,
        "delivery_notes": order.delivery_notes,
        "is_emergency": order.is_emergency
    }

@router.post("/{order_id}/delivery-proof")
async def upload_delivery_proof(
    order_id: int,
    current_user: User = Depends(get_delivery_partner),
    db: Session = Depends(get_db)
):
    """Upload delivery confirmation (delivery partner only)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if delivery partner is assigned to this order
    if order.delivery_partner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this order"
        )
    
    # Update order status to delivered
    order.status = OrderStatus.DELIVERED
    order.actual_delivery_time = datetime.utcnow()
    order.delivery_notes = "Delivery confirmed"
    
    db.commit()
    
    return {
        "message": "Delivery proof uploaded successfully",
        "order_id": order.id,
        "delivered_at": order.actual_delivery_time
    }

# Delivery endpoints
@delivery_router.get("/estimate", response_model=DeliveryEstimate)
async def get_delivery_estimate(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get delivery time estimate."""
    # Mock distance calculation - in production, use user's location
    distance = 5.0
    
    # Check if user has emergency medicines in cart
    cart_items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    has_emergency_medicines = False
    
    for item in cart_items:
        medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
        if medicine and is_emergency_medicine(medicine.name):
            has_emergency_medicines = True
            break
    
    regular_time = calculate_delivery_time(distance, False)
    emergency_time = calculate_delivery_time(distance, True)
    
    return DeliveryEstimate(
        estimated_time=regular_time,
        delivery_fee=calculate_delivery_fee(distance, False),
        is_emergency_available=has_emergency_medicines
    )

@delivery_router.get("/partners", response_model=List[DeliveryPartnerResponse])
async def get_delivery_partners(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available delivery partners."""
    partners = db.query(DeliveryPartner).filter(
        DeliveryPartner.is_available == True
    ).limit(5).all()
    
    partner_responses = []
    for partner in partners:
        user = db.query(User).filter(User.id == partner.user_id).first()
        if user:
            partner_responses.append(DeliveryPartnerResponse(
                id=partner.id,
                user_id=partner.user_id,
                vehicle_type=partner.vehicle_type,
                is_available=partner.is_available,
                rating=partner.rating,
                distance=2.5  # Mock distance
            ))
    
    return partner_responses

@delivery_router.post("/emergency")
async def create_emergency_delivery(
    emergency_request: EmergencyDeliveryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create emergency medicine delivery request."""
    # Check if medicines are available for emergency delivery
    available_medicines = []
    unavailable_medicines = []
    
    for medicine_name in emergency_request.medicine_names:
        medicine = db.query(Medicine).filter(
            Medicine.name.ilike(f"%{medicine_name}%")
        ).first()
        
        if medicine and medicine.is_available and medicine.stock_quantity > 0:
            if is_emergency_medicine(medicine.name):
                available_medicines.append(medicine)
            else:
                unavailable_medicines.append(medicine_name)
        else:
            unavailable_medicines.append(medicine_name)
    
    if not available_medicines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No emergency medicines available"
        )
    
    # Create emergency order
    subtotal = sum(medicine.price for medicine in available_medicines)
    delivery_fee = calculate_delivery_fee(5.0, True)  # Emergency delivery fee
    tax_amount = calculate_tax_amount(subtotal)
    total_amount = subtotal + delivery_fee + tax_amount
    
    order = Order(
        user_id=current_user.id,
        order_number=generate_order_number(),
        total_amount=total_amount,
        delivery_fee=delivery_fee,
        tax_amount=tax_amount,
        status=OrderStatus.CONFIRMED,
        delivery_address=emergency_request.delivery_address,
        delivery_phone=emergency_request.delivery_phone,
        estimated_delivery_time=datetime.utcnow() + timedelta(minutes=10),
        is_emergency=True,
        payment_method="cash_on_delivery",
        tracking_number=generate_tracking_number(),
        delivery_notes=f"EMERGENCY: {emergency_request.urgent_notes}"
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Create order items
    for medicine in available_medicines:
        order_item = OrderItem(
            order_id=order.id,
            medicine_id=medicine.id,
            quantity=1,
            price=medicine.price
        )
        db.add(order_item)
    
    db.commit()
    
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "estimated_delivery_time": order.estimated_delivery_time,
        "available_medicines": [m.name for m in available_medicines],
        "unavailable_medicines": unavailable_medicines,
        "total_amount": total_amount,
        "tracking_number": order.tracking_number
    }

@delivery_router.get("/nearby-pharmacies", response_model=List[PharmacyResponse])
async def get_nearby_pharmacies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Find nearby pharmacies with stock."""
    pharmacies = db.query(Pharmacy).filter(
        Pharmacy.is_active == True
    ).limit(5).all()
    
    pharmacy_responses = []
    for pharmacy in pharmacies:
        pharmacy_responses.append(PharmacyResponse(
            id=pharmacy.id,
            name=pharmacy.name,
            address=pharmacy.address,
            phone=pharmacy.phone,
            email=pharmacy.email,
            is_active=pharmacy.is_active,
            operating_hours=pharmacy.operating_hours,
            distance=2.5  # Mock distance
        ))
    
    return pharmacy_responses 