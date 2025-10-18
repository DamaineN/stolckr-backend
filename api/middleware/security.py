"""
Security middleware for rate limiting, validation, and security headers
"""
import time
import re
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional, Set
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for additional protection"""
    
    def __init__(self, app, allowed_hosts: Optional[Set[str]] = None):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or set()
        self.blocked_ips: Dict[str, datetime] = {}
        self.failed_attempts: Dict[str, int] = defaultdict(int)
        self.suspicious_patterns = [
            r'<script.*?>',  # XSS attempts
            r'union.*select',  # SQL injection
            r'drop.*table',  # SQL injection
            r'exec\(',  # Code execution
            r'eval\(',  # Code execution
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security checks"""
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check if IP is blocked
        if self._is_blocked(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "IP temporarily blocked due to suspicious activity"}
            )
        
        # Validate request
        if not self._validate_request(request):
            self._record_suspicious_activity(client_ip)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid request"}
            )
        
        # Add security headers
        response = await call_next(request)
        self._add_security_headers(response)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _is_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked"""
        if ip in self.blocked_ips:
            if datetime.now() < self.blocked_ips[ip]:
                return True
            else:
                # Unblock expired IPs
                del self.blocked_ips[ip]
                if ip in self.failed_attempts:
                    del self.failed_attempts[ip]
        return False
    
    def _validate_request(self, request: Request) -> bool:
        """Validate request for malicious patterns"""
        try:
            # Check URL path
            path = str(request.url.path).lower()
            query = str(request.url.query).lower()
            
            # Check for suspicious patterns
            for pattern in self.suspicious_patterns:
                if re.search(pattern, path + " " + query, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected: {pattern} from {self._get_client_ip(request)}")
                    return False
            
            # Check headers for suspicious content
            user_agent = request.headers.get("user-agent", "").lower()
            if "sqlmap" in user_agent or "nmap" in user_agent or len(user_agent) > 1000:
                logger.warning(f"Suspicious user agent: {user_agent[:100]} from {self._get_client_ip(request)}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating request: {str(e)}")
            return True  # Allow request if validation fails
    
    def _record_suspicious_activity(self, ip: str):
        """Record suspicious activity and block if needed"""
        self.failed_attempts[ip] += 1
        
        # Block IP after 10 suspicious attempts
        if self.failed_attempts[ip] >= 10:
            self.blocked_ips[ip] = datetime.now() + timedelta(hours=1)
            logger.warning(f"Blocked IP {ip} for suspicious activity")
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value

# Input validation utilities
class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_stock_symbol(symbol: str) -> bool:
        """Validate stock symbol format"""
        if not symbol or len(symbol) > 10:
            return False
        return re.match(r'^[A-Za-z0-9.-]+$', symbol) is not None
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email or len(email) > 254:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, any]:
        """Validate password strength"""
        if not password:
            return {"valid": False, "errors": ["Password is required"]}
        
        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        if len(password) > 128:
            errors.append("Password must be less than 128 characters")
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    @staticmethod
    def sanitize_string(input_string: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not input_string:
            return ""
        
        # Remove HTML tags and limit length
        sanitized = re.sub(r'<[^>]+>', '', input_string[:max_length])
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', sanitized)
        
        return sanitized.strip()

# Rate limiting decorators
class RateLimiters:
    """Rate limiting configurations"""
    
    # General API limits
    GENERAL_LIMIT = "100/minute"
    
    # Authentication limits (stricter)
    AUTH_LIMIT = "5/minute"
    
    # Stock data limits (moderate)
    STOCK_DATA_LIMIT = "50/minute" 
    
    # Prediction limits (stricter due to computation)
    PREDICTION_LIMIT = "10/minute"

# Dependency for input validation
def validate_stock_symbol(symbol: str) -> str:
    """Dependency to validate stock symbol"""
    if not InputValidator.validate_stock_symbol(symbol):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stock symbol format"
        )
    return symbol.upper()

def validate_pagination(skip: int = 0, limit: int = 50) -> Dict[str, int]:
    """Dependency to validate pagination parameters"""
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip value cannot be negative"
        )
    
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100"
        )
    
    return {"skip": skip, "limit": limit}

# Error handler for rate limiting
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded handler"""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Too many requests. Limit: {exc.detail}",
            "retry_after": getattr(exc, 'retry_after', 60)
        }
    )
