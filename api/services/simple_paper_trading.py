"""
Simple Paper Trading Service - In-memory virtual portfolio management
No authentication or database required - for demonstration purposes
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
from collections import defaultdict

from api.collectors.yahoo_finance import YahooFinanceCollector

logger = logging.getLogger(__name__)

class SimplePaperTradingService:
    """Simplified paper trading service using in-memory storage"""
    
    # In-memory storage (in production, use a proper database)
    portfolios: Dict[str, Dict[str, Any]] = {}
    trades: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def __init__(self):
        self.data_collector = YahooFinanceCollector()
        self.STARTING_CASH = 10000.0
        self.MIN_TRADE_AMOUNT = 1.0
    
    async def create_portfolio(self, starting_cash: float = 10000.0) -> Dict[str, Any]:
        """Create a new paper trading portfolio"""
        try:
            portfolio_id = str(uuid.uuid4())
            
            portfolio = {
                "id": portfolio_id,
                "created_at": datetime.utcnow().isoformat(),
                "starting_cash": starting_cash,
                "cash": starting_cash,
                "positions": {},  # {symbol: {quantity: int, avg_price: float, total_invested: float}}
                "total_value": starting_cash,
                "total_return": 0.0,
                "total_return_percent": 0.0,
                "trade_count": 0
            }
            
            self.portfolios[portfolio_id] = portfolio
            
            return {
                "success": True,
                "message": "Portfolio created successfully",
                "portfolio": portfolio
            }
            
        except Exception as e:
            logger.error(f"Error creating portfolio: {str(e)}")
            return {
                "success": False,
                "message": f"Error creating portfolio: {str(e)}"
            }
    
    async def get_portfolio(self, portfolio_id: str) -> Dict[str, Any]:
        """Get portfolio with current values"""
        try:
            if portfolio_id not in self.portfolios:
                return {
                    "success": False,
                    "message": f"Portfolio {portfolio_id} not found"
                }
            
            portfolio = self.portfolios[portfolio_id].copy()
            
            # Update current values for all positions
            positions_value = 0.0
            updated_positions = {}
            
            for symbol, position in portfolio["positions"].items():
                current_price = await self.get_stock_price(symbol)
                if current_price:
                    current_value = position["quantity"] * current_price
                    unrealized_pnl = current_value - position["total_invested"]
                    unrealized_pnl_percent = (unrealized_pnl / position["total_invested"]) * 100 if position["total_invested"] > 0 else 0
                    
                    updated_positions[symbol] = {
                        **position,
                        "current_price": current_price,
                        "current_value": current_value,
                        "unrealized_pnl": unrealized_pnl,
                        "unrealized_pnl_percent": unrealized_pnl_percent
                    }
                    
                    positions_value += current_value
                else:
                    # Keep existing position if can't get current price
                    updated_positions[symbol] = position
                    positions_value += position.get("current_value", position["total_invested"])
            
            # Update portfolio totals
            portfolio["positions"] = updated_positions
            portfolio["total_value"] = portfolio["cash"] + positions_value
            portfolio["total_return"] = portfolio["total_value"] - portfolio["starting_cash"]
            portfolio["total_return_percent"] = (portfolio["total_return"] / portfolio["starting_cash"]) * 100 if portfolio["starting_cash"] > 0 else 0
            
            # Update the stored portfolio
            self.portfolios[portfolio_id] = portfolio
            
            return {
                "success": True,
                "portfolio": portfolio
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio {portfolio_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Error getting portfolio: {str(e)}"
            }
    
    async def execute_trade(self, portfolio_id: str, symbol: str, action: str, quantity: int) -> Dict[str, Any]:
        """Execute a buy or sell trade"""
        try:
            if portfolio_id not in self.portfolios:
                return {
                    "success": False,
                    "message": f"Portfolio {portfolio_id} not found"
                }
            
            # Get current stock price
            current_price = await self.get_stock_price(symbol)
            if not current_price:
                return {
                    "success": False,
                    "message": f"Unable to get current price for {symbol}"
                }
            
            portfolio = self.portfolios[portfolio_id]
            trade_amount = current_price * quantity
            
            if action == "buy":
                return await self._execute_buy(portfolio, portfolio_id, symbol, quantity, current_price, trade_amount)
            elif action == "sell":
                return await self._execute_sell(portfolio, portfolio_id, symbol, quantity, current_price, trade_amount)
            else:
                return {
                    "success": False,
                    "message": "Invalid action. Use 'buy' or 'sell'"
                }
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return {
                "success": False,
                "message": f"Error executing trade: {str(e)}"
            }
    
    async def _execute_buy(self, portfolio: Dict, portfolio_id: str, symbol: str, quantity: int, current_price: float, trade_amount: float) -> Dict[str, Any]:
        """Execute a buy order"""
        try:
            # Check if enough cash
            if trade_amount > portfolio["cash"]:
                return {
                    "success": False,
                    "message": f"Insufficient funds. Need ${trade_amount:.2f}, have ${portfolio['cash']:.2f}"
                }
            
            # Check minimum trade amount
            if trade_amount < self.MIN_TRADE_AMOUNT:
                return {
                    "success": False,
                    "message": f"Trade amount too small. Minimum is ${self.MIN_TRADE_AMOUNT}"
                }
            
            # Update position
            if symbol in portfolio["positions"]:
                # Add to existing position
                existing = portfolio["positions"][symbol]
                new_quantity = existing["quantity"] + quantity
                new_total_invested = existing["total_invested"] + trade_amount
                new_avg_price = new_total_invested / new_quantity
                
                portfolio["positions"][symbol] = {
                    "quantity": new_quantity,
                    "avg_price": new_avg_price,
                    "total_invested": new_total_invested,
                    "last_trade_price": current_price,
                    "last_trade_date": datetime.utcnow().isoformat()
                }
            else:
                # Create new position
                portfolio["positions"][symbol] = {
                    "quantity": quantity,
                    "avg_price": current_price,
                    "total_invested": trade_amount,
                    "last_trade_price": current_price,
                    "last_trade_date": datetime.utcnow().isoformat()
                }
            
            # Update portfolio cash and trade count
            portfolio["cash"] -= trade_amount
            portfolio["trade_count"] += 1
            
            # Record trade
            trade_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "action": "buy",
                "quantity": quantity,
                "price": current_price,
                "total_amount": trade_amount,
                "cash_after": portfolio["cash"]
            }
            
            self.trades[portfolio_id].append(trade_record)
            
            return {
                "success": True,
                "message": f"Successfully bought {quantity} shares of {symbol}",
                "trade_details": {
                    "symbol": symbol,
                    "action": "buy",
                    "quantity": quantity,
                    "price": current_price,
                    "total_amount": trade_amount,
                    "cash_remaining": portfolio["cash"],
                    "trade_time": trade_record["timestamp"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing buy order: {str(e)}")
            return {
                "success": False,
                "message": f"Error executing buy order: {str(e)}"
            }
    
    async def _execute_sell(self, portfolio: Dict, portfolio_id: str, symbol: str, quantity: int, current_price: float, trade_amount: float) -> Dict[str, Any]:
        """Execute a sell order"""
        try:
            # Check if position exists
            if symbol not in portfolio["positions"]:
                return {
                    "success": False,
                    "message": f"No position found for {symbol}"
                }
            
            position = portfolio["positions"][symbol]
            
            # Check if enough shares
            if quantity > position["quantity"]:
                return {
                    "success": False,
                    "message": f"Insufficient shares. Have {position['quantity']}, trying to sell {quantity}"
                }
            
            # Calculate profit/loss
            cost_basis = position["avg_price"] * quantity
            profit_loss = trade_amount - cost_basis
            profit_loss_percent = (profit_loss / cost_basis) * 100 if cost_basis > 0 else 0
            
            # Update position
            if quantity == position["quantity"]:
                # Selling all shares - remove position
                del portfolio["positions"][symbol]
            else:
                # Partial sale - update position
                remaining_quantity = position["quantity"] - quantity
                remaining_invested = position["total_invested"] - cost_basis
                
                portfolio["positions"][symbol] = {
                    "quantity": remaining_quantity,
                    "avg_price": position["avg_price"],  # Keep same avg price
                    "total_invested": remaining_invested,
                    "last_trade_price": current_price,
                    "last_trade_date": datetime.utcnow().isoformat()
                }
            
            # Update portfolio cash and trade count
            portfolio["cash"] += trade_amount
            portfolio["trade_count"] += 1
            
            # Record trade
            trade_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "action": "sell",
                "quantity": quantity,
                "price": current_price,
                "total_amount": trade_amount,
                "profit_loss": profit_loss,
                "profit_loss_percent": profit_loss_percent,
                "cash_after": portfolio["cash"]
            }
            
            self.trades[portfolio_id].append(trade_record)
            
            return {
                "success": True,
                "message": f"Successfully sold {quantity} shares of {symbol}",
                "trade_details": {
                    "symbol": symbol,
                    "action": "sell",
                    "quantity": quantity,
                    "price": current_price,
                    "total_amount": trade_amount,
                    "profit_loss": profit_loss,
                    "profit_loss_percent": profit_loss_percent,
                    "cash_remaining": portfolio["cash"],
                    "trade_time": trade_record["timestamp"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing sell order: {str(e)}")
            return {
                "success": False,
                "message": f"Error executing sell order: {str(e)}"
            }
    
    async def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price"""
        try:
            # Use the existing Yahoo Finance collector
            historical_data = await self.data_collector.get_historical_data(
                symbol=symbol,
                period="1d",
                interval="1m"
            )
            
            if historical_data and len(historical_data) > 0:
                return historical_data[-1]["close"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {str(e)}")
            return None
    
    async def get_trade_history(self, portfolio_id: str) -> Dict[str, Any]:
        """Get trading history for a portfolio"""
        try:
            if portfolio_id not in self.portfolios:
                return {
                    "success": False,
                    "message": f"Portfolio {portfolio_id} not found"
                }
            
            trades = self.trades.get(portfolio_id, [])
            
            # Calculate summary stats
            total_trades = len(trades)
            buy_trades = [t for t in trades if t["action"] == "buy"]
            sell_trades = [t for t in trades if t["action"] == "sell"]
            
            total_bought = sum(t["total_amount"] for t in buy_trades)
            total_sold = sum(t["total_amount"] for t in sell_trades)
            
            profitable_trades = [t for t in sell_trades if t.get("profit_loss", 0) > 0]
            losing_trades = [t for t in sell_trades if t.get("profit_loss", 0) < 0]
            
            total_realized_pnl = sum(t.get("profit_loss", 0) for t in sell_trades)
            
            return {
                "success": True,
                "trades": list(reversed(trades)),  # Most recent first
                "summary": {
                    "total_trades": total_trades,
                    "buy_trades": len(buy_trades),
                    "sell_trades": len(sell_trades),
                    "total_bought": round(total_bought, 2),
                    "total_sold": round(total_sold, 2),
                    "profitable_trades": len(profitable_trades),
                    "losing_trades": len(losing_trades),
                    "total_realized_pnl": round(total_realized_pnl, 2),
                    "win_rate": (len(profitable_trades) / len(sell_trades)) * 100 if len(sell_trades) > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting trade history: {str(e)}")
            return {
                "success": False,
                "message": f"Error getting trade history: {str(e)}"
            }
    
    async def reset_portfolio(self, portfolio_id: str) -> Dict[str, Any]:
        """Reset portfolio to starting conditions"""
        try:
            if portfolio_id not in self.portfolios:
                return {
                    "success": False,
                    "message": f"Portfolio {portfolio_id} not found"
                }
            
            portfolio = self.portfolios[portfolio_id]
            starting_cash = portfolio["starting_cash"]
            
            # Reset portfolio
            portfolio.update({
                "cash": starting_cash,
                "positions": {},
                "total_value": starting_cash,
                "total_return": 0.0,
                "total_return_percent": 0.0,
                "trade_count": 0
            })
            
            # Clear trade history
            self.trades[portfolio_id] = []
            
            return {
                "success": True,
                "message": "Portfolio reset successfully",
                "portfolio": portfolio
            }
            
        except Exception as e:
            logger.error(f"Error resetting portfolio: {str(e)}")
            return {
                "success": False,
                "message": f"Error resetting portfolio: {str(e)}"
            }
    
    async def list_portfolios(self) -> Dict[str, Any]:
        """List all portfolios (for demo purposes)"""
        try:
            portfolio_list = []
            for portfolio_id, portfolio in self.portfolios.items():
                portfolio_list.append({
                    "id": portfolio_id,
                    "created_at": portfolio["created_at"],
                    "total_value": portfolio["total_value"],
                    "total_return_percent": portfolio["total_return_percent"],
                    "positions_count": len(portfolio["positions"]),
                    "trade_count": portfolio["trade_count"]
                })
            
            return {
                "success": True,
                "portfolios": portfolio_list,
                "total_portfolios": len(portfolio_list)
            }
            
        except Exception as e:
            logger.error(f"Error listing portfolios: {str(e)}")
            return {
                "success": False,
                "message": f"Error listing portfolios: {str(e)}"
            }