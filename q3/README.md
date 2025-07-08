# Q3 - Quick Commerce Medicine Delivery Application

A comprehensive medicine delivery platform with 10-30 minute delivery promise, built with FastAPI and modern web technologies.

## 🚀 Features

### Core Features
- **Quick Delivery**: 10-30 minute delivery with 10-minute emergency delivery
- **Medicine Catalog**: Search, filter, and browse medicines by category
- **Prescription Management**: Upload, verify, and manage prescriptions
- **Shopping Cart**: Add medicines with prescription validation
- **Order Tracking**: Real-time order status and delivery tracking
- **User Authentication**: JWT-based authentication with role-based access
- **Medical Profiles**: Store user medical information and allergies

### User Roles
- **User**: Browse medicines, place orders, manage prescriptions
- **Admin**: Manage medicines, users, orders, and system settings
- **Pharmacist**: Verify prescriptions and manage inventory
- **Delivery Partner**: Handle deliveries and update order status

### Emergency Features
- **Emergency Delivery**: 10-minute delivery for critical medicines
- **Emergency Medicine Catalog**: Pre-approved medicines for emergency delivery
- **Priority Processing**: Emergency orders get priority handling

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT tokens
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **File Upload**: Support for prescription images
- **API Documentation**: Auto-generated with FastAPI/Swagger

## 📋 Prerequisites

- Python 3.8+
- pip (Python package manager)

## 🚀 Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd q3
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Access the application**
   - Open your browser and go to `http://localhost:8000`
   - API documentation available at `http://localhost:8000/docs`

## 🏗️ Project Structure

```
q3/
├── app/
│   ├── routers/
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── medicines.py      # Medicine CRUD operations
│   │   ├── cart.py           # Shopping cart functionality
│   │   ├── orders.py         # Order management
│   │   └── prescriptions.py  # Prescription handling
│   ├── models.py             # Database models
│   ├── schemas.py            # Pydantic schemas
│   ├── database.py           # Database configuration
│   ├── auth.py               # Authentication utilities
│   ├── config.py             # Application settings
│   └── dependencies.py       # Dependency injection
├── static/
│   ├── style.css             # CSS styles
│   └── app.js                # JavaScript functionality
├── templates/
│   ├── index.html            # Home page
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   ├── dashboard.html        # User dashboard
│   ├── medicines.html        # Medicine catalog
│   ├── cart.html             # Shopping cart
│   ├── orders.html           # Order history
│   ├── prescriptions.html    # Prescription management
│   ├── profile.html          # User profile
│   └── admin.html            # Admin dashboard
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 📚 API Documentation

### Authentication Endpoints

#### POST /auth/register
Register a new user with medical profile
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password",
  "full_name": "John Doe",
  "phone": "+1-555-0123",
  "age": 30,
  "medical_conditions": "Diabetes",
  "allergies": "Penicillin",
  "address": "123 Main St",
  "city": "New York",
  "state": "NY",
  "zip_code": "10001"
}
```

#### POST /auth/login
Login with username and password
```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

### Medicine Endpoints

#### GET /medicines/
Get all medicines with optional filters
- Query parameters: `category_id`, `search`, `prescription_required`, `emergency_available`

#### GET /medicines/{id}
Get specific medicine details

#### POST /medicines/ (Admin only)
Add new medicine to catalog

#### PUT /medicines/{id} (Admin only)
Update medicine information

### Cart Endpoints

#### GET /cart/
Get user's cart with prescription validation

#### POST /cart/items
Add medicine to cart
```json
{
  "medicine_id": 1,
  "quantity": 2,
  "prescription_id": 1
}
```

#### PUT /cart/items/{id}
Update cart item quantity

#### DELETE /cart/items/{id}
Remove item from cart

### Order Endpoints

#### POST /orders/
Create order from cart
```json
{
  "delivery_address": "123 Main St, New York, NY 10001",
  "delivery_phone": "+1-555-0123",
  "payment_method": "credit_card",
  "is_emergency": false,
  "delivery_notes": "Leave at door"
}
```

#### GET /orders/
Get user's order history

#### GET /orders/{id}
Get specific order details

#### GET /orders/{id}/track
Real-time order tracking

### Prescription Endpoints

#### POST /prescriptions/upload
Upload prescription image
```json
{
  "doctor_name": "Dr. Smith",
  "doctor_license": "MD123456",
  "notes": "Regular prescription"
}
```

#### GET /prescriptions/
Get user's prescriptions

#### POST /prescriptions/{id}/verify (Pharmacist only)
Verify uploaded prescription

## 🎯 Usage Examples

### User Registration
```javascript
const userData = {
  username: 'john_doe',
  email: 'john@example.com',
  password: 'secure_password',
  full_name: 'John Doe',
  phone: '+1-555-0123',
  age: 30,
  address: '123 Main St',
  city: 'New York',
  state: 'NY',
  zip_code: '10001'
};

const response = await fetch('/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(userData)
});
```

### Add Medicine to Cart
```javascript
const cartItem = {
  medicine_id: 1,
  quantity: 2,
  prescription_id: 1  // Required for prescription medicines
};

const response = await fetch('/cart/items', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(cartItem)
});
```

### Place Order
```javascript
const orderData = {
  delivery_address: '123 Main St, New York, NY 10001',
  delivery_phone: '+1-555-0123',
  payment_method: 'credit_card',
  is_emergency: false
};

const response = await fetch('/orders/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(orderData)
});
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:
```
SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///./quickmed.db
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Sample Data
The application automatically creates sample data on startup:
- Admin user: `admin` / `admin123`
- Pharmacist user: `pharmacist` / `pharma123`
- Sample medicine categories and medicines
- Sample pharmacy data

## 🚑 Emergency Delivery

### How it Works
1. User requests emergency delivery
2. System checks for emergency-available medicines
3. Order is prioritized for 10-minute delivery
4. Delivery partner is immediately assigned
5. Real-time tracking is provided

### Emergency Medicines
Pre-approved medicines available for emergency delivery:
- Pain relievers (Paracetamol, Ibuprofen)
- Emergency medications (Aspirin, Insulin)
- First aid supplies

## 🔐 Security Features

- JWT-based authentication
- Role-based access control
- Password hashing with bcrypt
- Input validation and sanitization
- File upload restrictions
- SQL injection prevention

## 📱 Mobile Responsive

The application is fully responsive and works on:
- Desktop browsers
- Tablet devices
- Mobile phones

## 🧪 Testing

Run the application locally:
```bash
python main.py
```

Access different user roles:
- **Admin**: Login with `admin` / `admin123`
- **Pharmacist**: Login with `pharmacist` / `pharma123`
- **User**: Register a new account

## 🔄 API Rate Limiting

The application implements basic rate limiting:
- Authentication endpoints: 5 requests per minute
- General endpoints: 100 requests per minute
- Emergency endpoints: 20 requests per minute

## 📊 Database Schema

### Key Models
- **User**: User accounts with medical profiles
- **Medicine**: Medicine catalog with stock and pricing
- **Category**: Medicine categories
- **Prescription**: Uploaded prescriptions with verification status
- **Cart**: Shopping cart items
- **Order**: Order management with delivery tracking
- **Pharmacy**: Pharmacy information
- **DeliveryPartner**: Delivery partner management

