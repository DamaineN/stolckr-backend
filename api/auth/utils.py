"""
Authentication utilities for JWT-based authentication
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import re
from config.settings import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# HTTP Bearer for JWT
security = HTTPBearer()

class AuthUtils:
    """Authentication utility class"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a plain password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        Validate password strength
        
        Requirements:
        - At least 8 characters long
        - Contains uppercase letter
        - Contains lowercase letter  
        - Contains digit
        - Contains special character
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
            
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
            
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
            
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "strength": AuthUtils._calculate_password_strength(password)
        }
    
    @staticmethod
    def _calculate_password_strength(password: str) -> str:
        """Calculate password strength score"""
        score = 0
        
        # Length bonus
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
            
        # Character variety bonus
        if re.search(r"[a-z]", password):
            score += 1
        if re.search(r"[A-Z]", password):
            score += 1
        if re.search(r"\d", password):
            score += 1
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            score += 1
            
        if score <= 2:
            return "weak"
        elif score <= 4:
            return "medium"
        else:
            return "strong"
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            
            # Check token type
            if payload.get("type") != token_type:
                return None
                
            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                return None
                
            if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return None
                
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(length)

# Dependency for getting current user from JWT token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = AuthUtils.verify_token(credentials.credentials, "access")
        if payload is None:
            raise credentials_exception
            
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        return {"user_id": user_id, "email": payload.get("email"), "role": payload.get("role", "user")}
    except Exception:
        raise credentials_exception

# Optional user dependency (for endpoints that work with or without auth)
async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
    """Optional dependency to get current user (returns None if not authenticated)"""
    if not credentials:
        return None
        
    try:
        payload = AuthUtils.verify_token(credentials.credentials, "access")
        if payload is None:
            return None
            
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
            
        return {"user_id": user_id, "email": payload.get("email"), "role": payload.get("role", "user")}
    except Exception:
        return None
