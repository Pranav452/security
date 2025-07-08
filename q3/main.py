from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import create_tables, get_db
from app.config import settings
from app.routers import auth, medicines, prescriptions, cart, orders
from app.routers.medicines import categories_router
from app.routers.orders import delivery_router
from app.models import User, Category, Medicine
from app.dependencies import get_current_user
import os

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="A comprehensive quick commerce medicine delivery platform with 10-30 minute delivery promise",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router)
app.include_router(medicines.router)
app.include_router(categories_router)
app.include_router(prescriptions.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(delivery_router)

# Create database tables on startup
@app.on_event("startup")
def startup_event():
    create_tables()
    # Create sample data if needed
    create_sample_data()

def create_sample_data():
    """Create sample data for demo purposes."""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import Category, Medicine, Pharmacy, UserRole, User
    from app.auth import get_password_hash
    
    db = SessionLocal()
    
    try:
        # Check if categories exist
        if not db.query(Category).first():
            # Create categories
            categories = [
                Category(name="Pain Relief", description="Medicines for pain management"),
                Category(name="Antibiotics", description="Prescription antibiotics"),
                Category(name="Vitamins", description="Vitamins and supplements"),
                Category(name="First Aid", description="Emergency and first aid medicines"),
                Category(name="Cold & Flu", description="Cold and flu treatments"),
                Category(name="Diabetes", description="Diabetes management medicines"),
            ]
            
            for category in categories:
                db.add(category)
            
            db.commit()
            
            # Create medicines
            medicines = [
                Medicine(name="Paracetamol", generic_name="Acetaminophen", brand_name="Tylenol", 
                        description="Pain reliever and fever reducer", price=5.99, stock_quantity=100,
                        dosage="500mg", form="Tablet", prescription_required=False, category_id=1,
                        is_emergency_available=True),
                Medicine(name="Ibuprofen", generic_name="Ibuprofen", brand_name="Advil",
                        description="Anti-inflammatory pain reliever", price=7.99, stock_quantity=80,
                        dosage="400mg", form="Tablet", prescription_required=False, category_id=1,
                        is_emergency_available=True),
                Medicine(name="Amoxicillin", generic_name="Amoxicillin", brand_name="Amoxil",
                        description="Antibiotic for bacterial infections", price=15.99, stock_quantity=50,
                        dosage="250mg", form="Capsule", prescription_required=True, category_id=2),
                Medicine(name="Vitamin D3", generic_name="Cholecalciferol", brand_name="D3-Max",
                        description="Vitamin D supplement", price=12.99, stock_quantity=120,
                        dosage="1000 IU", form="Tablet", prescription_required=False, category_id=3),
                Medicine(name="Aspirin", generic_name="Acetylsalicylic acid", brand_name="Bayer",
                        description="Pain reliever and blood thinner", price=4.99, stock_quantity=90,
                        dosage="325mg", form="Tablet", prescription_required=False, category_id=4,
                        is_emergency_available=True),
                Medicine(name="Insulin", generic_name="Human insulin", brand_name="Humalog",
                        description="Diabetes medication", price=89.99, stock_quantity=25,
                        dosage="100 units/mL", form="Injection", prescription_required=True, category_id=6,
                        is_emergency_available=True),
            ]
            
            for medicine in medicines:
                db.add(medicine)
            
            db.commit()
        
        # Create admin user if doesn't exist
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@quickmed.com",
                phone="+1-555-0100",
                full_name="Admin User",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                is_active=True,
                is_phone_verified=True,
                address="123 Admin St",
                city="Admin City",
                state="Admin State",
                zip_code="12345"
            )
            db.add(admin_user)
        
        # Create pharmacist user
        pharmacist_user = db.query(User).filter(User.username == "pharmacist").first()
        if not pharmacist_user:
            pharmacist_user = User(
                username="pharmacist",
                email="pharmacist@quickmed.com",
                phone="+1-555-0101",
                full_name="John Pharmacist",
                hashed_password=get_password_hash("pharma123"),
                role=UserRole.PHARMACIST,
                is_active=True,
                is_phone_verified=True
            )
            db.add(pharmacist_user)
        
        # Create sample pharmacy
        if not db.query(Pharmacy).first():
            pharmacy = Pharmacy(
                name="QuickMed Central Pharmacy",
                address="456 Main St, City Center",
                phone="+1-555-0200",
                email="central@quickmed.com",
                latitude=40.7128,
                longitude=-74.0060,
                operating_hours="24/7",
                is_active=True
            )
            db.add(pharmacy)
        
        db.commit()
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()

# HTML Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page."""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """User dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/medicines", response_class=HTMLResponse)
async def medicines_page(request: Request, db: Session = Depends(get_db)):
    """Browse medicines page."""
    categories = db.query(Category).all()
    medicines = db.query(Medicine).filter(Medicine.is_available == True).limit(20).all()
    return templates.TemplateResponse("medicines.html", {
        "request": request, 
        "categories": categories,
        "medicines": medicines
    })

@app.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request):
    """Shopping cart page."""
    return templates.TemplateResponse("cart.html", {"request": request})

@app.get("/prescriptions", response_class=HTMLResponse)
async def prescriptions_page(request: Request):
    """Prescriptions management page."""
    return templates.TemplateResponse("prescriptions.html", {"request": request})

@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    """Orders history page."""
    return templates.TemplateResponse("orders.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page."""
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin dashboard."""
    return templates.TemplateResponse("admin.html", {"request": request})

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 