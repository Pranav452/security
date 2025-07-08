from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from app.database import get_db
from app.models import Medicine, Category, User
from app.schemas import (
    MedicineCreate, MedicineUpdate, MedicineResponse, MedicineSearch,
    CategoryCreate, CategoryResponse
)
from app.dependencies import get_current_user, get_admin_user, get_pharmacist_user
from app.auth import extract_medicine_alternatives, format_medicine_name

router = APIRouter(prefix="/medicines", tags=["medicines"])
categories_router = APIRouter(prefix="/categories", tags=["categories"])

# Medicine endpoints
@router.get("/", response_model=List[MedicineResponse])
async def get_medicines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all medicines with availability and pricing."""
    medicines = db.query(Medicine).filter(
        Medicine.is_available == True
    ).offset(skip).limit(limit).all()
    
    # Load category relationships
    for medicine in medicines:
        medicine.category = db.query(Category).filter(Category.id == medicine.category_id).first()
    
    return medicines

@router.post("/", response_model=MedicineResponse)
async def create_medicine(
    medicine_data: MedicineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Add new medicine (admin only)."""
    # Check if category exists
    category = db.query(Category).filter(Category.id == medicine_data.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check for duplicate medicine names
    existing_medicine = db.query(Medicine).filter(
        or_(
            Medicine.name == medicine_data.name,
            Medicine.brand_name == medicine_data.brand_name
        )
    ).first()
    
    if existing_medicine:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medicine with this name already exists"
        )
    
    # Create medicine
    db_medicine = Medicine(
        name=format_medicine_name(medicine_data.name),
        generic_name=medicine_data.generic_name,
        brand_name=medicine_data.brand_name,
        description=medicine_data.description,
        price=medicine_data.price,
        dosage=medicine_data.dosage,
        form=medicine_data.form,
        strength=medicine_data.strength,
        manufacturer=medicine_data.manufacturer,
        prescription_required=medicine_data.prescription_required,
        category_id=medicine_data.category_id,
        stock_quantity=medicine_data.stock_quantity,
        low_stock_threshold=medicine_data.low_stock_threshold,
        search_keywords=f"{medicine_data.name} {medicine_data.generic_name or ''} {medicine_data.brand_name or ''}"
    )
    
    db.add(db_medicine)
    db.commit()
    db.refresh(db_medicine)
    
    # Load category relationship
    db_medicine.category = category
    
    return db_medicine

@router.put("/{medicine_id}", response_model=MedicineResponse)
async def update_medicine(
    medicine_id: int,
    medicine_update: MedicineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Update medicine details (admin only)."""
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    
    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found"
        )
    
    # Update fields
    if medicine_update.name is not None:
        medicine.name = format_medicine_name(medicine_update.name)
    
    if medicine_update.generic_name is not None:
        medicine.generic_name = medicine_update.generic_name
    
    if medicine_update.brand_name is not None:
        medicine.brand_name = medicine_update.brand_name
    
    if medicine_update.description is not None:
        medicine.description = medicine_update.description
    
    if medicine_update.price is not None:
        medicine.price = medicine_update.price
    
    if medicine_update.dosage is not None:
        medicine.dosage = medicine_update.dosage
    
    if medicine_update.form is not None:
        medicine.form = medicine_update.form
    
    if medicine_update.strength is not None:
        medicine.strength = medicine_update.strength
    
    if medicine_update.manufacturer is not None:
        medicine.manufacturer = medicine_update.manufacturer
    
    if medicine_update.prescription_required is not None:
        medicine.prescription_required = medicine_update.prescription_required
    
    if medicine_update.category_id is not None:
        # Check if category exists
        category = db.query(Category).filter(Category.id == medicine_update.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        medicine.category_id = medicine_update.category_id
    
    if medicine_update.is_available is not None:
        medicine.is_available = medicine_update.is_available
    
    # Update search keywords
    medicine.search_keywords = f"{medicine.name} {medicine.generic_name or ''} {medicine.brand_name or ''}"
    
    db.commit()
    db.refresh(medicine)
    
    # Load category relationship
    medicine.category = db.query(Category).filter(Category.id == medicine.category_id).first()
    
    return medicine

@router.delete("/{medicine_id}")
async def delete_medicine(
    medicine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Remove medicine (admin only)."""
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    
    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found"
        )
    
    # Soft delete - just mark as unavailable
    medicine.is_available = False
    db.commit()
    
    return {"message": "Medicine removed successfully"}

