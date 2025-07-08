from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.auth import verify_token
from app.security import get_client_ip

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    token_data = verify_token(token, credentials_exception)
    
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

class SecurityMiddleware:
    """Security middleware for request processing."""
    
    def __init__(self, request: Request):
        self.request = request
        self.client_ip = get_client_ip(request)
    
    def validate_request(self):
        """Validate request for security issues."""
        suspicious_headers = [
            "X-Forwarded-Host",
            "X-Original-URL",
            "X-Rewrite-URL"
        ]
        
        for header in suspicious_headers:
            if header in self.request.headers:
                print(f"Suspicious header detected: {header} from IP: {self.client_ip}")
        
        if len(str(self.request.url)) > 2048:
            raise HTTPException(
                status_code=status.HTTP_414_REQUEST_URI_TOO_LONG,
                detail="Request URI too long"
            )
        
        user_agent = self.request.headers.get("User-Agent", "")
        if len(user_agent) > 512:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user agent"
            )

def security_middleware(request: Request):
    """Security middleware dependency."""
    middleware = SecurityMiddleware(request)
    middleware.validate_request()
    
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "Unknown")
    endpoint = request.url.path
    method = request.method
    
    print(f"[{method}] {endpoint} - IP: {client_ip} - User-Agent: {user_agent}")
    
    return middleware 