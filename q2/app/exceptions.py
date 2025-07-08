from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityException(HTTPException):
    """Custom exception for security-related errors."""
    def __init__(self, detail: str, status_code: int = status.HTTP_403_FORBIDDEN):
        super().__init__(status_code=status_code, detail=detail)

class RateLimitException(HTTPException):
    """Custom exception for rate limiting errors."""
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: str = "60"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": retry_after}
        )

async def http_exception_handler(request: Request, exc: HTTPException):
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    
    if exc.status_code >= 400:
        logger.warning(
            f"HTTP {exc.status_code} - {request.method} {request.url.path} - "
            f"IP: {client_ip} - Detail: {exc.detail}"
        )
    
    if exc.status_code == 500:
        detail = "Internal server error"
    else:
        detail = exc.detail
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": detail,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        }
    )
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    if hasattr(exc, 'headers') and exc.headers:
        for key, value in exc.headers.items():
            response.headers[key] = value
    
    return response

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    
    logger.warning(
        f"Validation error - {request.method} {request.url.path} - "
        f"IP: {client_ip} - Errors: {exc.errors()}"
    )
    
    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    response = JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path,
                "details": formatted_errors
            }
        }
    )
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

async def integrity_error_handler(request: Request, exc: IntegrityError):
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    
    logger.error(
        f"Database integrity error - {request.method} {request.url.path} - "
        f"IP: {client_ip} - Error: {str(exc)}"
    )
    
    error_message = "Database constraint violation"
    if "UNIQUE constraint failed" in str(exc):
        if "username" in str(exc):
            error_message = "Username already exists"
        elif "email" in str(exc):
            error_message = "Email already registered"
        else:
            error_message = "Duplicate entry"
    
    response = JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": 409,
                "message": error_message,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        }
    )
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

async def general_exception_handler(request: Request, exc: Exception):
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    
    logger.error(
        f"Unexpected error - {request.method} {request.url.path} - "
        f"IP: {client_ip} - Error: {str(exc)}",
        exc_info=True
    )
    
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        }
    )
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response 