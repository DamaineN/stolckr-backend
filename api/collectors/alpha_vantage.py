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
        # Always use mock data for reliable demo experience
        logger.info(f"Using mock intraday data for reliable demo experience: {symbol}")
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
        # Always use mock data for reliable demo experience
        logger.info(f"Using mock technical indicator data for reliable demo experience: {symbol} {indicator}")
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
        """Generate realistic intraday data for professional demo"""
        import random
        
        # Professional stock prices
        stock_prices = {
            "AAPL": 225.47, "GOOGL": 172.89, "MSFT": 412.18, "TSLA": 242.83,
            "NVDA": 139.76, "META": 583.45, "AMZN": 187.92, "NFLX": 701.28
        }
        
        base_price = stock_prices.get(symbol.upper(), 150.0)
        data = []
        current_price = base_price
        
        # Generate realistic intraday data (market hours: 9:30 AM - 4:00 PM)
        for i in range(78):  # 78 five-minute intervals in trading day
            # Market open time calculation
            minutes_from_open = i * 5
            hour = 9 + minutes_from_open // 60
            minute = 30 + (minutes_from_open % 60)
            
            if minute >= 60:
                hour += 1
                minute -= 60
            
            # Realistic intraday price movement
            volatility = random.uniform(0.001, 0.008)  # 0.1% to 0.8% per 5-min interval
            price_change = random.gauss(0, volatility)
            current_price *= (1 + price_change)
            
            # Generate OHLC for interval
            interval_volatility = random.uniform(0.001, 0.003)
            open_price = current_price * random.uniform(0.999, 1.001)
            high_price = current_price * (1 + interval_volatility)
            low_price = current_price * (1 - interval_volatility)
            close_price = current_price
            
            # Realistic volume patterns (higher at open/close)
            base_volume = 100000 if symbol == "AAPL" else random.randint(50000, 200000)
            if i < 6 or i > 72:  # First 30 min and last 30 min have higher volume
                volume_multiplier = random.uniform(2.0, 4.0)
            else:
                volume_multiplier = random.uniform(0.8, 1.5)
            
            volume = int(base_volume * volume_multiplier)
            
            timestamp = datetime.now().replace(hour=hour, minute=minute, second=0)
            
            data.append({
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume
            })
        
        logger.info(f"Generated {len(data)} realistic intraday data points for {symbol}")
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
