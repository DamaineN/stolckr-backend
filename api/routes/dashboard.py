"""
Real-time Dashboard API Routes
Provides real-time user statistics and dashboard data
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from api.auth.utils import get_current_user
from api.database.mongodb import get_database
from api.services.xp_service import XPService

def calculate_activity_streak(recent_logins: list) -> tuple[int, int, str]:
    """Calculate current and longest activity streaks from login data
    
    Args:
        recent_logins: List of XP activity records for daily_login activities
        
    Returns:
        tuple: (current_streak, longest_streak, last_activity_date)
    """
    current_streak = 0
    longest_streak = 0
    last_activity = None
    
    if not recent_logins:
        return current_streak, longest_streak, last_activity
    
    # Convert login dates to unique days
    login_dates = []
    for login in recent_logins:
        login_date = login["earned_at"].date()
        if login_date not in login_dates:
            login_dates.append(login_date)
    
    # Sort dates in descending order (most recent first)
    login_dates.sort(reverse=True)
    last_activity = login_dates[0].isoformat() if login_dates else None
    
    # Calculate current streak
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    
    # Start checking from today or yesterday
    if login_dates and login_dates[0] == today:
        # Logged in today, start streak from today
        current_streak = 1
        check_date = today - timedelta(days=1)
    elif login_dates and login_dates[0] == yesterday:
        # Logged in yesterday but not today, start streak from yesterday
        current_streak = 1
        check_date = yesterday - timedelta(days=1)
    else:
        # Haven't logged in today or yesterday, no current streak
        current_streak = 0
        check_date = None
    
    # Continue counting consecutive days backwards
    if check_date is not None:
        for date in login_dates[1:]:  # Skip the first date we already counted
            if date == check_date:
                current_streak += 1
                check_date = check_date - timedelta(days=1)
            else:
                break
    
    # Calculate longest streak
    if len(login_dates) > 1:
        max_streak = 0
        current_longest = 1
        
        for i in range(1, len(login_dates)):
            # Check if consecutive days
            if login_dates[i-1] - login_dates[i] == timedelta(days=1):
                current_longest += 1
            else:
                max_streak = max(max_streak, current_longest)
                current_longest = 1
        
        longest_streak = max(max_streak, current_longest)
    elif len(login_dates) == 1:
        longest_streak = 1
    else:
        longest_streak = 0
    
    return current_streak, longest_streak, last_activity

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get comprehensive dashboard statistics for the current user"""
    try:
        # Award XP for viewing dashboard
        xp_service = XPService(db)
        await xp_service.award_xp(
            user_id=current_user["user_id"],
            activity_type="dashboard_viewed",
            description="Viewed dashboard statistics"
        )
        
        # Get XP stats and user info directly
        xp_stats = await xp_service.get_user_xp_stats(current_user["user_id"])
        
        # Get basic user and prediction data
        user_doc = await db.users.find_one({"_id": ObjectId(current_user["user_id"])})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
            
        predictions_made = await db.predictions.count_documents({"user_id": ObjectId(current_user["user_id"])})
        
        # Get recent predictions
        recent_predictions = await db.predictions.find({
            "user_id": ObjectId(current_user["user_id"])
        }).sort("created_at", -1).limit(5).to_list(length=5)
        
        # Format predictions data with frontend-expected field names
        formatted_predictions = []
        for pred in recent_predictions:
            formatted_predictions.append({
                "id": str(pred["_id"]),
                "symbol": pred.get("symbol", "N/A"),
                "model": pred.get("prediction_type", pred.get("model", "LSTM")),  # Map to 'model'
                "prediction": pred.get("target_price", pred.get("predicted_price")),  # Map to 'prediction'
                "predicted_price": pred.get("target_price", pred.get("predicted_price")),  # Also provide as fallback
                "date": pred.get("created_at").isoformat() if pred.get("created_at") else None,  # Map to 'date'
                "created_at": pred.get("created_at").isoformat() if pred.get("created_at") else None,  # Also keep original
                "confidence": pred.get("confidence", 0.95),  # Default confidence if missing
                "status": pred.get("status", "pending"),
                # Legacy fields for compatibility
                "prediction_type": pred.get("prediction_type", "unknown")
            })
        
        stats = {
            "total_predictions": predictions_made,
            "recent_predictions": formatted_predictions,
            "user_role": user_doc.get("role", "beginner"),
            "xp_info": {
                "total_xp": xp_stats.get("total_xp", 0),
                "current_role": xp_stats.get("current_role", "beginner"),
                "next_role_info": xp_stats.get("next_role_info")
            }
        }
        
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")

