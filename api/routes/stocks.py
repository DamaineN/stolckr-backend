"""
Stock data API routes
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from api.collectors.yahoo_finance import YahooFinanceCollector
from api.collectors.alpha_vantage import AlphaVantageCollector
from api.auth.utils import get_current_user_optional
from api.database.mongodb import get_database
from api.services.xp_service import XPService

router = APIRouter()

class StockDataResponse(BaseModel):
    symbol: str
    data: List[dict]
    metadata: dict

class StockInfo(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    price: Optional[float] = None

@router.get("/stocks/{symbol}/historical")
async def get_historical_data(
    symbol: str,
    period: str = Query(default="1y", description="Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)"),
    interval: str = Query(default="1d", description="Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)"),
    current_user: dict = Depends(get_current_user_optional),
    db = Depends(get_database)
):
    """Get historical stock data from Yahoo Finance"""
    try:
        collector = YahooFinanceCollector()
        data = await collector.get_historical_data(symbol.upper(), period, interval)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
        
        # Award XP for viewing historical data if user is logged in
        if current_user:
            try:
                xp_service = XPService(db)
                await xp_service.track_historical_data_view(
                    user_id=current_user["user_id"],
                    symbol=symbol.upper()
                )
            except Exception as xp_error:
                print(f"XP tracking failed: {xp_error}")
        
        return StockDataResponse(
            symbol=symbol.upper(),
            data=data,
            metadata={
                "period": period,
                "interval": interval,
                "count": len(data),
                "last_updated": datetime.utcnow().isoformat(),
                "source": "Yahoo Finance"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

@router.get("/stocks/{symbol}/info")
async def get_stock_info(symbol: str):
    """Get basic stock information"""
    try:
        collector = YahooFinanceCollector()
        info = await collector.get_stock_info(symbol.upper())
        
        if not info:
            raise HTTPException(status_code=404, detail=f"Stock information not found for {symbol}")
        
        return StockInfo(
            symbol=symbol.upper(),
            name=info.get('longName', info.get('shortName', '')),
            sector=info.get('sector'),
            industry=info.get('industry'),
            market_cap=info.get('marketCap'),
            price=info.get('currentPrice', info.get('regularMarketPrice'))
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stock info: {str(e)}")

@router.get("/stocks/{symbol}/intraday")
async def get_intraday_data(
    symbol: str,
    interval: str = Query(default="5min", description="Intraday interval (1min, 5min, 15min, 30min, 60min)"),
    outputsize: str = Query(default="compact", description="Output size (compact, full)")
):
    """Get intraday stock data from Alpha Vantage"""
    try:
        collector = AlphaVantageCollector()
        data = await collector.get_intraday_data(symbol.upper(), interval, outputsize)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No intraday data found for symbol {symbol}")
        
        return StockDataResponse(
            symbol=symbol.upper(),
            data=data,
            metadata={
                "interval": interval,
                "outputsize": outputsize,
                "count": len(data),
                "last_updated": datetime.utcnow().isoformat(),
                "source": "Alpha Vantage"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching intraday data: {str(e)}")

@router.get("/stocks/{symbol}/technical-indicators")
async def get_technical_indicators(
    symbol: str,
    indicator: str = Query(description="Technical indicator (SMA, EMA, RSI, MACD, etc.)"),
    time_period: int = Query(default=20, description="Time period for the indicator"),
    series_type: str = Query(default="close", description="Price type (open, high, low, close)")
):
    """Get technical indicators from Alpha Vantage"""
    try:
        collector = AlphaVantageCollector()
        data = await collector.get_technical_indicator(
            symbol.upper(), 
            indicator.upper(), 
            time_period,
            series_type
        )
        
        if not data:
            raise HTTPException(
                status_code=404, 
                detail=f"No {indicator} data found for symbol {symbol}"
            )
        
        return {
            "symbol": symbol.upper(),
            "indicator": indicator.upper(),
            "time_period": time_period,
            "series_type": series_type,
            "data": data,
            "metadata": {
                "count": len(data),
                "last_updated": datetime.utcnow().isoformat(),
                "source": "Alpha Vantage"
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching technical indicators: {str(e)}"
        )

@router.get("/stocks/search")
async def search_stocks(
    query: str = Query(description="Search query for stock symbols or company names"),
    limit: int = Query(default=10, le=50, description="Maximum number of results")
):
    """Search for stocks by symbol or company name"""
    try:
        collector = YahooFinanceCollector()
        results = await collector.search_stocks(query, limit)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching stocks: {str(e)}")
