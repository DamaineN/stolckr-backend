"""
WebSocket API routes for real-time updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Optional
import json
import asyncio
import logging

from api.websocket.manager import manager

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

# Professional-grade realistic stock market simulation for demo
async def simulate_stock_updates():
    """Advanced stock market simulation with authentic trading patterns"""
    import random
    import math
    from datetime import datetime, time
    
    # Real current market prices and company data for authentic demo
    stocks = {
        "AAPL": {
            "price": 184.60,
            "prev_close": 185.50,
            "trend": 0.0015,
            "volatility": 0.018,
            "name": "Apple Inc.",
            "market_cap": 3500000000000
        },
        "GOOGL": {
            "price": 2767.65,
            "prev_close": 2750.30,
            "trend": -0.0008,
            "volatility": 0.022,
            "name": "Alphabet Inc.",
            "market_cap": 2100000000000
        },
        "MSFT": {
            "price": 429.12,
            "prev_close": 430.02,
            "trend": 0.0012,
            "volatility": 0.016,
            "name": "Microsoft Corp.",
            "market_cap": 3100000000000
        },
        "TSLA": {
            "price": 242.83,
            "prev_close": 247.14,
            "trend": -0.0025,
            "volatility": 0.035,
            "name": "Tesla Inc.",
            "market_cap": 780000000000
        },
        "NVDA": {
            "price": 139.76,
            "prev_close": 138.05,
            "trend": 0.0022,
            "volatility": 0.028,
            "name": "NVIDIA Corp.",
            "market_cap": 3400000000000
        },
        "META": {
            "price": 583.45,
            "prev_close": 574.28,
            "trend": 0.0018,
            "volatility": 0.025,
            "name": "Meta Platforms",
            "market_cap": 1500000000000
        },
        "AMZN": {
            "price": 187.92,
            "prev_close": 189.67,
            "trend": -0.0011,
            "volatility": 0.021,
            "name": "Amazon.com Inc.",
            "market_cap": 1950000000000
        },
        "NFLX": {
            "price": 701.28,
            "prev_close": 688.93,
            "trend": 0.0021,
            "volatility": 0.032,
            "name": "Netflix Inc.",
            "market_cap": 305000000000
        }
    }
    
    # Market session tracking for authentic behavior
    session_start = time(9, 30)  # NYSE opens 9:30 AM
    session_end = time(16, 0)    # NYSE closes 4:00 PM
    
    iteration = 0
    logger.info("📈 Initializing professional stock market simulation...")
    
    while True:
        current_time = datetime.now().time()
        is_market_hours = session_start <= current_time <= session_end
        
        # Market-wide sentiment factor (simulates overall market mood)
        market_sentiment = 0.5 + 0.3 * math.sin(iteration * 0.008)
        
        for symbol, data in stocks.items():
            try:
                current_price = data["price"]
                prev_close = data["prev_close"]
                trend = data["trend"]
                volatility = data["volatility"]
                
                # Advanced price modeling with realistic factors
                
                # 1. Trend continuation with natural momentum
                trend_component = trend * random.uniform(0.92, 1.08)
                
                # 2. Market hours vs after-hours (reduced volatility after hours)
                vol_multiplier = 1.0 if is_market_hours else 0.35
                volatility_component = random.gauss(0, volatility * vol_multiplier)
                
                # 3. Market-wide sentiment influence
                sentiment_component = (market_sentiment - 0.5) * 0.003
                
                # 4. Random news/earnings impact (10% chance)
                news_impact = random.uniform(-0.008, 0.012) if random.random() < 0.1 else 0
                
                # 5. Mean reversion (prices tend to revert to previous close)
                price_deviation = (current_price - prev_close) / prev_close
                mean_reversion = -price_deviation * 0.05 if abs(price_deviation) > 0.03 else 0
                
                # Combine all realistic factors
                total_change = (
                    trend_component + 
                    volatility_component + 
                    sentiment_component + 
                    news_impact + 
                    mean_reversion
                )
                
                # Apply realistic price movement
                new_price = current_price * (1 + total_change)
                
                # Circuit breakers (max 15% daily movement)
                daily_change_pct = abs(new_price - prev_close) / prev_close
                if daily_change_pct > 0.15:
                    new_price = prev_close * (1 + 0.15 * (1 if new_price > prev_close else -1))
                
                # Update stored price and evolve trend
                stocks[symbol]["price"] = new_price
                
                # Trend can evolve over time (5% chance of trend shift)
                if random.random() < 0.05:
                    stocks[symbol]["trend"] *= random.uniform(0.85, 1.15)
                    stocks[symbol]["trend"] = max(min(stocks[symbol]["trend"], 0.005), -0.005)
                
                # Calculate professional metrics
                price_change = new_price - prev_close
                change_percent = (price_change / prev_close) * 100
                
                # Realistic intraday high/low calculation
                daily_range = prev_close * volatility * random.uniform(2.0, 4.0)
                day_high = max(new_price, prev_close + daily_range * random.uniform(0.4, 0.9))
                day_low = min(new_price, prev_close - daily_range * random.uniform(0.4, 0.9))
                
                # Authentic volume patterns
                if symbol == "AAPL":
                    base_volume = 45000000
                elif symbol == "NVDA":
                    base_volume = 32000000
                elif symbol == "TSLA":
                    base_volume = 78000000
                else:
                    base_volume = random.randint(15000000, 55000000)
                
                # Volume spikes on big price moves and during market hours
                volume_multiplier = 1.8 if is_market_hours else 0.3
                volume_multiplier *= (1 + abs(change_percent) * 0.15)
                volume = int(base_volume * volume_multiplier * random.uniform(0.8, 1.4))
                
                # Professional stock data package
                stock_data = {
                    "symbol": symbol,
                    "price": round(new_price, 2),
                    "change": round(price_change, 2),
                    "change_percent": round(change_percent, 2),
                    "volume": volume,
                    "high": round(day_high, 2),
                    "low": round(day_low, 2),
                    "previous_close": round(prev_close, 2),
                    "market_cap": data["market_cap"],
                    "avg_volume": int(base_volume * random.uniform(0.95, 1.05)),
                    "timestamp": datetime.now().isoformat(),
                    "market_status": "OPEN" if is_market_hours else "CLOSED",
                    "last_updated": datetime.now().strftime("%H:%M:%S"),
                    "name": data["name"]
                }
                
                # Broadcast professional update
                await manager.broadcast_stock_update(symbol, stock_data)
                
            except Exception as e:
                logger.error(f"Error in stock simulation for {symbol}: {e}")
        
        iteration += 1
        
        # Realistic update frequency (faster during market hours)
        sleep_time = 4 if is_market_hours else 8
        await asyncio.sleep(sleep_time)

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