@router.get("/activity")
async def get_activity_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get user activity statistics for profile page"""
    try:
        # Get XP-based activity data directly
        xp_service = XPService(db)
        xp_stats = await xp_service.get_user_xp_stats(current_user["user_id"])
        
        if "error" in xp_stats:
            raise HTTPException(status_code=500, detail=f"XP stats error: {xp_stats['error']}")
        
        # Get user data for additional info - handle both ObjectId and string formats
        user_id = current_user["user_id"]
        user_doc = None
        
        # Try ObjectId format first
        if ObjectId.is_valid(user_id):
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        
        # If not found, try string format
        if not user_doc:
            user_doc = await db.users.find_one({"_id": user_id})
            
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get actual counts from database - use same flexible approach
        user_id_obj = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        predictions_made = await db.predictions.count_documents({"user_id": user_id_obj})
        
        watchlist_doc = await db.watchlists.find_one({"user_id": user_id_obj})
        stocks_watched = len(watchlist_doc.get("items", [])) if watchlist_doc else 0
        
        # Calculate activity streak from XP activities - proper implementation
        recent_logins = await db.xp_activities.find({
            "user_id": user_id,  # Use string format for XP activities
            "activity_type": "daily_login"
        }).sort("earned_at", -1).limit(100).to_list(length=100)  # Get more records for proper calculation
        
        current_streak, longest_streak, last_activity = calculate_activity_streak(recent_logins)
        
        return {
            "predictions_made": predictions_made,
            "stocks_watched": stocks_watched,
            "last_login": user_doc.get("last_login").isoformat() if user_doc.get("last_login") else None,
            "account_created": user_doc.get("created_at").isoformat() if user_doc.get("created_at") else None,
            "activity_streak": {
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "last_activity": last_activity
            },
            "xp_info": {
                "total_xp": xp_stats.get("total_xp", 0),
                "current_role": xp_stats.get("current_role", "beginner"),
                "active_goals": 0,  # No goals system implemented yet
                "completed_goals": 0  # No goals system implemented yet
            },
            "user_role": user_doc.get("role", "beginner"),
            "total_xp": xp_stats.get("total_xp", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get activity stats: {str(e)}")

@router.get("/real-time")
async def get_real_time_metrics(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get real-time metrics that update frequently"""
    try:
        # Get basic real-time metrics
        user_id = ObjectId(current_user["user_id"])
        
        # Count predictions made today
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        predictions_today = await db.predictions.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": today}
        })
        
        # Get total XP
        xp_service = XPService(db)
        xp_stats = await xp_service.get_user_xp_stats(current_user["user_id"])
        
        return {
            "predictions_today": predictions_today,
            "total_xp": xp_stats.get("total_xp", 0),
            "current_role": xp_stats.get("current_role", "beginner"),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get real-time metrics: {str(e)}")

@router.get("/predictions/recent")
async def get_recent_predictions(
    limit: Optional[int] = 10,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get recent predictions with detailed information"""
    try:
        # Get recent predictions directly from database
        user_id = ObjectId(current_user["user_id"])
        
        # Get total count
        total_count = await db.predictions.count_documents({"user_id": user_id})
        
        # Get recent predictions
        recent_predictions = await db.predictions.find({
            "user_id": user_id
        }).sort("created_at", -1).limit(limit).to_list(length=limit)
        
        # Format predictions data with frontend-expected field names
        formatted_predictions = []
        for pred in recent_predictions:
            formatted_predictions.append({
                "id": str(pred["_id"]),
                "symbol": pred.get("symbol", "N/A"),
                "model": pred.get("prediction_type", pred.get("model", "LSTM")),  # Map to 'model'
                "prediction": pred.get("target_price", pred.get("predicted_price")),  # Map to 'prediction'
                "predicted_price": pred.get("target_price", pred.get("predicted_price")),  # Also provide as fallback
                "date": pred.get("created_at").isoformat() if pred.get("created_at") else None,  # Map to 'date'
                "created_at": pred.get("created_at").isoformat() if pred.get("created_at") else None,  # Also keep original
                "confidence": pred.get("confidence", 0.95),  # Default confidence if missing
                "status": pred.get("status", "pending"),
                # Legacy fields for compatibility
                "prediction_type": pred.get("prediction_type", "unknown"),
                "target_price": pred.get("target_price")
            })
        
        return {
            "predictions": formatted_predictions,
            "total_count": total_count,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent predictions: {str(e)}")

@router.get("/summary")
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get a lightweight summary for dashboard header/cards"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Get basic stats efficiently
        total_predictions = await db.predictions.count_documents({"user_id": user_id})
        
        # Get watchlist items count
        watchlist_doc = await db.watchlists.find_one({"user_id": user_id})
        watchlist_items = len(watchlist_doc.get("items", [])) if watchlist_doc else 0
        
        # Return lightweight summary
        return {
            "total_predictions": total_predictions,
            "model_accuracy": 0.0,  # Placeholder - would need actual calculation
            "watchlist_items": watchlist_items, 
            "active_models": 1,  # Placeholder - would track active ML models
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard summary: {str(e)}")

@router.get("/activity-streak")
async def get_activity_streak(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get user activity streak information"""
    try:
        user_id = ObjectId(current_user["user_id"])
        xp_service = XPService(db)
        
        # Calculate activity streak from XP activities using helper function
        recent_logins = await db.xp_activities.find({
            "user_id": current_user["user_id"],  # Use string format for XP activities consistency
            "activity_type": "daily_login"
        }).sort("earned_at", -1).limit(100).to_list(length=100)
        
        current_streak, longest_streak, last_activity = calculate_activity_streak(recent_logins)
        
        # Get XP info
        xp_stats = await xp_service.get_user_xp_stats(current_user["user_id"])
        
        return {
            "streak_info": {
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "last_activity": last_activity
            },
            "xp_info": {
                "total_xp": xp_stats.get("total_xp", 0),
                "current_role": xp_stats.get("current_role", "beginner")
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get activity streak: {str(e)}")

@router.post("/refresh")
async def refresh_dashboard_data(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Force refresh of dashboard data (useful for testing)"""
    try:
        # Simply return success - actual refresh would involve cache clearing in a real system
        user_id = ObjectId(current_user["user_id"])
        
        # Get some basic current stats to verify the refresh
        total_predictions = await db.predictions.count_documents({"user_id": user_id})
        
        xp_service = XPService(db)
        xp_stats = await xp_service.get_user_xp_stats(current_user["user_id"])
        
        return {
            "success": True,
            "message": "Dashboard data refreshed successfully",
            "data": {
                "total_predictions": total_predictions,
                "total_xp": xp_stats.get("total_xp", 0),
                "current_role": xp_stats.get("current_role", "beginner")
            },
            "refreshed_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh dashboard data: {str(e)}")

@router.get("/xp")
async def get_xp_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get detailed XP and role progression statistics"""
    try:
        xp_service = XPService(db)
        xp_stats = await xp_service.get_user_xp_stats(current_user["user_id"])
        
        return {
            "success": True,
            "data": xp_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get XP stats: {str(e)}")

@router.get("/leaderboard")
async def get_xp_leaderboard(
    limit: Optional[int] = 10,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get XP leaderboard"""
    try:
        xp_service = XPService(db)
        leaderboard = await xp_service.get_leaderboard(limit)
        
        return {
            "success": True,
            "data": leaderboard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {str(e)}")

@router.get("/health")
async def dashboard_health_check():
    """Health check endpoint for dashboard API"""
    return {
        "status": "healthy",
        "service": "dashboard-api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
