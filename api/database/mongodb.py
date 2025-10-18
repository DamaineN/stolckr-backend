"""
MongoDB connection and database utilities using Motor (async MongoDB driver)
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class MongoDB:
    """MongoDB connection manager"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(
                settings.mongodb_connection_string,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=1
            )
            
            # Test the connection
            await self.client.admin.command('ping')
            
            # Get database
            self.database = self.client[settings.mongodb_database_name]
            
            # Create indexes
            await self._create_indexes()
            
            logger.info("Connected to MongoDB successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create necessary indexes for better performance"""
        try:
            # Users collection indexes
            await self.database.users.create_index("email", unique=True)
            await self.database.users.create_index("created_at")
            
            # Stock info indexes
            await self.database.stock_info.create_index("symbol", unique=True)
            await self.database.stock_info.create_index("sector")
            
            # Stock prices indexes
            await self.database.stock_prices.create_index([("symbol", 1), ("date", -1)])
            await self.database.stock_prices.create_index("date")
            
            # Predictions indexes  
            await self.database.predictions.create_index([("user_id", 1), ("created_at", -1)])
            await self.database.predictions.create_index([("symbol", 1), ("created_at", -1)])
            await self.database.predictions.create_index("status")
            
            # Portfolios indexes
            await self.database.portfolios.create_index("user_id")
            await self.database.portfolios.create_index("created_at")
            
            # Audit logs indexes
            await self.database.audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
            await self.database.audit_logs.create_index("action")
            await self.database.audit_logs.create_index("timestamp")
            
            # API usage indexes
            await self.database.api_usage.create_index([("user_id", 1), ("timestamp", -1)])
            await self.database.api_usage.create_index("endpoint")
            await self.database.api_usage.create_index("timestamp")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Some indexes might already exist: {str(e)}")
    
    def get_collection(self, collection_name: str):
        """Get a collection from the database"""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database[collection_name]

# Global MongoDB instance
mongodb = MongoDB()

# Dependency to get database
async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance"""
    if mongodb.database is None:
        raise RuntimeError("Database not connected")
    return mongodb.database

# Database service classes
class UserService:
    """User-related database operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.users
    
    async def create_user(self, user_data: dict) -> str:
        """Create a new user"""
        result = await self.collection.insert_one(user_data)
        return str(result.inserted_id)
    
    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email"""
        return await self.collection.find_one({"email": email})
    
    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID - handles both ObjectId and string formats"""
        from bson import ObjectId
        
        # Try ObjectId format first
        if ObjectId.is_valid(user_id):
            try:
                user_doc = await self.collection.find_one({"_id": ObjectId(user_id)})
                if user_doc:
                    return user_doc
            except:
                pass
        
        # If not found, try string format
        return await self.collection.find_one({"_id": user_id})
    
    async def update_user(self, user_id: str, update_data: dict) -> bool:
        """Update user data - handles both ObjectId and string formats"""
        from bson import ObjectId
        from datetime import datetime, timezone
        
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Try ObjectId format first
        if ObjectId.is_valid(user_id):
            try:
                result = await self.collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": update_data}
                )
                if result.modified_count > 0:
                    return True
            except:
                pass
        
        # If not successful, try string format
        result = await self.collection.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by setting status)"""
        return await self.update_user(user_id, {"status": "inactive"})

class StockService:
    """Stock-related database operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.info_collection = db.stock_info
        self.prices_collection = db.stock_prices
    
    async def save_stock_info(self, stock_data: dict) -> str:
        """Save stock information"""
        # Upsert stock info
        result = await self.info_collection.update_one(
            {"symbol": stock_data["symbol"]},
            {"$set": stock_data},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else stock_data["symbol"]
    
    async def save_stock_prices(self, prices_data: list) -> int:
        """Save historical stock prices"""
        if not prices_data:
            return 0
            
        # Use upsert to avoid duplicates
        operations = []
        for price in prices_data:
            operations.append({
                "update_one": {
                    "filter": {"symbol": price["symbol"], "date": price["date"]},
                    "update": {"$set": price},
                    "upsert": True
                }
            })
        
        if operations:
            result = await self.prices_collection.bulk_write(operations)
            return result.upserted_count + result.modified_count
        return 0
    
    async def get_stock_prices(self, symbol: str, start_date=None, end_date=None, limit: int = 1000):
        """Get stock prices for a symbol"""
        filter_query = {"symbol": symbol}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            filter_query["date"] = date_filter
        
        cursor = self.prices_collection.find(filter_query).sort("date", -1).limit(limit)
        return await cursor.to_list(length=limit)

class PredictionService:
    """Prediction-related database operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.predictions
    
    async def save_prediction(self, prediction_data: dict) -> str:
        """Save prediction result"""
        result = await self.collection.insert_one(prediction_data)
        return str(result.inserted_id)
    
    async def get_user_predictions(self, user_id: str, limit: int = 50):
        """Get predictions for a user"""
        from bson import ObjectId
        cursor = self.collection.find(
            {"user_id": ObjectId(user_id)}
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_symbol_predictions(self, symbol: str, limit: int = 50):
        """Get predictions for a symbol"""
        cursor = self.collection.find(
            {"symbol": symbol}
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

class AuditService:
    """Audit logging database operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.audit_logs
    
    async def log_action(self, log_data: dict) -> str:
        """Log an action"""
        result = await self.collection.insert_one(log_data)
        return str(result.inserted_id)
    
    async def get_user_logs(self, user_id: str, limit: int = 100):
        """Get audit logs for a user"""
        from bson import ObjectId
        cursor = self.collection.find(
            {"user_id": ObjectId(user_id)}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
