"""
Yahoo Finance data collector
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class YahooFinanceCollector:
    """Yahoo Finance data collector using yfinance library"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1y", 
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """
        Get historical stock data
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
        Returns:
            List of historical data points
        """
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                self.executor, 
                self._fetch_historical_data, 
                symbol, period, interval
            )
            return data
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return []
    
    def _fetch_historical_data(self, symbol: str, period: str, interval: str) -> List[Dict[str, Any]]:
        """Internal method to fetch historical data"""
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            return []
        
        # Convert to list of dictionaries
        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(date, 'strftime') else str(date),
                "open": float(row['Open']) if pd.notna(row['Open']) else None,
                "high": float(row['High']) if pd.notna(row['High']) else None,
                "low": float(row['Low']) if pd.notna(row['Low']) else None,
                "close": float(row['Close']) if pd.notna(row['Close']) else None,
                "volume": int(row['Volume']) if pd.notna(row['Volume']) else None,
            })
        
        return data
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get basic stock information
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Stock information dictionary
        """
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                self.executor, 
                self._fetch_stock_info, 
                symbol
            )
            return info
        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {str(e)}")
            return None
    
    def _fetch_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Internal method to fetch stock information"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                return None
            
            # Extract relevant information
            return {
                "symbol": symbol.upper(),
                "longName": info.get("longName"),
                "shortName": info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "marketCap": info.get("marketCap"),
                "currentPrice": info.get("currentPrice"),
                "regularMarketPrice": info.get("regularMarketPrice"),
                "previousClose": info.get("previousClose"),
                "dayLow": info.get("dayLow"),
                "dayHigh": info.get("dayHigh"),
                "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
                "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
                "volume": info.get("volume"),
                "averageVolume": info.get("averageVolume"),
                "beta": info.get("beta"),
                "dividendYield": info.get("dividendYield"),
                "peRatio": info.get("trailingPE"),
                "eps": info.get("trailingEps"),
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange"),
                "description": info.get("longBusinessSummary", "")[:500] if info.get("longBusinessSummary") else None
            }
        except Exception as e:
            logger.error(f"Error in _fetch_stock_info for {symbol}: {str(e)}")
            return None
    
    async def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for stocks by symbol or company name
        Only returns real, valid stocks that exist on major exchanges
        
        Args:
            query: Search query (symbol or company name)
            limit: Maximum number of results
            
        Returns:
            List of search results with valid stocks only
        """
        try:
            query = query.upper().strip()
            
            # If query looks like a stock symbol, validate it directly
            if len(query) <= 5 and query.isalpha():
                info = await self.get_stock_info(query)
                if info and info.get('symbol') and info.get('longName'):
                    # Additional validation: check if it has valid market data
                    if (info.get('currentPrice') or info.get('regularMarketPrice')) and info.get('marketCap'):
                        return [{
                            "symbol": query,
                            "name": info.get("longName") or info.get("shortName"),
                            "sector": info.get("sector"),
                            "exchange": info.get("exchange"),
                            "currency": info.get("currency", "USD"),
                            "price": info.get('currentPrice') or info.get('regularMarketPrice'),
                            "marketCap": info.get('marketCap')
                        }]
            
            # For longer queries or company names, use a predefined list of popular stocks
            # In production, you'd use a proper search API like Alpha Vantage's SYMBOL_SEARCH
            popular_stocks = {
                'APPLE': 'AAPL', 'MICROSOFT': 'MSFT', 'GOOGLE': 'GOOGL', 'ALPHABET': 'GOOGL',
                'AMAZON': 'AMZN', 'TESLA': 'TSLA', 'META': 'META', 'FACEBOOK': 'META',
                'NVIDIA': 'NVDA', 'NETFLIX': 'NFLX', 'DISNEY': 'DIS', 'COCA-COLA': 'KO',
                'JOHNSON': 'JNJ', 'WALMART': 'WMT', 'PROCTER': 'PG', 'MASTERCARD': 'MA',
                'VISA': 'V', 'HOME DEPOT': 'HD', 'BANK OF AMERICA': 'BAC', 'INTEL': 'INTC',
                'CISCO': 'CSCO', 'PFIZER': 'PFE', 'ORACLE': 'ORCL', 'ADOBE': 'ADBE',
                'SALESFORCE': 'CRM', 'TWITTER': 'TWTR', 'UBER': 'UBER', 'SPOTIFY': 'SPOT',
                'ZOOM': 'ZM', 'PAYPAL': 'PYPL', 'SQUARE': 'SQ', 'SHOPIFY': 'SHOP'
            }
            
            results = []
            
            # Search in popular stocks for company name matches
            for company, symbol in popular_stocks.items():
                if query in company or company in query:
                    info = await self.get_stock_info(symbol)
                    if info and info.get('symbol') and (info.get('currentPrice') or info.get('regularMarketPrice')):
                        results.append({
                            "symbol": symbol,
                            "name": info.get("longName") or info.get("shortName"),
                            "sector": info.get("sector"),
                            "exchange": info.get("exchange"),
                            "currency": info.get("currency", "USD"),
                            "price": info.get('currentPrice') or info.get('regularMarketPrice'),
                            "marketCap": info.get('marketCap')
                        })
                    
                    if len(results) >= limit:
                        break
            
            # If no results found in popular stocks, the symbol likely doesn't exist
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching stocks for query '{query}': {str(e)}")
            return []
    
    async def get_financial_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get financial data for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Financial data dictionary
        """
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                self.executor, 
                self._fetch_financial_data, 
                symbol
            )
            return data
        except Exception as e:
            logger.error(f"Error fetching financial data for {symbol}: {str(e)}")
            return None
    
    def _fetch_financial_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Internal method to fetch financial data"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get financial statements
            income_stmt = ticker.income_stmt
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cash_flow
            
            return {
                "symbol": symbol.upper(),
                "income_statement": income_stmt.to_dict() if not income_stmt.empty else {},
                "balance_sheet": balance_sheet.to_dict() if not balance_sheet.empty else {},
                "cash_flow": cash_flow.to_dict() if not cash_flow.empty else {},
                "fetched_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in _fetch_financial_data for {symbol}: {str(e)}")
            return None
    
    def __del__(self):
        """Clean up the thread pool executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
