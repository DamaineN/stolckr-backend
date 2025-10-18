"""
XP API Routes - Handles user XP and role progression through natural usage
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from api.auth.utils import get_current_user
from api.database.mongodb import get_database
from api.database.mongodb_models import XPActivityType
from api.services.xp_service import XPService

router = APIRouter()

# Pydantic models for API requests
class AwardXPRequest(BaseModel):
    activity_type: XPActivityType
    description: str
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    multiplier: float = 1.0

class GoalProgressUpdate(BaseModel):
    goal_id: str
    progress_increment: int = 1

@router.get("/progress")
async def get_user_progress(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get user XP progress and role information"""
    try:
        xp_service = XPService(db)
        xp_stats = await xp_service.get_user_xp_stats(current_user["user_id"])
        
        if "error" in xp_stats:
            raise HTTPException(status_code=500, detail=xp_stats["error"])
        
        # Format response to match frontend expectations
        response = {
            "user_id": current_user["user_id"],
            "current_role": xp_stats.get("current_role", "beginner"),
            "total_xp": xp_stats.get("total_xp", 0),
            "next_role": None,
            "recent_activities": xp_stats.get("recent_activities", [])
        }
        
        # Add next role info if available
        next_role_info = xp_stats.get("next_role_info")
        if next_role_info:
            # Fix the next_role formatting - remove UserRole. prefix
            next_role_name = str(next_role_info["next_role"])
            if next_role_name.startswith("UserRole."):
                next_role_name = next_role_name.replace("UserRole.", "")
            
            response["next_role"] = {
                "next_role": next_role_name,
                "required_xp": next_role_info["total_needed"],
                "current_xp": xp_stats["total_xp"],
                "remaining_xp": next_role_info["xp_needed"],
                "progress_percentage": ((xp_stats["total_xp"] / next_role_info["total_needed"]) * 100) if next_role_info["total_needed"] > 0 else 0
            }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get user progress: {str(e)}")

