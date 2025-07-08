from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
from datetime import datetime
from app.database import get_db
from app.models import Prescription, User, Medicine, PrescriptionStatus
from app.schemas import PrescriptionCreate, PrescriptionResponse, PrescriptionVerify
from app.dependencies import get_current_user, get_pharmacist_user
from app.config import settings
from app.auth import sanitize_input

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)

@router.post("/upload", response_model=PrescriptionResponse)
async def upload_prescription(
    doctor_name: str = Form(...),
    hospital_name: Optional[str] = Form(None),
    prescription_date: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload prescription image."""
    # Validate file type
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPG, PNG, and PDF files are allowed."
        )
    
    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB."
        )
    
    # Parse prescription date
    try:
        prescription_date_obj = datetime.strptime(prescription_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD."
        )
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"prescription_{current_user.id}_{timestamp}{file_extension}"
    file_path = os.path.join(settings.upload_dir, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        )
    
    # Create prescription record
    db_prescription = Prescription(
        user_id=current_user.id,
        doctor_name=sanitize_input(doctor_name),
        hospital_name=sanitize_input(hospital_name) if hospital_name else None,
        prescription_date=prescription_date_obj,
        file_path=file_path,
        file_name=file.filename,
        status=PrescriptionStatus.PENDING
    )
    
    db.add(db_prescription)
    db.commit()
    db.refresh(db_prescription)
    
    return db_prescription

@router.get("/", response_model=List[PrescriptionResponse])
async def get_user_prescriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's prescriptions."""
    prescriptions = db.query(Prescription).filter(
        Prescription.user_id == current_user.id
    ).order_by(Prescription.created_at.desc()).all()
    
    return prescriptions

@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific prescription details."""
    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id
    ).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    # Check if user owns this prescription or is a pharmacist
    if (prescription.user_id != current_user.id and 
        current_user.role.value not in ['pharmacist', 'admin']):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this prescription"
        )
    
    return prescription

@router.put("/{prescription_id}/verify", response_model=PrescriptionResponse)
async def verify_prescription(
    prescription_id: int,
    verification_data: PrescriptionVerify,
    current_user: User = Depends(get_pharmacist_user),
    db: Session = Depends(get_db)
):
    """Verify prescription (pharmacist only)."""
    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id
    ).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    # Update prescription status
    prescription.status = verification_data.status
    prescription.verified_by = current_user.id
    prescription.verification_notes = sanitize_input(verification_data.verification_notes) if verification_data.verification_notes else None
    
    if verification_data.extracted_medicines:
        prescription.extracted_medicines = verification_data.extracted_medicines
    
    db.commit()
    db.refresh(prescription)
    
    return prescription

@router.get("/{prescription_id}/medicines")
async def get_prescription_medicines(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get medicines from prescription."""
    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id
    ).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    # Check if user owns this prescription or is a pharmacist
    if (prescription.user_id != current_user.id and 
        current_user.role.value not in ['pharmacist', 'admin']):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this prescription"
        )
    
    if not prescription.extracted_medicines:
        return {
            "prescription_id": prescription_id,
            "medicines": [],
            "status": prescription.status.value,
            "message": "No medicines extracted yet. Please wait for pharmacist verification."
        }
    
    try:
        # Parse extracted medicines JSON
        medicine_names = json.loads(prescription.extracted_medicines)
        
        # Find medicines in database
        medicines = []
        for medicine_name in medicine_names:
            # Try to find exact match first
            medicine = db.query(Medicine).filter(
                Medicine.name.ilike(f"%{medicine_name}%")
            ).first()
            
            if medicine:
                medicines.append({
                    "id": medicine.id,
                    "name": medicine.name,
                    "generic_name": medicine.generic_name,
                    "brand_name": medicine.brand_name,
                    "price": medicine.price,
                    "stock_quantity": medicine.stock_quantity,
                    "prescription_required": medicine.prescription_required,
                    "is_available": medicine.is_available
                })
            else:
                # Medicine not found in database
                medicines.append({
                    "id": None,
                    "name": medicine_name,
                    "generic_name": None,
                    "brand_name": None,
                    "price": None,
                    "stock_quantity": 0,
                    "prescription_required": True,
                    "is_available": False,
                    "error": "Medicine not found in our database"
                })
        
        return {
            "prescription_id": prescription_id,
            "medicines": medicines,
            "status": prescription.status.value,
            "total_medicines": len(medicines),
            "available_medicines": len([m for m in medicines if m.get("is_available", False)])
        }
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid medicine data format"
        )

@router.post("/{prescription_id}/extract-medicines")
async def extract_medicines_from_prescription(
    prescription_id: int,
    current_user: User = Depends(get_pharmacist_user),
    db: Session = Depends(get_db)
):
    """Extract medicines from prescription (pharmacist only)."""
    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id
    ).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    # Mock OCR/AI extraction - in production, use actual OCR service
    # This would typically involve image processing and AI/ML to extract medicine names
    mock_extracted_medicines = [
        "Paracetamol 500mg",
        "Ibuprofen 400mg",
        "Amoxicillin 250mg"
    ]
    
    # Save extracted medicines
    prescription.extracted_medicines = json.dumps(mock_extracted_medicines)
    prescription.status = PrescriptionStatus.VERIFIED
    prescription.verified_by = current_user.id
    prescription.verification_notes = "Medicines extracted automatically"
    
    db.commit()
    db.refresh(prescription)
    
    return {
        "prescription_id": prescription_id,
        "extracted_medicines": mock_extracted_medicines,
        "status": prescription.status.value,
        "message": "Medicines extracted successfully"
    }

@router.get("/pending/verify")
async def get_pending_prescriptions(
    current_user: User = Depends(get_pharmacist_user),
    db: Session = Depends(get_db)
):
    """Get pending prescriptions for verification (pharmacist only)."""
    pending_prescriptions = db.query(Prescription).filter(
        Prescription.status == PrescriptionStatus.PENDING
    ).order_by(Prescription.created_at.asc()).all()
    
    return {
        "pending_prescriptions": pending_prescriptions,
        "total_pending": len(pending_prescriptions)
    }

@router.delete("/{prescription_id}")
async def delete_prescription(
    prescription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete prescription."""
    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id
    ).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    # Check if user owns this prescription
    if prescription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this prescription"
        )
    
    # Delete file from storage
    try:
        if prescription.file_path and os.path.exists(prescription.file_path):
            os.remove(prescription.file_path)
    except Exception:
        pass  # File deletion failed, but continue with database deletion
    
    # Delete from database
    db.delete(prescription)
    db.commit()
    
    return {"message": "Prescription deleted successfully"} 