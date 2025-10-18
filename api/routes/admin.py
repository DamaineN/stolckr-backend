"""
Admin API routes for user management and system administration
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

from api.middleware.admin import get_current_admin_user
from api.database.mongodb import get_database, UserService, AuditService
from api.database.mongodb_models import UserRole, UserStatus, UserInDB

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin Response Models
class AdminUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    total_xp: int = 0
    current_role_xp: int = 0
    login_streak: int = 0
    last_daily_checkin_date: Optional[datetime] = None

class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    suspended_users: int
    admin_users: int
    users_by_role: Dict[str, int]
    users_registered_today: int
    users_registered_this_week: int
    users_registered_this_month: int
    average_user_xp: float
    most_active_users: List[Dict[str, Any]]

class UserUpdateRequest(BaseModel):
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_verified: Optional[bool] = None

class AdminUserCreationRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.ADMIN

# Helper function to calculate login streak
def calculate_login_streak(user_doc: Dict[str, Any]) -> int:
    """Calculate current login streak based on last daily checkin date"""
    last_checkin = user_doc.get("last_daily_checkin_date")
    if not last_checkin:
        return 0
    
    # Convert to UTC datetime if it's not already
    if isinstance(last_checkin, str):
        last_checkin = datetime.fromisoformat(last_checkin.replace('Z', '+00:00'))
    
    # Calculate days between last checkin and today
    today = datetime.now(timezone.utc).date()
    last_checkin_date = last_checkin.date()
    
    days_diff = (today - last_checkin_date).days
    
    # If they checked in yesterday or today, they maintain streak
    if days_diff <= 1:
        return user_doc.get("current_streak", 0)
    else:
        return 0  # Streak broken

@router.get("/users", response_model=List[AdminUserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of users to return"),
    role_filter: Optional[UserRole] = Query(None, description="Filter users by role"),
    status_filter: Optional[UserStatus] = Query(None, description="Filter users by status"),
    search: Optional[str] = Query(None, description="Search users by name or email"),
    admin_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Get all users with optional filtering and pagination"""
    user_service = UserService(db)
    
    try:
        # Build filter criteria
        filter_criteria = {}
        
        if role_filter:
            filter_criteria["role"] = role_filter.value
            
        if status_filter:
            filter_criteria["status"] = status_filter.value
            
        if search:
            filter_criteria["$or"] = [
                {"full_name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]
        
        # Get users from database
        users_cursor = db.users.find(filter_criteria).skip(skip).limit(limit)
        users = await users_cursor.to_list(length=limit)
        
        # Convert to response format
        admin_users = []
        for user_doc in users:
            login_streak = calculate_login_streak(user_doc)
            
            admin_users.append(AdminUserResponse(
                id=str(user_doc["_id"]),
                email=user_doc["email"],
                full_name=user_doc["full_name"],
                role=user_doc.get("role", UserRole.BEGINNER),
                status=user_doc.get("status", UserStatus.ACTIVE),
                is_verified=user_doc.get("is_verified", False),
                created_at=user_doc["created_at"],
                updated_at=user_doc["updated_at"],
                last_login=user_doc.get("last_login"),
                total_xp=user_doc.get("total_xp", 0),
                current_role_xp=user_doc.get("current_role_xp", 0),
                login_streak=login_streak,
                last_daily_checkin_date=user_doc.get("last_daily_checkin_date")
            ))
        
        return admin_users
        
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching users"
        )

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Get comprehensive admin statistics"""
    try:
        # Total user counts
        total_users = await db.users.count_documents({})
        active_users = await db.users.count_documents({"status": UserStatus.ACTIVE.value})
        inactive_users = await db.users.count_documents({"status": UserStatus.INACTIVE.value})
        suspended_users = await db.users.count_documents({"status": UserStatus.SUSPENDED.value})
        admin_users = await db.users.count_documents({"role": UserRole.ADMIN.value})
        
        # Users by role
        role_pipeline = [
            {"$group": {"_id": "$role", "count": {"$sum": 1}}}
        ]
        role_counts = await db.users.aggregate(role_pipeline).to_list(length=None)
        users_by_role = {item["_id"]: item["count"] for item in role_counts}
        
        # Time-based registrations
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        users_today = await db.users.count_documents({"created_at": {"$gte": today_start}})
        users_week = await db.users.count_documents({"created_at": {"$gte": week_start}})
        users_month = await db.users.count_documents({"created_at": {"$gte": month_start}})
        
        # Average user XP
        xp_pipeline = [
            {"$group": {"_id": None, "avg_xp": {"$avg": "$total_xp"}}}
        ]
        xp_result = await db.users.aggregate(xp_pipeline).to_list(length=1)
        avg_xp = xp_result[0]["avg_xp"] if xp_result else 0.0
        
        # Most active users (top 10 by XP)
        most_active_cursor = db.users.find({}).sort("total_xp", -1).limit(10)
        most_active_docs = await most_active_cursor.to_list(length=10)
        most_active_users = [
            {
                "id": str(user["_id"]),
                "full_name": user["full_name"],
                "email": user["email"],
                "total_xp": user.get("total_xp", 0),
                "role": user.get("role", UserRole.BEGINNER.value),
                "login_streak": calculate_login_streak(user)
            }
            for user in most_active_docs
        ]
        
        return AdminStatsResponse(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            suspended_users=suspended_users,
            admin_users=admin_users,
            users_by_role=users_by_role,
            users_registered_today=users_today,
            users_registered_this_week=users_week,
            users_registered_this_month=users_month,
            average_user_xp=avg_xp,
            most_active_users=most_active_users
        )
        
    except Exception as e:
        logger.error(f"Error fetching admin stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching statistics"
        )

@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user_by_id(
    user_id: str,
    admin_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Get detailed information about a specific user"""
    user_service = UserService(db)
    
    try:
        user_doc = await user_service.get_user_by_id(user_id)
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        login_streak = calculate_login_streak(user_doc)
        
        return AdminUserResponse(
            id=str(user_doc["_id"]),
            email=user_doc["email"],
            full_name=user_doc["full_name"],
            role=user_doc.get("role", UserRole.BEGINNER),
            status=user_doc.get("status", UserStatus.ACTIVE),
            is_verified=user_doc.get("is_verified", False),
            created_at=user_doc["created_at"],
            updated_at=user_doc["updated_at"],
            last_login=user_doc.get("last_login"),
            total_xp=user_doc.get("total_xp", 0),
            current_role_xp=user_doc.get("current_role_xp", 0),
            login_streak=login_streak,
            last_daily_checkin_date=user_doc.get("last_daily_checkin_date")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user"
        )

@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    admin_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Update user role, status, or verification"""
    user_service = UserService(db)
    audit_service = AuditService(db)
    
    try:
        # Get current user data
        user_doc = await user_service.get_user_by_id(user_id)
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent admin from changing their own role/status
        if user_id == admin_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify your own account"
            )
        
        # Build update data
        update_fields = {}
        if update_data.role is not None:
            update_fields["role"] = update_data.role.value
        if update_data.status is not None:
            update_fields["status"] = update_data.status.value
        if update_data.is_verified is not None:
            update_fields["is_verified"] = update_data.is_verified
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
        
        # Update user
        success = await user_service.update_user(user_id, update_fields)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
        
        # Log the admin action
        await audit_service.log_action({
            "user_id": ObjectId(admin_user["user_id"]),
            "action": "admin_user_update",
            "resource": f"user:{user_id}",
            "details": {
                "updated_fields": update_fields,
                "target_user_email": user_doc["email"]
            },
            "success": True
        })
        
        # Get updated user data
        updated_user = await user_service.get_user_by_id(user_id)
        login_streak = calculate_login_streak(updated_user)
        
        return AdminUserResponse(
            id=str(updated_user["_id"]),
            email=updated_user["email"],
            full_name=updated_user["full_name"],
            role=updated_user.get("role", UserRole.BEGINNER),
            status=updated_user.get("status", UserStatus.ACTIVE),
            is_verified=updated_user.get("is_verified", False),
            created_at=updated_user["created_at"],
            updated_at=updated_user["updated_at"],
            last_login=updated_user.get("last_login"),
            total_xp=updated_user.get("total_xp", 0),
            current_role_xp=updated_user.get("current_role_xp", 0),
            login_streak=login_streak,
            last_daily_checkin_date=updated_user.get("last_daily_checkin_date")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Delete a user account and all associated data"""
    user_service = UserService(db)
    audit_service = AuditService(db)
    
    try:
        # Get user data before deletion
        user_doc = await user_service.get_user_by_id(user_id)
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent admin from deleting themselves
        if user_id == admin_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Prevent deletion of other admin users (safety measure)
        if user_doc.get("role") == UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete admin users"
            )
        
        user_email = user_doc["email"]
        
        # Delete user and associated data
        user_obj_id = ObjectId(user_id)
        
        # Delete from various collections
        await db.users.delete_one({"_id": user_obj_id})
        await db.watchlists.delete_many({"user_id": user_obj_id})
        await db.portfolios.delete_many({"user_id": user_obj_id})
        await db.paper_trading_portfolios.delete_many({"user_id": user_obj_id})
        await db.paper_trading_holdings.delete_many({"user_id": user_obj_id})
        await db.trade_history.delete_many({"user_id": user_obj_id})
        await db.predictions.delete_many({"user_id": user_obj_id})
        await db.user_profiles.delete_many({"user_id": user_obj_id})
        await db.investment_goals.delete_many({"user_id": user_obj_id})
        await db.xp_activities.delete_many({"user_id": user_obj_id})
        await db.user_activities.delete_many({"user_id": user_obj_id})
        
        # Log the deletion
        await audit_service.log_action({
            "user_id": ObjectId(admin_user["user_id"]),
            "action": "admin_user_delete",
            "resource": f"user:{user_id}",
            "details": {
                "deleted_user_email": user_email
            },
            "success": True
        })
        
        return {"message": f"User {user_email} has been successfully deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting user"
        )

