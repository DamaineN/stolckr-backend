"""
Simple XP Tracking Service
Awards XP for user actions and handles automatic role progression
"""
from datetime import datetime, timezone, date
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from api.database.mongodb_models import UserRole, XPActivityType


class XPService:
    """Simple XP tracking and role progression service"""
    
    # XP rewards for different actions
    XP_REWARDS = {
        XPActivityType.DAILY_LOGIN: 10,
        XPActivityType.PREDICTION_USED: 25,
        XPActivityType.STOCK_ADDED_WATCHLIST: 15,
        XPActivityType.AI_INSIGHT_VIEWED: 20,
        XPActivityType.TRADING_ACTION: 30,
        XPActivityType.PROFILE_COMPLETED: 50,
        XPActivityType.QUIZ_PASSED: 100,
        "historical_data_viewed": 15,  # Custom action
        "dashboard_viewed": 5,
        "portfolio_updated": 20,
        "learning_module_completed": 50,  # Learning Hub module completion
    }
    
    # XP thresholds for role progression
    ROLE_THRESHOLDS = {
        UserRole.BEGINNER: 0,      # Starting role
        UserRole.CASUAL: 100,      # Need 100 XP to become Casual
        UserRole.PAPER_TRADER: 500  # Need 500 XP to become Paper Trader
    }
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.users_collection = self.db.users
        self.xp_activities_collection = self.db.xp_activities
    
    async def award_xp(self, user_id: str, activity_type: str, 
                      xp_amount: Optional[int] = None,
                      description: Optional[str] = None,
                      related_entity: Optional[str] = None) -> Dict[str, Any]:
        """
        Award XP to a user for performing an action
        
        Args:
            user_id: User's ObjectId as string
            activity_type: Type of activity (from XPActivityType or custom string)
            xp_amount: Custom XP amount (uses default if None)
            description: Optional description of the activity
            related_entity: Optional related entity (e.g., stock symbol)
        
        Returns:
            Dict with XP awarded, new total, role change info
        """
        try:
            # Get XP amount
            if xp_amount is None:
                xp_amount = self.XP_REWARDS.get(activity_type, 10)  # Default 10 XP
            
            # Get current user data - try both ObjectId and string lookups
            user_doc = None
            
            # First try as ObjectId if it's a valid ObjectId
            if ObjectId.is_valid(user_id):
                try:
                    user_doc = await self.users_collection.find_one({"_id": ObjectId(user_id)})
                except:
                    pass
            
            # If not found, try as string
            if not user_doc:
                user_doc = await self.users_collection.find_one({"_id": user_id})
                
            if not user_doc:
                raise ValueError(f"User {user_id} not found")
            
            current_xp = user_doc.get("total_xp", 0)
            current_role = user_doc.get("role", UserRole.BEGINNER)
            
            # Calculate new XP total
            new_xp_total = current_xp + xp_amount
            
            # Check for role progression
            new_role = self._calculate_role_from_xp(new_xp_total)
            role_changed = new_role != current_role
            
            # Record XP activity
            activity_record = {
                "user_id": user_id,  # Use string ID directly
                "activity_type": activity_type,
                "activity_description": description or f"Earned {xp_amount} XP for {activity_type}",
                "xp_earned": xp_amount,
                "related_entity_id": related_entity,
                "earned_at": datetime.now(timezone.utc)
            }
            await self.xp_activities_collection.insert_one(activity_record)
            
            # Update user's XP and role
            update_data = {
                "total_xp": new_xp_total,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if role_changed:
                update_data["role"] = new_role
                # Add to role progression history
                role_change_entry = {
                    "from_role": current_role,
                    "to_role": new_role,
                    "xp_at_change": new_xp_total,
                    "changed_at": datetime.now(timezone.utc)
                }
                await self.users_collection.update_one(
                    {"_id": user_id},  # Use string ID directly
                    {
                        "$set": update_data,
                        "$push": {"role_progression_history": role_change_entry}
                    }
                )
            else:
                await self.users_collection.update_one(
                    {"_id": user_id},  # Use string ID directly
                    {"$set": update_data}
                )
            
            return {
                "success": True,
                "xp_awarded": xp_amount,
                "previous_xp": current_xp,
                "new_total_xp": new_xp_total,
                "activity_type": activity_type,
                "role_changed": role_changed,
                "previous_role": current_role,
                "new_role": new_role,
                "next_role_threshold": self._get_next_role_threshold(new_xp_total)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "xp_awarded": 0
            }
    
    def _calculate_role_from_xp(self, total_xp: int) -> UserRole:
        """Calculate user role based on total XP"""
        if total_xp >= self.ROLE_THRESHOLDS[UserRole.PAPER_TRADER]:
            return UserRole.PAPER_TRADER
        elif total_xp >= self.ROLE_THRESHOLDS[UserRole.CASUAL]:
            return UserRole.CASUAL
        else:
            return UserRole.BEGINNER
    
    def _get_next_role_threshold(self, current_xp: int) -> Optional[Dict[str, Any]]:
        """Get information about the next role threshold"""
        if current_xp < self.ROLE_THRESHOLDS[UserRole.CASUAL]:
            return {
                "next_role": UserRole.CASUAL,
                "xp_needed": self.ROLE_THRESHOLDS[UserRole.CASUAL] - current_xp,
                "total_needed": self.ROLE_THRESHOLDS[UserRole.CASUAL]
            }
        elif current_xp < self.ROLE_THRESHOLDS[UserRole.PAPER_TRADER]:
            return {
                "next_role": UserRole.PAPER_TRADER,
                "xp_needed": self.ROLE_THRESHOLDS[UserRole.PAPER_TRADER] - current_xp,
                "total_needed": self.ROLE_THRESHOLDS[UserRole.PAPER_TRADER]
            }
        else:
            return None  # Already at max role
    
    async def get_user_xp_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user's XP statistics and progression info"""
        try:
            # Try both ObjectId and string lookups for compatibility
            user_doc = None
            
            # First try as ObjectId if it's a valid ObjectId
            if ObjectId.is_valid(user_id):
                try:
                    user_doc = await self.users_collection.find_one({"_id": ObjectId(user_id)})
                except:
                    pass
            
            # If not found, try as string (some databases store _id as string)
            if not user_doc:
                user_doc = await self.users_collection.find_one({"_id": user_id})
            
            if not user_doc:
                raise ValueError(f"User {user_id} not found")
            
            total_xp = user_doc.get("total_xp", 0)
            current_role = user_doc.get("role", UserRole.BEGINNER)
            
            # Get recent activities
            recent_activities = await self.xp_activities_collection.find(
                {"user_id": user_id}  # Use string ID directly
            ).sort("earned_at", -1).limit(10).to_list(length=10)
            
            return {
                "user_id": user_id,
                "total_xp": total_xp,
                "current_role": current_role,
                "next_role_info": self._get_next_role_threshold(total_xp),
                "role_progression_history": user_doc.get("role_progression_history", []),
                "recent_activities": [
                    {
                        "activity_type": activity.get("activity_type"),
                        "xp_earned": activity.get("xp_earned"),
                        "description": activity.get("activity_description"),
                        "earned_at": activity.get("earned_at")
                    }
                    for activity in recent_activities
                ]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_leaderboard(self, limit: int = 10) -> Dict[str, Any]:
        """Get top users by XP"""
        try:
            top_users = await self.users_collection.find(
                {"total_xp": {"$gt": 0}},
                {"email": 1, "full_name": 1, "total_xp": 1, "role": 1}
            ).sort("total_xp", -1).limit(limit).to_list(length=limit)
            
            leaderboard = []
            for i, user in enumerate(top_users, 1):
                leaderboard.append({
                    "rank": i,
                    "user_id": str(user["_id"]),
                    "full_name": user.get("full_name", "Anonymous"),
                    "email": user.get("email", "").split("@")[0] + "@***",  # Partial email for privacy
                    "total_xp": user.get("total_xp", 0),
                    "role": user.get("role", UserRole.BEGINNER)
                })
            
            return {
                "leaderboard": leaderboard,
                "total_users": len(top_users)
            }
            
        except Exception as e:
            return {"error": str(e)}

    # Convenience methods for common actions
    async def track_login(self, user_id: str) -> Dict[str, Any]:
        """Track daily login with proper daily validation"""
        try:
            # Get current user data - try both ObjectId and string lookups
            user_doc = None
            
            # First try as ObjectId if it's a valid ObjectId
            if ObjectId.is_valid(user_id):
                try:
                    user_doc = await self.users_collection.find_one({"_id": ObjectId(user_id)})
                except:
                    pass
            
            # If not found, try as string
            if not user_doc:
                user_doc = await self.users_collection.find_one({"_id": user_id})
                
            if not user_doc:
                return {
                    "success": False,
                    "error": f"User {user_id} not found",
                    "xp_awarded": 0
                }
            
            # Check if user already checked in today
            today = date.today()
            last_checkin_date = user_doc.get("last_daily_checkin_date")
            
            # Convert last_checkin_date to date if it exists
            if last_checkin_date:
                if isinstance(last_checkin_date, datetime):
                    last_checkin_date = last_checkin_date.date()
                elif isinstance(last_checkin_date, str):
                    try:
                        last_checkin_date = datetime.fromisoformat(last_checkin_date.replace('Z', '+00:00')).date()
                    except:
                        last_checkin_date = None
            
            # If user already checked in today, return early
            if last_checkin_date and last_checkin_date >= today:
                return {
                    "success": False,
                    "message": "You have already checked in today! Come back tomorrow for more XP.",
                    "xp_awarded": 0,
                    "already_checked_in_today": True
                }
            
            # Award XP and update last check-in date
            result = await self.award_xp(
                user_id=user_id,
                activity_type=XPActivityType.DAILY_LOGIN,
                description="Daily login bonus"
            )
            
            # Update last daily check-in date
            if result.get("success"):
                await self.users_collection.update_one(
                    {"_id": user_id},  # Use string ID directly
                    {
                        "$set": {
                            "last_daily_checkin_date": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                result["message"] = "Daily check-in successful! Come back tomorrow for more XP."
                result["already_checked_in_today"] = False
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "xp_awarded": 0
            }
    
    async def track_prediction(self, user_id: str, symbol: str, model_type: str) -> Dict[str, Any]:
        """Track stock prediction generation"""
        return await self.award_xp(
            user_id=user_id,
            activity_type=XPActivityType.PREDICTION_USED,
            description=f"Generated {model_type} prediction for {symbol}",
            related_entity=symbol
        )
    
    async def track_watchlist_add(self, user_id: str, symbol: str) -> Dict[str, Any]:
        """Track adding stock to watchlist"""
        return await self.award_xp(
            user_id=user_id,
            activity_type=XPActivityType.STOCK_ADDED_WATCHLIST,
            description=f"Added {symbol} to watchlist",
            related_entity=symbol
        )
    
    async def track_ai_insight_view(self, user_id: str, symbol: str) -> Dict[str, Any]:
        """Track viewing AI insights"""
        return await self.award_xp(
            user_id=user_id,
            activity_type=XPActivityType.AI_INSIGHT_VIEWED,
            description=f"Viewed AI insights for {symbol}",
            related_entity=symbol
        )
    
    async def track_paper_trade(self, user_id: str, symbol: str, action: str) -> Dict[str, Any]:
        """Track paper trading action"""
        return await self.award_xp(
            user_id=user_id,
            activity_type=XPActivityType.TRADING_ACTION,
            description=f"Paper traded {action} {symbol}",
            related_entity=symbol
        )
    
    async def track_historical_data_view(self, user_id: str, symbol: str) -> Dict[str, Any]:
        """Track viewing historical data"""
        return await self.award_xp(
            user_id=user_id,
            activity_type="historical_data_viewed",
            description=f"Viewed historical data for {symbol}",
            related_entity=symbol
        )
    
    async def track_learning_module_completion(self, user_id: str, module_id: str, module_title: str, custom_xp: Optional[int] = None) -> Dict[str, Any]:
        """Track learning module completion"""
        return await self.award_xp(
            user_id=user_id,
            activity_type="learning_module_completed",
            xp_amount=custom_xp,  # Allow custom XP from module definition
            description=f"Completed learning module: {module_title}",
            related_entity=module_id
        )
    
    async def sync_user_role(self, user_id: str) -> Dict[str, Any]:
        """Synchronize user's role in database with their current XP total"""
        try:
            # Get current user data - try both ObjectId and string lookups
            user_doc = None
            
            # First try as ObjectId if it's a valid ObjectId
            if ObjectId.is_valid(user_id):
                try:
                    user_doc = await self.users_collection.find_one({"_id": ObjectId(user_id)})
                except:
                    pass
            
            # If not found, try as string
            if not user_doc:
                user_doc = await self.users_collection.find_one({"_id": user_id})
                
            if not user_doc:
                raise ValueError(f"User {user_id} not found")
            
            current_xp = user_doc.get("total_xp", 0)
            stored_role = user_doc.get("role", UserRole.BEGINNER)
            
            # Calculate what role should be based on XP
            calculated_role = self._calculate_role_from_xp(current_xp)
            
            # Check if role needs updating
            if stored_role != calculated_role:
                # Update user's role in database
                update_data = {
                    "role": calculated_role,
                    "updated_at": datetime.now(timezone.utc)
                }
                
                # Add to role progression history
                role_change_entry = {
                    "from_role": stored_role,
                    "to_role": calculated_role,
                    "xp_at_change": current_xp,
                    "changed_at": datetime.now(timezone.utc),
                    "sync_correction": True  # Mark this as a sync correction
                }
                
                await self.users_collection.update_one(
                    {"_id": user_id},  # Use string ID directly
                    {
                        "$set": update_data,
                        "$push": {"role_progression_history": role_change_entry}
                    }
                )
                
                return {
                    "success": True,
                    "role_updated": True,
                    "previous_role": stored_role,
                    "new_role": calculated_role,
                    "current_xp": current_xp,
                    "message": f"Role synchronized from {stored_role} to {calculated_role}"
                }
            else:
                return {
                    "success": True,
                    "role_updated": False,
                    "current_role": stored_role,
                    "current_xp": current_xp,
                    "message": "Role already synchronized"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
