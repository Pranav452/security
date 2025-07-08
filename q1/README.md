# Secure User Authentication System

A secure user authentication system built with FastAPI, featuring JWT tokens and role-based access control.

## Features

- JWT token authentication with 30-minute expiration
- bcrypt password hashing with strong password requirements
- Role-based access control (USER/ADMIN)
- Input validation using Pydantic
- SQLAlchemy ORM with SQLite database
- Automatic API documentation

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user info (protected)

### User Management (Admin Only)
- `GET /users` - Get all users
- `GET /users/{user_id}` - Get user by ID
- `PUT /users/{user_id}/role` - Change user role
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user

## Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

## Technology Stack

- **FastAPI** - Web framework
- **SQLAlchemy** - Database ORM
- **JWT** - Token authentication
- **bcrypt** - Password hashing
- **Pydantic** - Data validation
- **SQLite** - Database 