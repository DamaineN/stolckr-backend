"""
Admin authentication middleware for protecting admin routes
"""
from fastapi import HTTPException, status, Depends
from typing import Dict, Any
from api.auth.utils import get_current_user
from api.database.mongodb_models import UserRole

def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that ensures the current user is an admin
    """
    user_role = current_user.get("role")
    
    # Allow hardcoded admin or database admin
    if user_role != UserRole.ADMIN.value and user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Alternative admin requirement function
    """
    return get_current_admin_user(current_user)