"""
Watchlist API routes
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime, timezone

from api.auth.utils import get_current_user
from api.database.mongodb import get_database, UserService
from api.database.mongodb_models import WatchlistItem, Watchlist
from api.collectors.yahoo_finance import YahooFinanceCollector
from api.services.xp_service import XPService

router = APIRouter()

@router.get("/watchlist")
async def get_user_watchlist(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get current user's watchlist"""
    try:
        from bson import ObjectId
        
        # Handle both ObjectId and string user ID formats
        user_id = current_user["user_id"]
        if ObjectId.is_valid(user_id):
            user_id_query = ObjectId(user_id)
        else:
            user_id_query = user_id
        
        # Get user's watchlist from database
        watchlist = await db.watchlists.find_one({"user_id": user_id_query})
        
        if not watchlist:
            # Create default watchlist if none exists
            default_watchlist = {
                "user_id": user_id_query,
                "name": "My Watchlist",
                "items": [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            await db.watchlists.insert_one(default_watchlist)
            return {
                "items": [],
                "count": 0,
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            }
        
        # Get current prices for watchlist items
        collector = YahooFinanceCollector()
        updated_items = []
        
        for item in watchlist.get("items", []):
            try:
                # Get current stock info
                stock_info = await collector.get_stock_info(item["symbol"])
                current_price = stock_info.get('currentPrice', stock_info.get('regularMarketPrice', 0))
                previous_close = stock_info.get('previousClose', current_price)
                
                change = current_price - previous_close
                change_percent = (change / previous_close * 100) if previous_close > 0 else 0
                
                updated_items.append({
                    "symbol": item["symbol"],
                    "name": stock_info.get('longName', stock_info.get('shortName', item.get("notes", item["symbol"]))),
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "addedAt": item["added_at"].isoformat() if isinstance(item["added_at"], datetime) else item["added_at"]
                })
            except:
                # If can't get current price, use stored data
                updated_items.append({
                    "symbol": item["symbol"],
                    "name": item.get("notes", item["symbol"]),
                    "price": 0,
                    "change": 0,
                    "changePercent": 0,
                    "addedAt": item["added_at"].isoformat() if isinstance(item["added_at"], datetime) else item["added_at"]
                })
        
        return {
            "items": updated_items,
            "count": len(updated_items),
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching watchlist: {str(e)}"
        )

@router.post("/watchlist")
async def add_to_watchlist(
    item: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Add a stock to user's watchlist"""
    try:
        from bson import ObjectId
        symbol = item.get("symbol", "").upper().strip()
        
        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stock symbol is required"
            )
        
        # Validate stock symbol by trying to fetch real data
        collector = YahooFinanceCollector()
        try:
            stock_info = await collector.get_stock_info(symbol)
            if not stock_info or not stock_info.get('symbol'):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Stock symbol '{symbol}' not found or doesn't exist"
                )
            current_price = stock_info.get('currentPrice', stock_info.get('regularMarketPrice', 0))
            company_name = stock_info.get('longName', stock_info.get('shortName', symbol))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unable to validate stock symbol '{symbol}'. It may not exist."
            )
        
        # Handle both ObjectId and string user ID formats
        user_id = current_user["user_id"]
        if ObjectId.is_valid(user_id):
            user_id_query = ObjectId(user_id)
        else:
            user_id_query = user_id
        
        # Get or create user's watchlist
        watchlist = await db.watchlists.find_one({"user_id": user_id_query})
        
        if not watchlist:
            # Create new watchlist
            watchlist = {
                "user_id": user_id_query,
                "name": "My Watchlist",
                "items": [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            await db.watchlists.insert_one(watchlist)
        
        # Check if symbol already exists in watchlist
        existing_symbols = [item["symbol"] for item in watchlist.get("items", [])]
        if symbol in existing_symbols:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock '{symbol}' is already in your watchlist"
            )
        
        # Create watchlist item
        watchlist_item_db = {
            "symbol": symbol,
            "added_at": datetime.now(timezone.utc),
            "notes": company_name,
            "target_price": None,
            "stop_loss": None
        }
        
        # Add to watchlist
        await db.watchlists.update_one(
            {"user_id": user_id_query},
            {
                "$push": {"items": watchlist_item_db},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        
        # Award XP for adding to watchlist
        try:
            xp_service = XPService(db)
            await xp_service.track_watchlist_add(
                user_id=current_user["user_id"],
                symbol=symbol
            )
        except Exception as xp_error:
            # Don't fail the watchlist operation if XP tracking fails
            print(f"XP tracking failed: {xp_error}")
        
        # Return the added item with current price info
        previous_close = stock_info.get('previousClose', current_price)
        change = current_price - previous_close
        change_percent = (change / previous_close * 100) if previous_close > 0 else 0
        
        return {
            "symbol": symbol,
            "name": company_name,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "addedAt": watchlist_item_db["added_at"].isoformat(),
            "message": f"Successfully added {symbol} to your watchlist"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding to watchlist: {str(e)}"
        )

@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(
    symbol: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Remove a stock from user's watchlist"""
    try:
        from bson import ObjectId
        
        # Handle both ObjectId and string user ID formats
        user_id = current_user["user_id"]
        if ObjectId.is_valid(user_id):
            user_id_query = ObjectId(user_id)
        else:
            user_id_query = user_id
            
        symbol = symbol.upper().strip()
        
        # Remove from watchlist
        result = await db.watchlists.update_one(
            {"user_id": user_id_query},
            {
                "$pull": {"items": {"symbol": symbol}},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock '{symbol}' not found in your watchlist"
            )
        
        return {"message": f"Successfully removed {symbol} from watchlist"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing from watchlist: {str(e)}"
        )

@router.post("/watchlist/refresh")
async def refresh_watchlist_prices(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Refresh prices for all stocks in watchlist"""
    try:
        # In a real app, you'd update all watchlist items with current prices
        # For now, return mock refreshed data
        refreshed_items = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "price": 186.75,
                "change": 3.55,
                "changePercent": 1.94,
                "addedAt": "2024-01-15T10:30:00Z"
            }
        ]
        
        return {
            "items": refreshed_items,
            "count": len(refreshed_items),
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing watchlist: {str(e)}"
        )

@router.get("/watchlist/stats")
async def get_watchlist_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get watchlist statistics"""
    try:
        # Mock statistics
        return {
            "totalItems": 2,
            "totalValue": 2935.80,
            "totalGain": -12.90,
            "totalGainPercent": -0.44,
            "topGainer": {
                "symbol": "AAPL",
                "changePercent": 1.26
            },
            "topLoser": {
                "symbol": "GOOGL", 
                "changePercent": -0.55
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting watchlist stats: {str(e)}"
        )