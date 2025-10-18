"""
Simple Paper Trading API routes - Demo virtual portfolio management
No authentication required - for demonstration purposes
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import uuid

from api.services.simple_paper_trading import SimplePaperTradingService

router = APIRouter()

class CreatePortfolioRequest(BaseModel):
    starting_cash: Optional[float] = 10000.0

class TradeRequest(BaseModel):
    portfolio_id: str
    symbol: str
    action: str  # "buy" or "sell"
    quantity: int

class TradeResponse(BaseModel):
    success: bool
    message: str
    trade_details: Optional[Dict[str, Any]] = None

@router.post("/simple-paper-trading/portfolio")
async def create_portfolio(request: CreatePortfolioRequest):
    """Create a new paper trading portfolio"""
    try:
        service = SimplePaperTradingService()
        result = await service.create_portfolio(starting_cash=request.starting_cash)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating portfolio: {str(e)}")

@router.get("/simple-paper-trading/portfolio/{portfolio_id}")
async def get_portfolio(portfolio_id: str):
    """Get portfolio details with current values"""
    try:
        service = SimplePaperTradingService()
        result = await service.get_portfolio(portfolio_id)
        
        if not result["success"]:
            if "not found" in result["message"].lower():
                raise HTTPException(status_code=404, detail=result["message"])
            else:
                raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting portfolio: {str(e)}")

@router.post("/simple-paper-trading/trade", response_model=TradeResponse)
async def execute_trade(request: TradeRequest):
    """Execute a paper trade (buy or sell)"""
    try:
        if request.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        
        if request.action.lower() not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="Action must be 'buy' or 'sell'")
        
        service = SimplePaperTradingService()
        result = await service.execute_trade(
            portfolio_id=request.portfolio_id,
            symbol=request.symbol.upper(),
            action=request.action.lower(),
            quantity=request.quantity
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing trade: {str(e)}")

@router.get("/simple-paper-trading/quote/{symbol}")
async def get_stock_quote(symbol: str):
    """Get current stock price"""
    try:
        service = SimplePaperTradingService()
        price = await service.get_stock_price(symbol.upper())
        
        if not price:
            raise HTTPException(status_code=404, detail=f"Unable to get price for {symbol.upper()}")
        
        return {
            "symbol": symbol.upper(),
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting quote: {str(e)}")

@router.get("/simple-paper-trading/portfolio/{portfolio_id}/history")
async def get_trade_history(portfolio_id: str):
    """Get portfolio trading history"""
    try:
        service = SimplePaperTradingService()
        result = await service.get_trade_history(portfolio_id)
        
        if not result["success"]:
            if "not found" in result["message"].lower():
                raise HTTPException(status_code=404, detail=result["message"])
            else:
                raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trade history: {str(e)}")

@router.delete("/simple-paper-trading/portfolio/{portfolio_id}")
async def reset_portfolio(portfolio_id: str):
    """Reset portfolio to starting conditions"""
    try:
        service = SimplePaperTradingService()
        result = await service.reset_portfolio(portfolio_id)
        
        if not result["success"]:
            if "not found" in result["message"].lower():
                raise HTTPException(status_code=404, detail=result["message"])
            else:
                raise HTTPException(status_code=400, detail=result["message"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting portfolio: {str(e)}")

@router.get("/simple-paper-trading/portfolios")
async def list_portfolios():
    """List all portfolios (for demo purposes)"""
    try:
        service = SimplePaperTradingService()
        result = await service.list_portfolios()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing portfolios: {str(e)}")