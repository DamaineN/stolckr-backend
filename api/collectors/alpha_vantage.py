"""
Alpha Vantage data collector
"""
import aiohttp
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class AlphaVantageCollector:
    """Alpha Vantage data collector for premium stock data"""
    
    def __init__(self):
        self.api_key = settings.alpha_vantage_api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_intraday_data(
        self, 
        symbol: str, 
        interval: str = "5min", 
        outputsize: str = "compact"
    ) -> List[Dict[str, Any]]:
        """
        Get intraday stock data from Alpha Vantage
        
        Args:
            symbol: Stock symbol
            interval: Time interval (1min, 5min, 15min, 30min, 60min)
            outputsize: compact (last 100 points) or full (all data)
            
        Returns:
            List of intraday data points
        """
        if not self.api_key or self.api_key == "your_alpha_vantage_api_key_here":
            logger.warning("Alpha Vantage API key not configured, returning mock data")
            return self._get_mock_intraday_data(symbol, interval)
        
        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "apikey": self.api_key
            }
            
            session = await self._get_session()
            async with session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_intraday_data(data, interval)
                else:
                    logger.error(f"Alpha Vantage API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching intraday data from Alpha Vantage: {str(e)}")
            return []
    
    def _parse_intraday_data(self, data: dict, interval: str) -> List[Dict[str, Any]]:
        """Parse Alpha Vantage intraday response"""
        time_series_key = f"Time Series ({interval})"
        time_series = data.get(time_series_key, {})
        
        parsed_data = []
        for timestamp, values in time_series.items():
            parsed_data.append({
                "timestamp": timestamp,
                "open": float(values.get("1. open", 0)),
                "high": float(values.get("2. high", 0)),
                "low": float(values.get("3. low", 0)),
                "close": float(values.get("4. close", 0)),
                "volume": int(values.get("5. volume", 0))
            })
        
        return sorted(parsed_data, key=lambda x: x["timestamp"])
    
    async def get_technical_indicator(
        self,
        symbol: str,
        indicator: str,
        time_period: int = 20,
        series_type: str = "close"
    ) -> List[Dict[str, Any]]:
        """
        Get technical indicators from Alpha Vantage
        
        Args:
            symbol: Stock symbol
            indicator: Technical indicator (SMA, EMA, RSI, MACD, etc.)
            time_period: Time period for the indicator
            series_type: Price type (open, high, low, close)
            
        Returns:
            List of technical indicator data points
        """
        if not self.api_key or self.api_key == "your_alpha_vantage_api_key_here":
            logger.warning("Alpha Vantage API key not configured, returning mock data")
            return self._get_mock_technical_indicator(symbol, indicator)
        
        try:
            params = {
                "function": indicator.upper(),
                "symbol": symbol,
                "interval": "daily",
                "time_period": time_period,
                "series_type": series_type,
                "apikey": self.api_key
            }
            
            session = await self._get_session()
            async with session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_technical_indicator(data, indicator)
                else:
                    logger.error(f"Alpha Vantage API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching technical indicator from Alpha Vantage: {str(e)}")
            return []
    
    def _parse_technical_indicator(self, data: dict, indicator: str) -> List[Dict[str, Any]]:
        """Parse Alpha Vantage technical indicator response"""
        # The key varies by indicator
        technical_key = f"Technical Analysis: {indicator.upper()}"
        technical_data = data.get(technical_key, {})
        
        parsed_data = []
        for date, values in technical_data.items():
            point = {"date": date}
            for key, value in values.items():
                # Remove the prefix numbers from keys (e.g., "1. SMA" -> "SMA")
                clean_key = key.split(". ", 1)[-1] if ". " in key else key
                point[clean_key.lower()] = float(value)
            parsed_data.append(point)
        
        return sorted(parsed_data, key=lambda x: x["date"])
    
    def _get_mock_intraday_data(self, symbol: str, interval: str) -> List[Dict[str, Any]]:
        """Generate mock intraday data when API key is not available"""
        base_price = 150.0
        data = []
        
        for i in range(50):  # Generate 50 mock data points
            timestamp = datetime.now().replace(hour=9+i//10, minute=(i*5)%60)
            price_variation = (i % 10 - 5) * 0.5
            
            data.append({
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "open": base_price + price_variation,
                "high": base_price + price_variation + 0.5,
                "low": base_price + price_variation - 0.5,
                "close": base_price + price_variation + 0.2,
                "volume": 100000 + i * 1000
            })
        
        return data
    
    def _get_mock_technical_indicator(self, symbol: str, indicator: str) -> List[Dict[str, Any]]:
        """Generate mock technical indicator data"""
        data = []
        base_value = 150.0 if indicator.upper() in ["SMA", "EMA"] else 50.0
        
        for i in range(30):
            date = (datetime.now().replace(day=1) + 
                   timedelta(days=i)).strftime("%Y-%m-%d")
            
            if indicator.upper() == "RSI":
                value = 50 + (i % 20 - 10) * 2  # RSI between 30-70
            elif indicator.upper() in ["SMA", "EMA"]:
                value = base_value + (i % 10 - 5) * 2
            else:
                value = base_value + (i % 10 - 5)
            
            data.append({
                "date": date,
                indicator.lower(): value
            })
        
        return data
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