@router.get("/search", response_model=List[MedicineResponse])
async def search_medicines(
    q: Optional[str] = Query(None, description="Search term"),
    category: Optional[int] = Query(None, description="Category ID"),
    prescription_required: Optional[bool] = Query(None, description="Prescription required filter"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    in_stock: Optional[bool] = Query(True, description="Only in-stock medicines"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Search medicines with filters."""
    query = db.query(Medicine).filter(Medicine.is_available == True)
    
    if q:
        search_term = f"%{q.lower()}%"
        query = query.filter(
            or_(
                Medicine.name.ilike(search_term),
                Medicine.generic_name.ilike(search_term),
                Medicine.brand_name.ilike(search_term),
                Medicine.description.ilike(search_term),
                Medicine.search_keywords.ilike(search_term)
            )
        )
    
    if category:
        query = query.filter(Medicine.category_id == category)
    
    if prescription_required is not None:
        query = query.filter(Medicine.prescription_required == prescription_required)
    
    if min_price is not None:
        query = query.filter(Medicine.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Medicine.price <= max_price)
    
    if in_stock:
        query = query.filter(Medicine.stock_quantity > 0)
    
    medicines = query.offset(skip).limit(limit).all()
    
    # Load category relationships
    for medicine in medicines:
        medicine.category = db.query(Category).filter(Category.id == medicine.category_id).first()
    
    return medicines

@router.get("/{medicine_id}/alternatives", response_model=List[MedicineResponse])
async def get_medicine_alternatives(
    medicine_id: int,
    db: Session = Depends(get_db)
):
    """Get alternative medicines for the same condition."""
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    
    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found"
        )
    
    # Get alternatives based on generic name or category
    alternatives = []
    
    # First try to find medicines with same generic name
    if medicine.generic_name:
        alternatives = db.query(Medicine).filter(
            and_(
                Medicine.generic_name == medicine.generic_name,
                Medicine.id != medicine_id,
                Medicine.is_available == True
            )
        ).all()
    
    # If no alternatives found, try same category
    if not alternatives:
        alternatives = db.query(Medicine).filter(
            and_(
                Medicine.category_id == medicine.category_id,
                Medicine.id != medicine_id,
                Medicine.is_available == True
            )
        ).limit(5).all()
    
    # Load category relationships
    for alternative in alternatives:
        alternative.category = db.query(Category).filter(Category.id == alternative.category_id).first()
    
    return alternatives

@router.patch("/{medicine_id}/stock")
async def update_medicine_stock(
    medicine_id: int,
    stock_quantity: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_pharmacist_user)
):
    """Update medicine stock levels (pharmacist only)."""
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    
    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found"
        )
    
    old_stock = medicine.stock_quantity
    medicine.stock_quantity = stock_quantity
    
    # Auto-disable if out of stock
    if stock_quantity == 0:
        medicine.is_available = False
    elif stock_quantity > 0 and not medicine.is_available:
        medicine.is_available = True
    
    db.commit()
    
    return {
        "message": "Stock updated successfully",
        "medicine_id": medicine_id,
        "old_stock": old_stock,
        "new_stock": stock_quantity,
        "is_available": medicine.is_available
    }

# Category endpoints
@categories_router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all medicine categories."""
    categories = db.query(Category).offset(skip).limit(limit).all()
    return categories

@categories_router.post("/", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Create new category (admin only)."""
    # Check for duplicate category names
    existing_category = db.query(Category).filter(Category.name == category_data.name).first()
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    db_category = Category(
        name=category_data.name,
        description=category_data.description
    )
    
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    return db_category

@categories_router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Update category (admin only)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check for duplicate names (excluding current category)
    existing_category = db.query(Category).filter(
        and_(
            Category.name == category_data.name,
            Category.id != category_id
        )
    ).first()
    
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    category.name = category_data.name
    category.description = category_data.description
    
    db.commit()
    db.refresh(category)
    
    return category

@categories_router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Delete category (admin only)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if category has medicines
    medicines_count = db.query(Medicine).filter(Medicine.category_id == category_id).count()
    if medicines_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category with {medicines_count} medicines. Please reassign medicines first."
        )
    
    db.delete(category)
    db.commit()
    
    return {"message": "Category deleted successfully"} 