# Enhanced Secure Authentication API

A comprehensive secure user authentication system with advanced security features including JWT tokens, refresh tokens, rate limiting, and input sanitization.

## Features

- JWT access tokens (30-min) + refresh tokens (7-day)
- Redis-based rate limiting with fallback
- Input sanitization and XSS protection
- Security headers (HSTS, CSP, X-Frame-Options)
- Password reset functionality
- Health monitoring endpoints
- Role-based access control
- Comprehensive error handling

## Installation

1. Create virtual environment:
```bash
python3 -m venv venv
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

API available at `http://localhost:8000` | Docs at `http://localhost:8000/docs`

## API Endpoints

### Authentication
- `POST /auth/register` - Register (3/min)
- `POST /auth/login` - Login (5/min)
- `POST /auth/refresh` - Refresh token
- `POST /auth/logout` - Logout
- `POST /auth/forgot-password` - Password reset (1/min)
- `POST /auth/reset-password` - Confirm reset
- `GET /auth/me` - Current user info

### User Management (Admin Only)
- `GET /users` - List users
- `GET /users/{id}` - Get user
- `PUT /users/{id}/role` - Update role
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user

### Health
- `GET /health` - System health check
- `GET /health/database` - Database status
- `GET /health/redis` - Redis status

## Security Features

- **Rate Limiting**: Login (5/min), Register (3/min), Password Reset (1/min)
- **Input Sanitization**: XSS and SQL injection protection
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **Password Reset**: Secure token-based reset system
- **Request Validation**: Comprehensive input validation

## Technology Stack

- **FastAPI** - Web framework
- **SQLAlchemy** - Database ORM
- **Redis** - Rate limiting & caching
- **JWT** - Token authentication
- **bcrypt** - Password hashing
- **Pydantic** - Data validation
- **SQLite** - Database 