@router.post("/award-xp")
async def award_xp(
    request: AwardXPRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Award XP to user for completing activities"""
    try:
        xp_service = XPService(db)
        
        # Award XP directly
        result = await xp_service.award_xp(
            user_id=current_user["user_id"],
            activity_type=request.activity_type.value,
            description=request.description,
            related_entity_id=request.related_entity_id,
            related_entity_type=request.related_entity_type,
            multiplier=request.multiplier
        )
        
        return {
            "success": True,
            "xp_earned": result.get("xp_earned", 0),
            "activity_type": request.activity_type.value,
            "message": result.get("message", "XP awarded successfully!"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to award XP: {str(e)}")

@router.get("/xp-activities")
async def get_xp_activities(
    limit: int = 20,
    skip: int = 0,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get user's XP activity history"""
    try:
        xp_activities_collection = db["xp_activities"]
        
        user_id = current_user["user_id"]  # Use string ID directly
        
        activities = await xp_activities_collection.find({
            "user_id": user_id
        }).sort("earned_at", -1).skip(skip).limit(limit).to_list(None)
        
        return {
            "activities": [{
                "id": str(activity["_id"]),
                "activity_type": activity["activity_type"],
                "description": activity["activity_description"],
                "xp_earned": activity["xp_earned"],
                "multiplier": activity.get("multiplier", 1.0),
                "related_entity_id": activity.get("related_entity_id"),
                "related_entity_type": activity.get("related_entity_type"),
                "earned_at": activity["earned_at"].isoformat()
            } for activity in activities],
            "total_count": await xp_activities_collection.count_documents({
                "user_id": user_id
            })
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get XP activities: {str(e)}")


@router.get("/role-requirements")
async def get_role_requirements():
    """Get XP requirements for each role"""
    try:
        return {
            "role_requirements": {
                "beginner": 0,
                "casual": 100,
                "paper_trader": 500
            },
            "role_progression": [
                {
                    "role": "beginner",
                    "required_xp": 0,
                    "next_role": "casual",
                    "next_role_xp": 100
                },
                {
                    "role": "casual", 
                    "required_xp": 100,
                    "next_role": "paper_trader",
                    "next_role_xp": 500
                },
                {
                    "role": "paper_trader",
                    "required_xp": 500,
                    "next_role": None,
                    "next_role_xp": None
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get role requirements: {str(e)}")


@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = 10,
    role_filter: Optional[str] = None,
    db = Depends(get_database)
):
    """Get XP leaderboard"""
    try:
        users_collection = db["users"]
        
        query = {"status": "active"}
        if role_filter:
            query["role"] = role_filter
        
        top_users = await users_collection.find(
            query,
            {"email": 1, "full_name": 1, "role": 1, "total_xp": 1}
        ).sort("total_xp", -1).limit(limit).to_list(None)
        
        return {
            "leaderboard": [{
                "rank": idx + 1,
                "user_name": user["full_name"],
                "role": user["role"],
                "total_xp": user.get("total_xp", 0),
                "user_id": str(user["_id"])  # For current user identification
            } for idx, user in enumerate(top_users)],
            "filter": {
                "role": role_filter,
                "limit": limit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {str(e)}")

@router.post("/daily-checkin")
async def daily_checkin(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Award daily login XP to user (once per day)"""
    try:
        xp_service = XPService(db)
        
        result = await xp_service.track_login(
            user_id=current_user["user_id"]
        )
        
        # If user already checked in today, return 409 Conflict
        if not result.get("success") and result.get("already_checked_in_today"):
            raise HTTPException(
                status_code=409, 
                detail={
                    "message": result.get("message", "Already checked in today"),
                    "already_checked_in_today": True,
                    "xp_earned": 0
                }
            )
        
        # If other error occurred
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process daily checkin: {result.get('error', 'Unknown error')}"
            )
        
        return {
            "success": True,
            "xp_earned": result.get("xp_awarded", 0),
            "message": result.get("message", "Daily XP awarded!"),
            "already_checked_in_today": False,
            "new_total_xp": result.get("new_total_xp", 0),
            "role_changed": result.get("role_changed", False),
            "new_role": result.get("new_role")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process daily checkin: {str(e)}")

@router.get("/activity-types")
async def get_activity_types():
    """Get all available XP activity types and their rewards"""
    try:
        # XP rewards defined directly here since we removed goals service
        xp_rewards = {
            "prediction_used": 5,
            "stock_added_watchlist": 2,
            "daily_login": 3,
            "ai_insight_viewed": 3,
            "profile_completed": 10,
            "quiz_passed": 50,
            "trading_action": 8,
            "role_upgraded": 100
        }
        
        activity_types = []
        for activity_type, xp_reward in xp_rewards.items():
            activity_types.append({
                "activity_type": activity_type,
                "xp_reward": xp_reward,
                "description": _get_activity_description(activity_type)
            })
        
        return {"activity_types": activity_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get activity types: {str(e)}")

class LearningModuleCompletionRequest(BaseModel):
    module_id: str
    module_title: str
    xp_reward: int = 50

@router.post("/learning/complete-module")
async def complete_learning_module(
    request: LearningModuleCompletionRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Mark a learning module as completed and award XP"""
    try:
        xp_service = XPService(db)
        
        # Check if module was already completed by this user
        existing_completion = await db.xp_activities.find_one({
            "user_id": current_user["user_id"],
            "activity_type": "learning_module_completed",
            "related_entity_id": request.module_id
        })
        
        if existing_completion:
            return {
                "success": False,
                "message": "Module already completed",
                "already_completed": True,
                "xp_earned": 0
            }
        
        result = await xp_service.track_learning_module_completion(
            user_id=current_user["user_id"],
            module_id=request.module_id,
            module_title=request.module_title,
            custom_xp=request.xp_reward
        )
        
        return {
            "success": True,
            "xp_earned": result.get("xp_awarded", 0),
            "message": f"Completed '{request.module_title}' - Earned {result.get('xp_awarded', 0)} XP!",
            "new_total_xp": result.get("new_total_xp", 0),
            "role_changed": result.get("role_changed", False),
            "new_role": result.get("new_role")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete learning module: {str(e)}")

@router.get("/learning/progress")
async def get_learning_progress(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get user's learning module completion progress"""
    try:
        # Get all completed learning modules for this user
        completed_modules = await db.xp_activities.find({
            "user_id": current_user["user_id"],
            "activity_type": "learning_module_completed"
        }).to_list(length=None)
        
        completed_module_ids = [activity["related_entity_id"] for activity in completed_modules]
        
        # Calculate total learning XP earned
        total_learning_xp = sum(activity["xp_earned"] for activity in completed_modules)
        
        return {
            "user_id": current_user["user_id"],
            "completed_modules": completed_module_ids,
            "total_modules_completed": len(completed_module_ids),
            "total_learning_xp": total_learning_xp,
            "completion_history": [{
                "module_id": activity["related_entity_id"],
                "module_title": activity["activity_description"].replace("Completed learning module: ", ""),
                "xp_earned": activity["xp_earned"],
                "completed_at": activity["earned_at"].isoformat()
            } for activity in completed_modules]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get learning progress: {str(e)}")

@router.post("/sync-role")
async def sync_user_role(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Synchronize user's role in database with their current XP total"""
    try:
        xp_service = XPService(db)
        
        result = await xp_service.sync_user_role(
            user_id=current_user["user_id"]
        )
        
        return {
            "success": result.get("success", False),
            "role_updated": result.get("role_updated", False),
            "previous_role": result.get("previous_role"),
            "new_role": result.get("new_role"),
            "current_role": result.get("current_role", result.get("new_role")),
            "current_xp": result.get("current_xp", 0),
            "message": result.get("message", "Role synchronization completed")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync user role: {str(e)}")

def _get_activity_description(activity_type: str) -> str:
    """Get human-readable description for activity types"""
    descriptions = {
        "prediction_used": "Generate stock price predictions",
        "stock_added_watchlist": "Add stocks to your watchlist",
        "daily_login": "Log in daily to the app",
        "ai_insight_viewed": "View AI trading recommendations",
        "profile_completed": "Complete your user profile",
        "quiz_passed": "Pass knowledge assessment quizzes",
        "trading_action": "Execute paper trading transactions",
        "role_upgraded": "Advance to a higher user role",
        "learning_module_completed": "Complete learning modules"
    }
    return descriptions.get(activity_type, "Unknown activity")
