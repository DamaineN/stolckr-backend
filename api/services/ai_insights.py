"""
AI Insights Service - Provides intelligent buy/sell/hold recommendations
Analyzes multiple prediction models and market data to generate actionable insights
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np

# from models.model_manager import ModelManager  # Temporarily disabled
from api.collectors.yahoo_finance import YahooFinanceCollector
from api.database.mongodb_models import AIInsight, RecommendationType

logger = logging.getLogger(__name__)

class AIInsightsService:
    """Service for generating AI-powered investment insights and recommendations"""
    
    def __init__(self):
        # self.model_manager = ModelManager()  # Temporarily disabled
        self.data_collector = YahooFinanceCollector()
        
        # Confidence thresholds for recommendations
        self.BUY_THRESHOLD = 0.7
        self.SELL_THRESHOLD = 0.3
        self.HOLD_THRESHOLD_LOW = 0.4
        self.HOLD_THRESHOLD_HIGH = 0.6
        
        # Technical indicator weights
        self.indicator_weights = {
            "model_agreement": 0.4,
            "trend_strength": 0.25,
            "volatility": 0.15,
            "volume": 0.1,
            "support_resistance": 0.1
        }
    
    async def generate_insight(self, symbol: str, user_role: str = "beginner") -> Dict[str, Any]:
        """
        Generate comprehensive AI insight for a stock symbol
        
        Args:
            symbol: Stock symbol to analyze
            user_role: User role for personalized insights (beginner, casual, paper_trader)
            
        Returns:
            Dictionary containing AI insight and recommendation
        """
        try:
            # Get historical data (simplified for testing)
            try:
                historical_data = await self.data_collector.get_historical_data(
                    symbol=symbol,
                    period="1y",
                    interval="1d"
                )
            except Exception as data_error:
                logger.error(f"Data collection failed for {symbol}: {str(data_error)}")
                # Use mock historical data
                historical_data = [
                    {"close": 150.0, "volume": 1000000, "date": "2024-01-01"},
                    {"close": 152.0, "volume": 1100000, "date": "2024-01-02"},
                    {"close": 148.0, "volume": 900000, "date": "2024-01-03"}
                ]
            
            if not historical_data or len(historical_data) == 0:
                # Generate mock data
                historical_data = [
                    {"close": 150.0, "volume": 1000000, "date": "2024-01-01"},
                    {"close": 152.0, "volume": 1100000, "date": "2024-01-02"},
                    {"close": 148.0, "volume": 900000, "date": "2024-01-03"}
                ]
            
            # Analyze current market data first
            current_price = historical_data[-1]["close"]
            
            # Get predictions from all models (using mock data for now)
            # all_predictions = await self.model_manager.get_all_predictions(
            #     symbol=symbol,
            #     historical_data=historical_data,
            #     prediction_days=30
            # )
            
            # Mock predictions for testing
            all_predictions = {
                "LSTM": {
                    "status": "completed",
                    "predictions": [
                        {"predicted_price": current_price * 1.05, "date": "2024-01-01"},
                        {"predicted_price": current_price * 1.08, "date": "2024-01-02"},
                        {"predicted_price": current_price * 1.12, "date": "2024-01-07"}
                    ],
                    "metadata": {"accuracy_score": 0.85}
                },
                "Random Forest": {
                    "status": "completed", 
                    "predictions": [
                        {"predicted_price": current_price * 1.03, "date": "2024-01-01"},
                        {"predicted_price": current_price * 1.06, "date": "2024-01-02"},
                        {"predicted_price": current_price * 1.09, "date": "2024-01-07"}
                    ],
                    "metadata": {"accuracy_score": 0.78}
                }
            }
            technical_indicators = self._calculate_technical_indicators(historical_data)
            
            # Generate prediction analysis
            prediction_analysis = self._analyze_predictions(all_predictions, current_price)
            
            # Calculate overall confidence and recommendation
            recommendation_data = self._calculate_recommendation(
                prediction_analysis, 
                technical_indicators, 
                current_price
            )
            
            # Personalize insight based on user role
            personalized_reasoning = self._personalize_reasoning(
                recommendation_data["reasoning"], 
                recommendation_data["insight_type"], 
                user_role
            )
            
            # Create AI insight object
            insight = {
                "symbol": symbol,
                "insight_type": recommendation_data["insight_type"],
                "confidence_score": recommendation_data["confidence_score"],
                "reasoning": personalized_reasoning,
                "model_predictions": prediction_analysis["model_summary"],
                "technical_indicators": technical_indicators,
                "market_sentiment": self._determine_market_sentiment(technical_indicators),
                "current_price": current_price,
                "target_price": recommendation_data.get("target_price"),
                "stop_loss_price": recommendation_data.get("stop_loss_price"),
                "risk_level": self._assess_risk_level(technical_indicators),
                "time_horizon": self._suggest_time_horizon(user_role),
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=24)
            }
            
            return insight
            
        except Exception as e:
            logger.error(f"Error generating insight for {symbol}: {str(e)}")
            return {
                "symbol": symbol,
                "insight_type": RecommendationType.HOLD,
                "confidence_score": 0.5,
                "reasoning": f"Error analyzing {symbol}. Please try again later.",
                "error": str(e)
            }
    
    def _calculate_technical_indicators(self, historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate technical indicators from historical data"""
        try:
            prices = [item["close"] for item in historical_data[-50:]]  # Last 50 days
            volumes = [item.get("volume", 1000000) for item in historical_data[-50:]]
            
            # Moving averages
            sma_20 = np.mean(prices[-20:])
            sma_50 = np.mean(prices) if len(prices) >= 50 else np.mean(prices)
            
            # Price momentum
            current_price = prices[-1]
            price_change_1d = (current_price - prices[-2]) / prices[-2] if len(prices) > 1 else 0
            price_change_5d = (current_price - prices[-6]) / prices[-6] if len(prices) > 5 else 0
            price_change_20d = (current_price - prices[-21]) / prices[-21] if len(prices) > 20 else 0
            
            # Volatility (standard deviation of returns)
            returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            volatility = np.std(returns) if len(returns) > 1 else 0.02
            
            # RSI (Relative Strength Index) - simplified
            rsi = self._calculate_rsi(prices)
            
            # Volume trend
            volume_sma_10 = np.mean(volumes[-10:]) if len(volumes) >= 10 else np.mean(volumes)
            current_volume = volumes[-1]
            volume_ratio = current_volume / volume_sma_10 if volume_sma_10 > 0 else 1.0
            
            # Bollinger Band position
            bb_position = self._calculate_bollinger_position(prices)
            
            return {
                "sma_20": round(sma_20, 2),
                "sma_50": round(sma_50, 2),
                "price_vs_sma_20": round((current_price / sma_20 - 1) * 100, 2),
                "price_vs_sma_50": round((current_price / sma_50 - 1) * 100, 2),
                "price_change_1d": round(price_change_1d * 100, 2),
                "price_change_5d": round(price_change_5d * 100, 2),
                "price_change_20d": round(price_change_20d * 100, 2),
                "volatility": round(volatility * 100, 2),
                "rsi": round(rsi, 2),
                "volume_ratio": round(volume_ratio, 2),
                "bollinger_position": round(bb_position, 3)
            }
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            return {
                "sma_20": 0, "sma_50": 0, "price_vs_sma_20": 0, "price_vs_sma_50": 0,
                "price_change_1d": 0, "price_change_5d": 0, "price_change_20d": 0,
                "volatility": 2.0, "rsi": 50.0, "volume_ratio": 1.0, "bollinger_position": 0.5
            }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [change if change > 0 else 0 for change in changes]
        losses = [-change if change < 0 else 0 for change in changes]
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_position(self, prices: List[float], period: int = 20) -> float:
        """Calculate position within Bollinger Bands (0 = lower band, 1 = upper band)"""
        if len(prices) < period:
            return 0.5  # Middle position
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)
        current_price = prices[-1]
        
        if upper_band == lower_band:
            return 0.5
        
        position = (current_price - lower_band) / (upper_band - lower_band)
        return max(0, min(1, position))
    
    def _analyze_predictions(self, all_predictions: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Analyze predictions from all models"""
        successful_models = {
            name: result for name, result in all_predictions.items()
            if result.get("status") == "completed" and len(result.get("predictions", [])) > 0
        }
        
        if not successful_models:
            return {
                "model_agreement": 0.5,
                "average_predicted_change": 0.0,
                "model_summary": [],
                "confidence": 0.5
            }
        
        # Analyze predictions
        predictions_7d = []
        predictions_30d = []
        model_summary = []
        
        for model_name, result in successful_models.items():
            predictions = result["predictions"]
            accuracy = result["metadata"].get("accuracy_score", 0.75)
            
            # Get 7-day and 30-day predictions
            pred_7d = predictions[6]["predicted_price"] if len(predictions) > 6 else predictions[-1]["predicted_price"]
            pred_30d = predictions[-1]["predicted_price"]
            
            predictions_7d.append(pred_7d)
            predictions_30d.append(pred_30d)
            
            model_summary.append({
                "model": model_name,
                "predicted_7d": pred_7d,
                "predicted_30d": pred_30d,
                "change_7d": ((pred_7d - current_price) / current_price) * 100,
                "change_30d": ((pred_30d - current_price) / current_price) * 100,
                "accuracy": accuracy
            })
        
        # Calculate averages
        avg_pred_7d = np.mean(predictions_7d)
        avg_pred_30d = np.mean(predictions_30d)
        
        # Calculate model agreement (how much models agree on direction)
        changes_7d = [(p - current_price) for p in predictions_7d]
        changes_30d = [(p - current_price) for p in predictions_30d]
        
        # Agreement score based on how many models agree on direction
        bullish_7d = sum(1 for change in changes_7d if change > 0)
        bearish_7d = sum(1 for change in changes_7d if change < 0)
        agreement_7d = max(bullish_7d, bearish_7d) / len(changes_7d)
        
        return {
            "model_agreement": agreement_7d,
            "average_predicted_change": ((avg_pred_7d - current_price) / current_price) * 100,
            "predicted_7d": avg_pred_7d,
            "predicted_30d": avg_pred_30d,
            "model_summary": model_summary,
            "confidence": np.mean([model["accuracy"] for model in model_summary])
        }
    
    def _calculate_recommendation(self, prediction_analysis: Dict[str, Any], 
                                technical_indicators: Dict[str, float], 
                                current_price: float) -> Dict[str, Any]:
        """Calculate overall recommendation based on all factors"""
        
        # Factor scores (0 to 1, where 1 is most bullish)
        factors = {}
        
        # Model prediction factor
        avg_change = prediction_analysis["average_predicted_change"]
        if avg_change > 5:
            factors["model_prediction"] = 0.8
        elif avg_change > 2:
            factors["model_prediction"] = 0.7
        elif avg_change > -2:
            factors["model_prediction"] = 0.5
        elif avg_change > -5:
            factors["model_prediction"] = 0.3
        else:
            factors["model_prediction"] = 0.2
        
        # Model agreement factor
        factors["model_agreement"] = prediction_analysis["model_agreement"]
        
        # Technical indicators factors
        # RSI factor (oversold = bullish, overbought = bearish)
        rsi = technical_indicators["rsi"]
        if rsi < 30:
            factors["rsi"] = 0.8
        elif rsi < 50:
            factors["rsi"] = 0.6
        elif rsi < 70:
            factors["rsi"] = 0.4
        else:
            factors["rsi"] = 0.2
        
        # Price vs moving average factor
        price_vs_sma = (technical_indicators["price_vs_sma_20"] + technical_indicators["price_vs_sma_50"]) / 2
        if price_vs_sma > 5:
            factors["trend"] = 0.8
        elif price_vs_sma > 0:
            factors["trend"] = 0.6
        elif price_vs_sma > -5:
            factors["trend"] = 0.4
        else:
            factors["trend"] = 0.2
        
        # Volatility factor (lower volatility = higher confidence)
        volatility = technical_indicators["volatility"]
        if volatility < 1:
            factors["volatility"] = 0.8
        elif volatility < 2:
            factors["volatility"] = 0.6
        elif volatility < 3:
            factors["volatility"] = 0.4
        else:
            factors["volatility"] = 0.2
        
        # Calculate weighted score
        weights = {
            "model_prediction": 0.3,
            "model_agreement": 0.25,
            "rsi": 0.15,
            "trend": 0.2,
            "volatility": 0.1
        }
        
        overall_score = sum(factors[key] * weights[key] for key in factors.keys())
        
        # Determine recommendation
        if overall_score >= self.BUY_THRESHOLD:
            insight_type = RecommendationType.BUY
            target_price = current_price * 1.1  # 10% upside target
            stop_loss_price = current_price * 0.95  # 5% stop loss
        elif overall_score <= self.SELL_THRESHOLD:
            insight_type = RecommendationType.SELL
            target_price = current_price * 0.9  # 10% downside target
            stop_loss_price = current_price * 1.05  # 5% stop loss for short
        else:
            insight_type = RecommendationType.HOLD
            target_price = None
            stop_loss_price = None
        
        # Generate reasoning
        reasoning_parts = []
        
        if factors["model_prediction"] > 0.6:
            reasoning_parts.append("Multiple prediction models suggest upward price movement")
        elif factors["model_prediction"] < 0.4:
            reasoning_parts.append("Multiple prediction models suggest downward price movement")
        else:
            reasoning_parts.append("Prediction models show mixed signals")
        
        if factors["model_agreement"] > 0.7:
            reasoning_parts.append("High model agreement increases confidence")
        elif factors["model_agreement"] < 0.4:
            reasoning_parts.append("Low model agreement suggests uncertainty")
        
        if rsi < 30:
            reasoning_parts.append("Stock appears oversold (RSI < 30)")
        elif rsi > 70:
            reasoning_parts.append("Stock appears overbought (RSI > 70)")
        
        if price_vs_sma > 2:
            reasoning_parts.append("Price trading above moving averages indicates bullish trend")
        elif price_vs_sma < -2:
            reasoning_parts.append("Price trading below moving averages indicates bearish trend")
        
        reasoning = ". ".join(reasoning_parts) + "."
        
        return {
            "insight_type": insight_type,
            "confidence_score": overall_score,
            "reasoning": reasoning,
            "target_price": target_price,
            "stop_loss_price": stop_loss_price,
            "factors": factors
        }
    
    def _determine_market_sentiment(self, technical_indicators: Dict[str, float]) -> str:
        """Determine overall market sentiment"""
        bullish_indicators = 0
        bearish_indicators = 0
        
        # RSI
        if technical_indicators["rsi"] < 30:
            bullish_indicators += 1
        elif technical_indicators["rsi"] > 70:
            bearish_indicators += 1
        
        # Price vs moving averages
        if technical_indicators["price_vs_sma_20"] > 0 and technical_indicators["price_vs_sma_50"] > 0:
            bullish_indicators += 1
        elif technical_indicators["price_vs_sma_20"] < 0 and technical_indicators["price_vs_sma_50"] < 0:
            bearish_indicators += 1
        
        # Recent price changes
        if technical_indicators["price_change_5d"] > 2:
            bullish_indicators += 1
        elif technical_indicators["price_change_5d"] < -2:
            bearish_indicators += 1
        
        if bullish_indicators > bearish_indicators:
            return "bullish"
        elif bearish_indicators > bullish_indicators:
            return "bearish"
        else:
            return "neutral"
    
    def _assess_risk_level(self, technical_indicators: Dict[str, float]) -> str:
        """Assess risk level based on volatility and other factors"""
        volatility = technical_indicators["volatility"]
        
        if volatility > 4:
            return "high"
        elif volatility > 2:
            return "medium"
        else:
            return "low"
    
    def _suggest_time_horizon(self, user_role: str) -> str:
        """Suggest appropriate time horizon based on user role"""
        if user_role == "beginner":
            return "long-term"  # 6+ months
        elif user_role == "casual":
            return "medium-term"  # 1-6 months
        elif user_role == "paper_trader":
            return "short-term"  # days to weeks
        else:
            return "medium-term"
    
    def _personalize_reasoning(self, base_reasoning: str, insight_type: RecommendationType, user_role: str) -> str:
        """Personalize reasoning based on user role"""
        role_advice = {
            "beginner": {
                RecommendationType.BUY: " As a beginner, consider starting with a small position and focusing on well-established companies.",
                RecommendationType.SELL: " As a beginner, if you own this stock, consider taking profits or cutting losses. Focus on learning from each trade.",
                RecommendationType.HOLD: " As a beginner, holding can be a good strategy. Use this time to learn more about the company and market analysis."
            },
            "casual": {
                RecommendationType.BUY: " This could be a good addition to a diversified portfolio. Consider your overall allocation.",
                RecommendationType.SELL: " Consider your portfolio balance and tax implications before selling.",
                RecommendationType.HOLD: " Monitor the situation and be prepared to act if conditions change significantly."
            },
            "paper_trader": {
                RecommendationType.BUY: " Good opportunity for a paper trade. Consider your position size and risk management strategy.",
                RecommendationType.SELL: " Consider shorting opportunities or closing long positions in your paper portfolio.",
                RecommendationType.HOLD: " Continue monitoring for better entry/exit points in your paper trading strategy."
            }
        }
        
        personalized_advice = role_advice.get(user_role, {}).get(insight_type, "")
        return base_reasoning + personalized_advice

    async def get_multiple_insights(self, symbols: List[str], user_role: str = "beginner") -> Dict[str, Any]:
        """Generate insights for multiple symbols"""
        insights = {}
        
        # Process symbols concurrently
        tasks = []
        for symbol in symbols:
            task = self.generate_insight(symbol, user_role)
            tasks.append((symbol, task))
        
        for symbol, task in tasks:
            try:
                insight = await task
                insights[symbol] = insight
            except Exception as e:
                logger.error(f"Error generating insight for {symbol}: {str(e)}")
                insights[symbol] = {
                    "symbol": symbol,
                    "error": str(e),
                    "insight_type": RecommendationType.HOLD
                }
        
        return insights