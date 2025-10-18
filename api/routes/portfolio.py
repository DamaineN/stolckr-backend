"""
Paper Trading Portfolio API routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from api.routes.auth import get_current_user, require_user_type
from api.database.models import UserTypeEnum

router = APIRouter()

# Pydantic Models
class TradeRequest(BaseModel):
    symbol: str
    action: str  # "buy" or "sell"
    quantity: int
    price: Optional[float] = None  # If None, use current market price

class TradeResponse(BaseModel):
    trade_id: int
    symbol: str
    action: str
    quantity: int
    price: float
    timestamp: datetime
    total_cost: float

class PortfolioPosition(BaseModel):
    symbol: str
    quantity: int
    avg_buy_price: float
    current_price: float
    market_value: float
    profit_loss: float
    profit_loss_percent: float

class PortfolioSummary(BaseModel):
    total_value: float
    cash_balance: float
    total_profit_loss: float
    total_profit_loss_percent: float
    positions: List[PortfolioPosition]

@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio(current_user: dict = Depends(get_current_user)):
    """Get user's paper trading portfolio"""
    user_id = current_user["user_id"]
    
    # TODO: Fetch actual portfolio data from database
    # TODO: Calculate real-time P&L using current stock prices
    
    # Mock portfolio data
    positions = [
        PortfolioPosition(
            symbol="AAPL",
            quantity=10,
            avg_buy_price=150.0,
            current_price=155.0,  # Would fetch from real-time API
            market_value=1550.0,
            profit_loss=50.0,
            profit_loss_percent=3.33
        ),
        PortfolioPosition(
            symbol="GOOGL",
            quantity=5,
            avg_buy_price=2500.0,
            current_price=2450.0,
            market_value=12250.0,
            profit_loss=-250.0,
            profit_loss_percent=-2.04
        )
    ]
    
    total_value = sum(pos.market_value for pos in positions)
    total_pl = sum(pos.profit_loss for pos in positions)
    
    return PortfolioSummary(
        total_value=total_value + 5000,  # Include cash balance
        cash_balance=5000.0,
        total_profit_loss=total_pl,
        total_profit_loss_percent=(total_pl / (total_value - total_pl)) * 100,
        positions=positions
    )

@router.post("/trade", response_model=TradeResponse)
async def execute_trade(
    trade: TradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Execute a paper trade (buy/sell)"""
    user_id = current_user["user_id"]
    
    # TODO: Validate user has sufficient cash/shares
    # TODO: Get current market price if not provided
    # TODO: Record trade in database
    # TODO: Update portfolio positions
    
    # Mock trade execution
    current_price = trade.price or 150.0  # Would fetch from real-time API
    total_cost = trade.quantity * current_price
    
    if trade.action.lower() == "sell":
        total_cost = -total_cost  # Negative for sells (cash received)
    
    return TradeResponse(
        trade_id=12345,  # Would come from database
        symbol=trade.symbol.upper(),
        action=trade.action.lower(),
        quantity=trade.quantity,
        price=current_price,
        timestamp=datetime.utcnow(),
        total_cost=total_cost
    )

@router.get("/trades")
async def get_trade_history(
    limit: int = Query(default=50, le=100),
    symbol: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    """Get user's trade history"""
    user_id = current_user["user_id"]
    
    # TODO: Fetch trade history from database with filters
    
    # Mock trade history
    trades = [
        {
            "trade_id": 1,
            "symbol": "AAPL",
            "action": "buy",
            "quantity": 10,
            "price": 150.0,
            "timestamp": "2024-01-15T10:30:00Z",
            "total_cost": 1500.0
        },
        {
            "trade_id": 2,
            "symbol": "GOOGL", 
            "action": "buy",
            "quantity": 5,
            "price": 2500.0,
            "timestamp": "2024-01-16T14:20:00Z",
            "total_cost": 12500.0
        }
    ]
    
    # Apply symbol filter if provided
    if symbol:
        trades = [t for t in trades if t["symbol"] == symbol.upper()]
    
    return {
        "trades": trades[:limit],
        "total_count": len(trades)
    }

@router.get("/performance")
async def get_performance_metrics(
    period: str = Query(default="1M", description="Time period (1D, 1W, 1M, 3M, 1Y)"),
    current_user: dict = Depends(get_current_user)
):
    """Get portfolio performance metrics"""
    user_id = current_user["user_id"]
    
    # TODO: Calculate actual performance metrics from database
    # TODO: Include portfolio value over time, Sharpe ratio, etc.
    
    # Mock performance data
    return {
        "period": period,
        "total_return": 2.5,  # Percentage
        "total_return_amount": 425.0,
        "best_performing_stock": {
            "symbol": "AAPL",
            "return_percent": 3.33
        },
        "worst_performing_stock": {
            "symbol": "GOOGL", 
            "return_percent": -2.04
        },
        "win_rate": 60.0,  # Percentage of profitable trades
        "total_trades": 15,
        "profitable_trades": 9,
        "portfolio_value_history": [
            {"date": "2024-01-01", "value": 20000.0},
            {"date": "2024-01-15", "value": 20125.0},
            {"date": "2024-01-30", "value": 20425.0}
        ]
    }

@router.delete("/reset-portfolio")
async def reset_portfolio(current_user: dict = Depends(get_current_user)):
    """Reset paper trading portfolio (for testing)"""
    user_id = current_user["user_id"]
    
    # TODO: Delete all user's trades and reset cash balance
    
    return {
        "message": "Portfolio reset successfully",
        "cash_balance": 10000.0,  # Starting cash
        "positions": []
    }

@router.get("/leaderboard")
async def get_leaderboard():
    """Get paper trading leaderboard (public data)"""
    # TODO: Calculate leaderboard from all users' performance
    
    # Mock leaderboard data
    return {
        "leaderboard": [
            {
                "rank": 1,
                "user_id": "anonymous_123",
                "total_return": 15.5,
                "portfolio_value": 23100.0
            },
            {
                "rank": 2,
                "user_id": "anonymous_456", 
                "total_return": 12.3,
                "portfolio_value": 22460.0
            },
            {
                "rank": 3,
                "user_id": "anonymous_789",
                "total_return": 8.7,
                "portfolio_value": 21740.0
            }
        ],
        "your_rank": 15,  # Current user's rank
        "total_participants": 247
    }
