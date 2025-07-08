from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import CartItem, User, Medicine, Prescription, PrescriptionStatus
from app.schemas import CartItemCreate, CartItemUpdate, CartItemResponse, CartResponse
from app.dependencies import get_current_user, get_verified_user
from app.auth import calculate_tax_amount

router = APIRouter(prefix="/cart", tags=["cart"])

@router.get("/", response_model=CartResponse)
async def get_user_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's cart with prescription validation."""
    cart_items = db.query(CartItem).filter(
        CartItem.user_id == current_user.id
    ).all()
    
    # Load medicine relationships and calculate totals
    total_amount = 0.0
    prescription_required_items = 0
    cart_response_items = []
    
    for item in cart_items:
        medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
        
        if not medicine:
            # Remove invalid cart items
            db.delete(item)
            continue
        
        if not medicine.is_available or medicine.stock_quantity < item.quantity:
            # Update item quantity to available stock
            if medicine.stock_quantity > 0:
                item.quantity = medicine.stock_quantity
            else:
                db.delete(item)
                continue
        
        # Calculate item total
        item_total = medicine.price * item.quantity
        total_amount += item_total
        
        # Check prescription requirement
        if medicine.prescription_required:
            prescription_required_items += 1
        
        # Create response item
        cart_response_items.append(CartItemResponse(
            id=item.id,
            medicine_id=item.medicine_id,
            quantity=item.quantity,
            prescription_id=item.prescription_id,
            medicine=medicine,
            created_at=item.created_at
        ))
    
    db.commit()
    
    return CartResponse(
        items=cart_response_items,
        total_amount=total_amount,
        prescription_required_items=prescription_required_items
    )

@router.post("/items", response_model=CartItemResponse)
async def add_item_to_cart(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add medicine to cart."""
    # Check if medicine exists
    medicine = db.query(Medicine).filter(Medicine.id == item_data.medicine_id).first()
    
    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found"
        )
    
    if not medicine.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medicine is not available"
        )
    
    # Check stock availability
    if medicine.stock_quantity < item_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {medicine.stock_quantity} units available in stock"
        )
    
    # Check prescription requirement
    if medicine.prescription_required:
        if not item_data.prescription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prescription required for this medicine"
            )
        
        # Verify prescription exists and is verified
        prescription = db.query(Prescription).filter(
            Prescription.id == item_data.prescription_id,
            Prescription.user_id == current_user.id
        ).first()
        
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found"
            )
        
        if prescription.status != PrescriptionStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prescription must be verified before adding to cart"
            )
    
    # Check if item already exists in cart
    existing_item = db.query(CartItem).filter(
        CartItem.user_id == current_user.id,
        CartItem.medicine_id == item_data.medicine_id
    ).first()
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item.quantity + item_data.quantity
        
        if new_quantity > medicine.stock_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total quantity would exceed stock. Available: {medicine.stock_quantity}"
            )
        
        existing_item.quantity = new_quantity
        if item_data.prescription_id:
            existing_item.prescription_id = item_data.prescription_id
        
        db.commit()
        db.refresh(existing_item)
        
        # Load medicine relationship
        existing_item.medicine = medicine
        
        return existing_item
    
    # Create new cart item
    cart_item = CartItem(
        user_id=current_user.id,
        medicine_id=item_data.medicine_id,
        quantity=item_data.quantity,
        prescription_id=item_data.prescription_id
    )
    
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    
    # Load medicine relationship
    cart_item.medicine = medicine
    
    return cart_item

@router.put("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int,
    item_update: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update cart item quantity."""
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    # Check medicine availability
    medicine = db.query(Medicine).filter(Medicine.id == cart_item.medicine_id).first()
    
    if not medicine or not medicine.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medicine is not available"
        )
    
    # Check stock availability
    if medicine.stock_quantity < item_update.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {medicine.stock_quantity} units available in stock"
        )
    
    # Update quantity
    cart_item.quantity = item_update.quantity
    
    db.commit()
    db.refresh(cart_item)
    
    # Load medicine relationship
    cart_item.medicine = medicine
    
    return cart_item

@router.delete("/items/{item_id}")
async def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove medicine from cart."""
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    db.delete(cart_item)
    db.commit()
    
    return {"message": "Item removed from cart"}

@router.delete("/")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear entire cart."""
    cart_items = db.query(CartItem).filter(
        CartItem.user_id == current_user.id
    ).all()
    
    for item in cart_items:
        db.delete(item)
    
    db.commit()
    
    return {"message": f"Cart cleared. {len(cart_items)} items removed."}

@router.post("/validate-prescriptions")
async def validate_prescription_medicines(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate prescription medicines in cart."""
    cart_items = db.query(CartItem).filter(
        CartItem.user_id == current_user.id
    ).all()
    
    validation_results = []
    total_issues = 0
    
    for item in cart_items:
        medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
        
        if not medicine:
            continue
        
        result = {
            "cart_item_id": item.id,
            "medicine_name": medicine.name,
            "quantity": item.quantity,
            "requires_prescription": medicine.prescription_required,
            "has_prescription": bool(item.prescription_id),
            "prescription_status": None,
            "issues": []
        }
        
        # Check prescription requirement
        if medicine.prescription_required:
            if not item.prescription_id:
                result["issues"].append("Prescription required but not provided")
                total_issues += 1
            else:
                prescription = db.query(Prescription).filter(
                    Prescription.id == item.prescription_id,
                    Prescription.user_id == current_user.id
                ).first()
                
                if not prescription:
                    result["issues"].append("Prescription not found")
                    total_issues += 1
                else:
                    result["prescription_status"] = prescription.status.value
                    
                    if prescription.status != PrescriptionStatus.VERIFIED:
                        result["issues"].append("Prescription not verified")
                        total_issues += 1
        
        # Check stock availability
        if medicine.stock_quantity < item.quantity:
            result["issues"].append(f"Only {medicine.stock_quantity} units available")
            total_issues += 1
        
        # Check medicine availability
        if not medicine.is_available:
            result["issues"].append("Medicine is not available")
            total_issues += 1
        
        validation_results.append(result)
    
    return {
        "validation_results": validation_results,
        "total_items": len(cart_items),
        "total_issues": total_issues,
        "can_proceed_to_checkout": total_issues == 0
    }

@router.get("/summary")
async def get_cart_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cart summary with pricing breakdown."""
    cart_items = db.query(CartItem).filter(
        CartItem.user_id == current_user.id
    ).all()
    
    if not cart_items:
        return {
            "total_items": 0,
            "subtotal": 0.0,
            "tax_amount": 0.0,
            "total_amount": 0.0,
            "prescription_required_items": 0,
            "out_of_stock_items": 0
        }
    
    subtotal = 0.0
    prescription_required_items = 0
    out_of_stock_items = 0
    
    for item in cart_items:
        medicine = db.query(Medicine).filter(Medicine.id == item.medicine_id).first()
        
        if not medicine:
            continue
        
        if medicine.stock_quantity < item.quantity:
            out_of_stock_items += 1
        
        if medicine.prescription_required:
            prescription_required_items += 1
        
        subtotal += medicine.price * item.quantity
    
    tax_amount = calculate_tax_amount(subtotal)
    total_amount = subtotal + tax_amount
    
    return {
        "total_items": len(cart_items),
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
        "prescription_required_items": prescription_required_items,
        "out_of_stock_items": out_of_stock_items
    } 