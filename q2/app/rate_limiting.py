import redis
import time
from typing import Optional
from fastapi import HTTPException, Request, status
from app.config import settings

redis_client = None

def get_redis_client():
    """Get Redis client singleton."""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            redis_client.ping()
        except redis.RedisError:
            redis_client = InMemoryRateLimiter()
    return redis_client

class InMemoryRateLimiter:
    """In-memory fallback rate limiter when Redis is not available."""
    
    def __init__(self):
        self.requests = {}
    
    def get(self, key: str) -> Optional[str]:
        if key in self.requests:
            timestamp, count = self.requests[key]
            if time.time() - timestamp < 60:
                return str(count)
            else:
                del self.requests[key]
        return None
    
    def set(self, key: str, value: str, ex: int = 60) -> None:
        self.requests[key] = (time.time(), int(value))
    
    def incr(self, key: str) -> int:
        current_time = time.time()
        if key in self.requests:
            timestamp, count = self.requests[key]
            if current_time - timestamp < 60:
                count += 1
                self.requests[key] = (timestamp, count)
                return count
            else:
                self.requests[key] = (current_time, 1)
                return 1
        else:
            self.requests[key] = (current_time, 1)
            return 1
    
    def expire(self, key: str, seconds: int) -> None:
        pass

def check_rate_limit(request: Request, endpoint: str, limit: int, window: int = 60) -> bool:
    """Check if request is within rate limit."""
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    
    key = f"rate_limit:{endpoint}:{client_ip}"
    
    try:
        redis_client = get_redis_client()
        current_count = redis_client.get(key)
        
        if current_count is None:
            redis_client.set(key, "1", ex=window)
            return True
        
        current_count = int(current_count)
        
        if current_count >= limit:
            return False
        
        redis_client.incr(key)
        redis_client.expire(key, window)
        
        return True
        
    except Exception:
        return True

def rate_limit_middleware(endpoint: str, limit: int, window: int = 60):
    """Rate limiting middleware decorator."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if request and not check_rate_limit(request, endpoint, limit, window):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(window)}
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def login_rate_limit(func):
    return rate_limit_middleware("login", settings.login_rate_limit)(func)

def registration_rate_limit(func):
    return rate_limit_middleware("registration", settings.registration_rate_limit)(func)

def password_reset_rate_limit(func):
    return rate_limit_middleware("password_reset", settings.password_reset_rate_limit)(func) 