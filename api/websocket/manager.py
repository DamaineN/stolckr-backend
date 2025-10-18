"""
WebSocket Connection Manager for Real-time Stock Updates
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Set
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[int, WebSocket] = {}
        # Track which stocks each user is watching
        self.user_subscriptions: Dict[int, Set[str]] = {}
        # Track which users are watching each stock
        self.stock_watchers: Dict[str, Set[int]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept WebSocket connection and store it"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_subscriptions[user_id] = set()
        logger.info(f"User {user_id} connected via WebSocket")
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection_established",
            "message": "Real-time updates connected",
            "timestamp": datetime.utcnow().isoformat()
        }, user_id)
    
    def disconnect(self, user_id: int):
        """Remove WebSocket connection and clean up subscriptions"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Remove user from all stock subscriptions
        if user_id in self.user_subscriptions:
            for symbol in self.user_subscriptions[user_id]:
                if symbol in self.stock_watchers:
                    self.stock_watchers[symbol].discard(user_id)
                    if not self.stock_watchers[symbol]:
                        del self.stock_watchers[symbol]
            del self.user_subscriptions[user_id]
        
        logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast_stock_update(self, symbol: str, stock_data: dict):
        """Broadcast stock price update to all subscribers"""
        if symbol not in self.stock_watchers:
            return
        
        message = {
            "type": "stock_update",
            "symbol": symbol,
            "data": stock_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all users watching this stock
        users_to_remove = []
        for user_id in self.stock_watchers[symbol].copy():
            try:
                await self.send_personal_message(message, user_id)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                users_to_remove.append(user_id)
        
        # Clean up failed connections
        for user_id in users_to_remove:
            self.disconnect(user_id)
    
    async def subscribe_to_stock(self, user_id: int, symbol: str):
        """Subscribe user to stock price updates"""
        symbol = symbol.upper()
        
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        
        self.user_subscriptions[user_id].add(symbol)
        
        if symbol not in self.stock_watchers:
            self.stock_watchers[symbol] = set()
        
        self.stock_watchers[symbol].add(user_id)
        
        # Send subscription confirmation
        await self.send_personal_message({
            "type": "subscription_confirmed",
            "symbol": symbol,
            "message": f"Subscribed to {symbol} updates"
        }, user_id)
        
        logger.info(f"User {user_id} subscribed to {symbol}")
    
    async def unsubscribe_from_stock(self, user_id: int, symbol: str):
        """Unsubscribe user from stock price updates"""
        symbol = symbol.upper()
        
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(symbol)
        
        if symbol in self.stock_watchers:
            self.stock_watchers[symbol].discard(user_id)
            if not self.stock_watchers[symbol]:
                del self.stock_watchers[symbol]
        
        # Send unsubscription confirmation
        await self.send_personal_message({
            "type": "unsubscription_confirmed",
            "symbol": symbol,
            "message": f"Unsubscribed from {symbol} updates"
        }, user_id)
        
        logger.info(f"User {user_id} unsubscribed from {symbol}")
    
    async def broadcast_portfolio_update(self, user_id: int, portfolio_data: dict):
        """Send portfolio update to specific user"""
        message = {
            "type": "portfolio_update",
            "data": portfolio_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(message, user_id)
    
    async def broadcast_prediction_update(self, symbol: str, prediction_data: dict):
        """Broadcast new AI prediction to all subscribers"""
        message = {
            "type": "prediction_update",
            "symbol": symbol,
            "data": prediction_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all users watching this stock
        if symbol in self.stock_watchers:
            for user_id in self.stock_watchers[symbol].copy():
                await self.send_personal_message(message, user_id)
    
    async def broadcast_recommendation_update(self, symbol: str, recommendation_data: dict):
        """Broadcast new AI recommendation to all subscribers"""
        message = {
            "type": "recommendation_update",
            "symbol": symbol,
            "data": recommendation_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all users watching this stock
        if symbol in self.stock_watchers:
            for user_id in self.stock_watchers[symbol].copy():
                await self.send_personal_message(message, user_id)
    
    async def send_market_alert(self, alert_data: dict, user_ids: List[int] = None):
        """Send market-wide alert to specified users or all connected users"""
        message = {
            "type": "market_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        target_users = user_ids or list(self.active_connections.keys())
        
        for user_id in target_users:
            await self.send_personal_message(message, user_id)
    
    def get_connection_stats(self) -> dict:
        """Get statistics about current connections"""
        return {
            "active_connections": len(self.active_connections),
            "total_subscriptions": sum(len(subs) for subs in self.user_subscriptions.values()),
            "watched_stocks": len(self.stock_watchers),
            "most_watched_stocks": [
                {"symbol": symbol, "watchers": len(watchers)}
                for symbol, watchers in sorted(
                    self.stock_watchers.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )[:10]
            ]
        }

# Global connection manager instance
manager = ConnectionManager()