@router.post("/users", response_model=AdminUserResponse)
async def create_admin_user(
    user_data: AdminUserCreationRequest,
    admin_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Create a new admin user"""
    user_service = UserService(db)
    audit_service = AuditService(db)
    
    try:
        # Import auth utilities
        from api.auth.utils import AuthUtils
        
        # Check if user already exists
        existing_user = await user_service.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate password strength
        password_validation = AuthUtils.validate_password_strength(user_data.password)
        if not password_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password validation failed: {', '.join(password_validation['errors'])}"
            )
        
        # Create user document
        user_doc = UserInDB(
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            hashed_password=AuthUtils.get_password_hash(user_data.password),
            is_verified=True  # Admin-created users are auto-verified
        ).model_dump(by_alias=True)
        
        # Save user to database
        user_id = await user_service.create_user(user_doc)
        
        # Log the creation
        await audit_service.log_action({
            "user_id": ObjectId(admin_user["user_id"]),
            "action": "admin_user_create",
            "resource": f"user:{user_id}",
            "details": {
                "created_user_email": user_data.email,
                "created_user_role": user_data.role.value
            },
            "success": True
        })
        
        # Get created user data
        created_user = await user_service.get_user_by_id(user_id)
        
        return AdminUserResponse(
            id=str(created_user["_id"]),
            email=created_user["email"],
            full_name=created_user["full_name"],
            role=created_user.get("role", UserRole.BEGINNER),
            status=created_user.get("status", UserStatus.ACTIVE),
            is_verified=created_user.get("is_verified", False),
            created_at=created_user["created_at"],
            updated_at=created_user["updated_at"],
            last_login=created_user.get("last_login"),
            total_xp=created_user.get("total_xp", 0),
            current_role_xp=created_user.get("current_role_xp", 0),
            login_streak=0,
            last_daily_checkin_date=created_user.get("last_daily_checkin_date")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating admin user"
        )