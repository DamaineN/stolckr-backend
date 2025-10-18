"""
WebSocket API routes for real-time updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Optional
import json
import asyncio
import logging

from api.websocket.manager import manager
from api.routes.auth import get_user_from_token

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time stock updates"""
    
    # TODO: Add proper authentication for WebSocket connections
    # For now, we'll trust the user_id parameter
    
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "subscribe":
                # Subscribe to stock updates
                symbol = message.get("symbol")
                if symbol:
                    await manager.subscribe_to_stock(user_id, symbol)
                
            elif message_type == "unsubscribe":
                # Unsubscribe from stock updates
                symbol = message.get("symbol")
                if symbol:
                    await manager.unsubscribe_from_stock(user_id, symbol)
            
            elif message_type == "ping":
                # Respond to ping for connection health check
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": message.get("timestamp")
                }, user_id)
            
            elif message_type == "get_subscriptions":
                # Send current subscriptions to user
                subscriptions = list(manager.user_subscriptions.get(user_id, set()))
                await manager.send_personal_message({
                    "type": "current_subscriptions",
                    "subscriptions": subscriptions
                }, user_id)
            
            else:
                # Unknown message type
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }, user_id)
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)

@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics (admin endpoint)"""
    # TODO: Add admin authentication
    return manager.get_connection_stats()

# Background task to simulate real-time stock price updates
async def simulate_stock_updates():
    """Simulate real-time stock price updates (for testing)"""
    import random
    
    # Sample stocks with mock prices
    stocks = {
        "AAPL": 150.0,
        "GOOGL": 2500.0,
        "MSFT": 350.0,
        "TSLA": 800.0,
        "NVDA": 900.0
    }
    
    while True:
        for symbol, base_price in stocks.items():
            # Generate random price change
            change_percent = random.uniform(-0.02, 0.02)  # -2% to +2%
            new_price = base_price * (1 + change_percent)
            
            stock_data = {
                "price": round(new_price, 2),
                "change": round(new_price - base_price, 2),
                "change_percent": round(change_percent * 100, 2),
                "volume": random.randint(1000000, 5000000),
                "high": round(new_price * 1.01, 2),
                "low": round(new_price * 0.99, 2)
            }
            
            # Update base price for next iteration
            stocks[symbol] = new_price
            
            # Broadcast update to all subscribers
            await manager.broadcast_stock_update(symbol, stock_data)
        
        # Wait 5 seconds before next update
        await asyncio.sleep(5)

# Background task to simulate portfolio updates
async def simulate_portfolio_updates():
    """Simulate real-time portfolio value updates"""
    while True:
        # Send portfolio updates to all connected users
        for user_id in manager.active_connections.keys():
            portfolio_data = {
                "total_value": round(random.uniform(18000, 22000), 2),
                "daily_change": round(random.uniform(-500, 500), 2),
                "daily_change_percent": round(random.uniform(-2.5, 2.5), 2),
                "positions_count": random.randint(3, 8),
                "cash_balance": round(random.uniform(1000, 5000), 2)
            }
            
            await manager.broadcast_portfolio_update(user_id, portfolio_data)
        
        # Wait 30 seconds before next update
        await asyncio.sleep(30)

# Background task for AI predictions
async def simulate_prediction_updates():
    """Simulate new AI predictions"""
    import random
    
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
    
    while True:
        # Generate prediction for random stock
        symbol = random.choice(symbols)
        
        prediction_data = {
            "predicted_price": round(random.uniform(100, 1000), 2),
            "confidence": round(random.uniform(0.6, 0.95), 2),
            "model_used": random.choice(["lstm", "arima", "ensemble"]),
            "prediction_horizon": "7 days",
            "key_factors": [
                "Strong technical momentum",
                "Positive earnings outlook",
                "Sector rotation trends"
            ]
        }
        
        await manager.broadcast_prediction_update(symbol, prediction_data)
        
        # Wait 2 minutes before next prediction
        await asyncio.sleep(120)

# Start background tasks (these would typically be started in main.py)
async def start_background_tasks():
    """Start all background tasks for WebSocket updates"""
    tasks = [
        asyncio.create_task(simulate_stock_updates()),
        asyncio.create_task(simulate_portfolio_updates()),
        asyncio.create_task(simulate_prediction_updates())
    ]
    return tasks
