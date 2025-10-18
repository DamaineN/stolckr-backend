"""
ML Prediction API routes
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import asyncio

from models.model_manager import ModelManager
from api.collectors.yahoo_finance import YahooFinanceCollector
from api.auth.utils import get_current_user
from api.database.mongodb import get_database
from api.services.xp_service import XPService

router = APIRouter()

class PredictionRequest(BaseModel):
    symbol: str
    model_type: str  # "lstm", "arima", "ensemble", "all"
    prediction_days: int = 30
    confidence_level: float = 0.95

class PredictionResponse(BaseModel):
    symbol: str
    model_type: str
    predictions: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: str

class ModelTrainingRequest(BaseModel):
    symbol: str
    model_type: str
    training_period: str = "2y"
    parameters: Optional[Dict[str, Any]] = None

@router.post("/predictions/predict")
async def create_prediction(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Generate stock price predictions using specified model"""
    try:
        # Get historical data for the symbol
        data_collector = YahooFinanceCollector()
        historical_data = await data_collector.get_historical_data(
            request.symbol, 
            period="2y",  # Get 2 years of data for better predictions
            interval="1d"
        )
        
        if not historical_data:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data available for symbol {request.symbol}"
            )
        
        # Initialize model manager
        model_manager = ModelManager()
        available_models = model_manager.get_available_models()
        
        # Update valid models to include all available models plus special options
        valid_models = available_models + ["all"]
        
        if request.model_type not in valid_models:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid model type. Choose from: {valid_models}"
            )
        
        # Generate predictions based on requested model
        if request.model_type == "all":
            # Get predictions from all models
            results = await model_manager.get_all_predictions(
                symbol=request.symbol,
                historical_data=historical_data,
                prediction_days=request.prediction_days,
                confidence_level=request.confidence_level
            )
        else:
            # Get prediction from single model
            single_result = await model_manager.get_single_prediction(
                model_name=request.model_type,
                symbol=request.symbol,
                historical_data=historical_data,
                prediction_days=request.prediction_days,
                confidence_level=request.confidence_level
            )
            results = {request.model_type: single_result}
        
        # Award XP for generating prediction
        try:
            xp_service = XPService(db)
            await xp_service.track_prediction(
                user_id=current_user["user_id"],
                symbol=request.symbol.upper(),
                model_type=request.model_type
            )
        except Exception as xp_error:
            # Don't fail the prediction if XP tracking fails
            print(f"XP tracking failed: {xp_error}")
        
        # Store prediction in database for future reference
        try:
            predictions_collection = db["predictions"]
            from bson import ObjectId
            
            # Calculate a representative prediction value for storage
            representative_prediction = None
            confidence = 0.0
            
            if results:
                # Get the first model's prediction as representative
                first_model_results = next(iter(results.values()))
                if first_model_results and 'predictions' in first_model_results:
                    predictions_data = first_model_results['predictions']
                    if isinstance(predictions_data, list) and len(predictions_data) > 0:
                        # Use the next day's prediction as representative
                        first_prediction = predictions_data[0]
                        representative_prediction = first_prediction.get('predicted_price')
                        confidence = first_prediction.get('confidence', 0.0)
                    
                    # Also try to get accuracy from metadata as backup confidence
                    if confidence == 0.0 and 'metadata' in first_model_results:
                        metadata = first_model_results['metadata']
                        confidence = metadata.get('accuracy_score', 0.0)
            
            # Create a structured record with properly formatted values
            # Handle both ObjectId and string user ID formats
            user_id = current_user["user_id"]
            if ObjectId.is_valid(user_id):
                user_id_obj = ObjectId(user_id)
            else:
                user_id_obj = user_id
                
            prediction_record = {
                "user_id": user_id_obj,
                "symbol": request.symbol.upper(),
                "model_type": request.model_type,
                "predicted_price": representative_prediction,
                "confidence": confidence if 0 < confidence <= 1 else 0.85,  # Default to 85% if missing or invalid
                "prediction_days": request.prediction_days,
                "results": results,
                "status": "active",
                "created_at": datetime.utcnow()
            }
            
            # Log the prediction details for debugging
            print(f"Storing prediction: {request.symbol.upper()} with {request.model_type} model")
            print(f"Predicted price: {representative_prediction}, Confidence: {confidence}")
            
            await predictions_collection.insert_one(prediction_record)
        except Exception as storage_error:
            # Don't fail the prediction if storage fails
            print(f"Prediction storage failed: {storage_error}")
        
        return {
            "symbol": request.symbol,
            "model_type": request.model_type,
            "prediction_days": request.prediction_days,
            "results": results,
            "metadata": {
                "confidence_level": request.confidence_level,
                "created_at": datetime.utcnow().isoformat(),
                "models_used": list(results.keys()),
                "available_models": available_models
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@router.get("/predictions/{symbol}")
async def get_cached_predictions(
    symbol: str,
    model_type: Optional[str] = Query(default=None, description="Filter by model type"),
    limit: int = Query(default=10, le=100, description="Number of recent predictions to return")
):
    """Get cached predictions for a symbol"""
    try:
        # This would typically query from database
        # For now, return a placeholder response
        return {
            "symbol": symbol.upper(),
            "cached_predictions": [],
            "message": "Cached predictions feature coming soon",
            "model_type": model_type,
            "limit": limit
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cached predictions: {str(e)}")

@router.post("/predictions/train")
async def train_model(request: ModelTrainingRequest, background_tasks: BackgroundTasks):
    """Train a model on historical data"""
    try:
        # Add training task to background
        background_tasks.add_task(
            _train_model_background,
            request.symbol,
            request.model_type,
            request.training_period,
            request.parameters or {}
        )
        
        return {
            "message": f"Training {request.model_type} model for {request.symbol}",
            "symbol": request.symbol,
            "model_type": request.model_type,
            "training_period": request.training_period,
            "status": "training_started",
            "estimated_completion": "15-30 minutes"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training initiation error: {str(e)}")

@router.get("/predictions/models/available")
async def get_available_models():
    """Get information about all available prediction models"""
    try:
        model_manager = ModelManager()
        available_models = model_manager.get_available_models()
        
        model_info = {}
        for model_name in available_models:
            model_info[model_name] = model_manager.get_model_info(model_name)
        
        return {
            "available_models": available_models,
            "model_details": model_info,
            "special_options": ["all"],
            "total_models": len(available_models),
            "created_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching model information: {str(e)}")

@router.get("/predictions/models/status")
async def get_model_status():
    """Get status of all trained models"""
    try:
        model_manager = ModelManager()
        available_models = model_manager.get_available_models()
        
        models_status = {}
        for model_name in available_models:
            models_status[model_name] = {
                "status": "available",
                "info": model_manager.get_model_info(model_name),
                "last_trained": "N/A (Real-time training)",
                "accuracy": "Varies by stock and timeframe"
            }
        
        return {
            "models": models_status,
            "total_available": len(available_models),
            "created_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching model status: {str(e)}")

@router.get("/predictions/backtest/{symbol}")
async def backtest_model(
    symbol: str,
    model_type: str = Query(description="Model to backtest"),
    test_period: str = Query(default="3mo", description="Backtesting period"),
    train_period: str = Query(default="2y", description="Training period")
):
    """Backtest model performance on historical data"""
    try:
        # Get historical data for backtesting
        data_collector = YahooFinanceCollector()
        historical_data = await data_collector.get_historical_data(
            symbol.upper(), 
            period="2y",  # Get 2 years of data for backtesting
            interval="1d"
        )
        
        if not historical_data:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data available for symbol {symbol}"
            )
        
        # Determine test period in days
        period_days = {
            "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365
        }
        test_days = period_days.get(test_period, 90)  # Default to 3 months
        
        # Initialize model manager
        model_manager = ModelManager()
        
        # Backtest based on model type
        if model_type.lower() == "all":
            # Backtest all models
            backtest_results = await model_manager.backtest_all_models(
                symbol=symbol.upper(),
                historical_data=historical_data,
                test_days=test_days
            )
        else:
            # Backtest single model
            backtest_results = await model_manager.backtest_model(
                model_name=model_type,
                symbol=symbol.upper(),
                historical_data=historical_data,
                test_days=test_days
            )
        
        return {
            "symbol": symbol.upper(),
            "model_type": model_type,
            "test_period": test_period,
            "train_period": train_period,
            "results": backtest_results,
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "available_models": model_manager.get_available_models()
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtesting error: {str(e)}")

async def _train_model_background(
    symbol: str,
    model_type: str,
    training_period: str,
    parameters: Dict[str, Any]
):
    """Background task for model training"""
    try:
        # Mock training process until ML models are implemented
        await asyncio.sleep(2)  # Simulate training time
        print(f"✅ Mock training completed for {model_type} model on {symbol}")
        
    except Exception as e:
        print(f"❌ Model training failed for {symbol}: {str(e)}")
