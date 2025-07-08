import bleach
import re
from typing import Any, Dict
from fastapi import Request

# HTML tags and attributes allowed in sanitization
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'i', 'b', 'a', 'ul', 'ol', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'blockquote': ['cite'],
}

def sanitize_html(text: str) -> str:
    """Sanitize HTML content to prevent XSS attacks."""
    if not text:
        return text
    
    cleaned = bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    return cleaned

def sanitize_string(text: str) -> str:
    """Sanitize string input by removing potentially harmful characters."""
    if not text:
        return text
    
    # Remove null bytes and control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Remove SQL injection patterns
    sql_patterns = [
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
        r"(--|#|/\*|\*/)",
        r"([';])",
    ]
    
    for pattern in sql_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Remove XSS patterns
    xss_patterns = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
    ]
    
    for pattern in xss_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()

def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize dictionary values."""
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        sanitized_key = sanitize_string(str(key))
        
        if isinstance(value, str):
            sanitized[sanitized_key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[sanitized_key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[sanitized_key] = [
                sanitize_string(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            sanitized[sanitized_key] = value
    
    return sanitized

def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown" 