"""
Model Manager - Unified interface for all prediction models
Coordinates multiple models and provides ensemble predictions
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

# Import all prediction models
from models.lstm.lstm_predictor import LSTMPredictor
from models.arima.arima_predictor import ARIMAPredictor
from models.ensemble.ml_models import (
    RandomForestPredictor, 
    XGBoostPredictor, 
    SVRPredictor
)

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages all prediction models and provides ensemble predictions"""
    
    def __init__(self):
        self.models = {
            "LSTM": LSTMPredictor(),
            "ARIMA": ARIMAPredictor(),
            "Random Forest": RandomForestPredictor(),
            "XGBoost": XGBoostPredictor(),
            "SVR": SVRPredictor()
        }
        
    
    async def get_single_prediction(
        self,
        model_name: str,
        symbol: str,
        historical_data: List[Dict[str, Any]],
        prediction_days: int = 30,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """Get prediction from a single model"""
        if model_name not in self.models:
            return {
                "symbol": symbol,
                "model": model_name,
                "predictions": [],
                "metadata": {"error": f"Model {model_name} not available"},
                "status": "failed",
                "created_at": datetime.utcnow().isoformat()
            }
        
        try:
            model = self.models[model_name]
            result = await model.predict(
                symbol=symbol,
                historical_data=historical_data,
                prediction_days=prediction_days,
                confidence_level=confidence_level
            )
            return result
        except Exception as e:
            logger.error(f"Error in {model_name} prediction for {symbol}: {str(e)}")
            return {
                "symbol": symbol,
                "model": model_name,
                "predictions": [],
                "metadata": {"error": str(e)},
                "status": "failed",
                "created_at": datetime.utcnow().isoformat()
            }
    
    async def get_all_predictions(
        self,
        symbol: str,
        historical_data: List[Dict[str, Any]],
        prediction_days: int = 30,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """Get predictions from all available models"""
        results = {}
        
        # Run all models concurrently
        tasks = []
        for model_name in self.models.keys():
            task = self.get_single_prediction(
                model_name=model_name,
                symbol=symbol,
                historical_data=historical_data,
                prediction_days=prediction_days,
                confidence_level=confidence_level
            )
            tasks.append((model_name, task))
        
        # Wait for all predictions to complete
        for model_name, task in tasks:
            try:
                result = await task
                results[model_name] = result
            except Exception as e:
                logger.error(f"Error getting prediction from {model_name}: {str(e)}")
                results[model_name] = {
                    "symbol": symbol,
                    "model": model_name,
                    "predictions": [],
                    "metadata": {"error": str(e)},
                    "status": "failed",
                    "created_at": datetime.utcnow().isoformat()
                }
        
        return results
    
    
    async def backtest_model(
        self,
        model_name: str,
        symbol: str,
        historical_data: List[Dict[str, Any]],
        test_days: int = 30
    ) -> Dict[str, Any]:
        """Backtest a specific model"""
        if model_name not in self.models:
            return {
                "symbol": symbol,
                "model": model_name,
                "error": f"Model {model_name} not available",
                "status": "failed"
            }
        
        try:
            model = self.models[model_name]
            result = await model.backtest(
                symbol=symbol,
                historical_data=historical_data,
                test_days=test_days
            )
            return result
        except Exception as e:
            logger.error(f"Error in {model_name} backtesting for {symbol}: {str(e)}")
            return {
                "symbol": symbol,
                "model": model_name,
                "error": str(e),
                "status": "failed"
            }
    
    async def backtest_all_models(
        self,
        symbol: str,
        historical_data: List[Dict[str, Any]],
        test_days: int = 30
    ) -> Dict[str, Any]:
        """Backtest all available models"""
        results = {}
        
        # Run all backtests concurrently
        tasks = []
        for model_name in self.models.keys():
            task = self.backtest_model(
                model_name=model_name,
                symbol=symbol,
                historical_data=historical_data,
                test_days=test_days
            )
            tasks.append((model_name, task))
        
        # Wait for all backtests to complete
        for model_name, task in tasks:
            try:
                result = await task
                results[model_name] = result
            except Exception as e:
                logger.error(f"Error in {model_name} backtest: {str(e)}")
                results[model_name] = {
                    "symbol": symbol,
                    "model": model_name,
                    "error": str(e),
                    "status": "failed"
                }
        
        return results
    
    def get_available_models(self) -> List[str]:
        """Get list of available model names"""
        return list(self.models.keys())
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a specific model"""
        if model_name not in self.models:
            return {"error": f"Model {model_name} not found"}
        
        model = self.models[model_name]
        info = {
            "name": model_name,
            "class": model.__class__.__name__,
            "weight_in_ensemble": self.model_weights.get(model_name, 0.1)
        }
        
        # Add model-specific parameters
        if hasattr(model, 'short_window'):
            info["short_window"] = model.short_window
        if hasattr(model, 'long_window'):
            info["long_window"] = model.long_window
        if hasattr(model, 'sequence_length'):
            info["sequence_length"] = model.sequence_length
        if hasattr(model, 'order'):
            info["arima_order"] = model.order
        if hasattr(model, 'lookback_days'):
            info["lookback_days"] = model.lookback_days
        
        return info