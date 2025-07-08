from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime
import time

from app.database import engine, Base
from app.routers import auth, users, health
from app.config import settings
from app.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    general_exception_handler,
    SecurityException,
    RateLimitException
)

Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Enhanced Secure Authentication API",
    description="A comprehensive secure user authentication system with JWT tokens, rate limiting, and advanced security features",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.state.limiter = limiter

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization", 
        "Content-Type", 
        "X-Requested-With",
        "Accept",
        "Origin",
        "User-Agent",
        "X-CSRF-Token"
    ],
    expose_headers=["X-Process-Time"],
    max_age=86400,
)

app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SecurityException, http_exception_handler)
app.add_exception_handler(RateLimitException, http_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(health.router, prefix="", tags=["Health"])

@app.get("/")
async def root():
    return {
        "message": "Enhanced Secure Authentication API",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "authentication": "/auth",
            "users": "/users",
            "health": "/health",
            "documentation": "/docs"
        }
    } 