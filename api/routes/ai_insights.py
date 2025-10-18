"""
AI Insights API routes - Buy/Sell/Hold recommendations based on multiple models
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from api.services.ai_insights import AIInsightsService
from api.auth.utils import get_current_user
from api.database.mongodb_models import RecommendationType
from api.services.xp_service import XPService
from api.database.mongodb import get_database

router = APIRouter()

class InsightRequest(BaseModel):
    symbol: str
    user_role: Optional[str] = "beginner"

class MultipleInsightRequest(BaseModel):
    symbols: List[str]
    user_role: Optional[str] = "beginner"

class InsightResponse(BaseModel):
    symbol: str
    insight_type: RecommendationType
    confidence_score: float
    reasoning: str
    current_price: float
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    market_sentiment: str
    risk_level: str
    time_horizon: str
    technical_indicators: Dict[str, float]
    model_predictions: List[Dict[str, Any]]
    created_at: datetime
    expires_at: datetime

@router.post("/insights/generate", response_model=InsightResponse)
async def generate_ai_insight(
    request: InsightRequest,
    current_user: Dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Generate AI insight and recommendation for a single stock"""
    try:
        ai_service = AIInsightsService()
        
        # Determine user role from profile or request
        user_role = request.user_role or "beginner"
        
        insight = await ai_service.generate_insight(
            symbol=request.symbol.upper(),
            user_role=user_role
        )
        
        if "error" in insight:
            raise HTTPException(
                status_code=400,
                detail=f"Error generating insight for {request.symbol}: {insight['error']}"
            )
        
        # Award XP for viewing AI insight
        try:
            xp_service = XPService(db)
            await xp_service.track_ai_insight_view(
                user_id=current_user["user_id"],
                symbol=request.symbol.upper()
            )
        except Exception as xp_error:
            # Don't fail the insight if XP tracking fails
            print(f"XP tracking failed: {xp_error}")
        
        return insight
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating AI insight: {str(e)}"
        )

@router.post("/insights/multiple")
async def generate_multiple_insights(
    request: MultipleInsightRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Generate AI insights for multiple stocks"""
    try:
        if len(request.symbols) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 symbols allowed per request"
            )
        
        ai_service = AIInsightsService()
        user_role = request.user_role or "beginner"
        
        insights = await ai_service.get_multiple_insights(
            symbols=[s.upper() for s in request.symbols],
            user_role=user_role
        )
        
        return {
            "insights": insights,
            "user_role": user_role,
            "symbols_analyzed": len(request.symbols),
            "generated_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating multiple insights: {str(e)}"
        )

@router.get("/insights/{symbol}")
async def get_insight_for_symbol(
    symbol: str,
    user_role: Optional[str] = Query(default="beginner", description="User role for personalized insights"),
    current_user: Dict = Depends(get_current_user)
):
    """Get AI insight for a specific symbol (convenience endpoint)"""
    try:
        ai_service = AIInsightsService()
        
        insight = await ai_service.generate_insight(
            symbol=symbol.upper(),
            user_role=user_role
        )
        
        if "error" in insight:
            raise HTTPException(
                status_code=400,
                detail=f"Error generating insight for {symbol}: {insight['error']}"
            )
        
        return insight
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting insight for {symbol}: {str(e)}"
        )

@router.get("/insights/watchlist/{user_id}")
async def get_watchlist_insights(
    user_id: str,
    user_role: Optional[str] = Query(default="beginner", description="User role for personalized insights"),
    current_user: Dict = Depends(get_current_user)
):
    """Generate insights for all stocks in user's watchlist"""
    try:
        # For now, we'll use a default watchlist
        # In a real implementation, you'd fetch the user's actual watchlist from the database
        default_watchlist = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        
        ai_service = AIInsightsService()
        
        insights = await ai_service.get_multiple_insights(
            symbols=default_watchlist,
            user_role=user_role
        )
        
        # Sort insights by confidence score (highest first)
        sorted_insights = dict(sorted(
            insights.items(), 
            key=lambda x: x[1].get("confidence_score", 0), 
            reverse=True
        ))
        
        # Categorize by recommendation type
        buy_recommendations = {k: v for k, v in sorted_insights.items() 
                             if v.get("insight_type") == RecommendationType.BUY}
        sell_recommendations = {k: v for k, v in sorted_insights.items() 
                              if v.get("insight_type") == RecommendationType.SELL}
        hold_recommendations = {k: v for k, v in sorted_insights.items() 
                               if v.get("insight_type") == RecommendationType.HOLD}
        
        return {
            "user_id": user_id,
            "user_role": user_role,
            "watchlist_size": len(default_watchlist),
            "summary": {
                "buy_count": len(buy_recommendations),
                "sell_count": len(sell_recommendations),
                "hold_count": len(hold_recommendations)
            },
            "insights": {
                "all": sorted_insights,
                "buy_recommendations": buy_recommendations,
                "sell_recommendations": sell_recommendations,
                "hold_recommendations": hold_recommendations
            },
            "generated_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting watchlist insights: {str(e)}"
        )

@router.get("/insights/market-overview")
async def get_market_overview(
    user_role: Optional[str] = Query(default="beginner", description="User role for personalized insights"),
    current_user: Dict = Depends(get_current_user)
):
    """Get market overview with insights for major stocks"""
    try:
        # Major market stocks for overview
        market_stocks = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
        
        ai_service = AIInsightsService()
        
        insights = await ai_service.get_multiple_insights(
            symbols=market_stocks,
            user_role=user_role
        )
        
        # Calculate market sentiment
        total_insights = len([v for v in insights.values() if "error" not in v])
        bullish_count = len([v for v in insights.values() 
                           if v.get("insight_type") == RecommendationType.BUY])
        bearish_count = len([v for v in insights.values() 
                           if v.get("insight_type") == RecommendationType.SELL])
        
        if total_insights > 0:
            bullish_percent = (bullish_count / total_insights) * 100
            bearish_percent = (bearish_count / total_insights) * 100
        else:
            bullish_percent = bearish_percent = 0
        
        # Determine overall market sentiment
        if bullish_percent > 60:
            overall_sentiment = "bullish"
        elif bearish_percent > 60:
            overall_sentiment = "bearish"
        else:
            overall_sentiment = "neutral"
        
        # Calculate average confidence
        confidences = [v.get("confidence_score", 0.5) for v in insights.values() if "error" not in v]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        return {
            "market_overview": {
                "overall_sentiment": overall_sentiment,
                "bullish_percentage": round(bullish_percent, 1),
                "bearish_percentage": round(bearish_percent, 1),
                "average_confidence": round(avg_confidence, 3),
                "stocks_analyzed": total_insights
            },
            "stock_insights": insights,
            "user_role": user_role,
            "generated_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting market overview: {str(e)}"
        )

@router.get("/insights/recommendation-summary")
async def get_recommendation_summary(
    symbols: Optional[str] = Query(default=None, description="Comma-separated list of symbols"),
    user_role: Optional[str] = Query(default="beginner", description="User role for personalized insights"),
    current_user: Dict = Depends(get_current_user)
):
    """Get summary of recommendations for specified symbols or popular stocks"""
    try:
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            if len(symbol_list) > 20:
                raise HTTPException(status_code=400, detail="Maximum 20 symbols allowed")
        else:
            # Default popular stocks
            symbol_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX"]
        
        ai_service = AIInsightsService()
        
        insights = await ai_service.get_multiple_insights(
            symbols=symbol_list,
            user_role=user_role
        )
        
        # Create summary
        summary = {
            "total_symbols": len(symbol_list),
            "successful_analysis": len([v for v in insights.values() if "error" not in v]),
            "buy_signals": [],
            "sell_signals": [],
            "hold_signals": [],
            "high_confidence": [],  # > 0.7 confidence
            "medium_confidence": [],  # 0.5 - 0.7 confidence
            "low_confidence": []  # < 0.5 confidence
        }
        
        for symbol, insight in insights.items():
            if "error" in insight:
                continue
                
            confidence = insight.get("confidence_score", 0.5)
            insight_type = insight.get("insight_type")
            
            # Categorize by recommendation
            if insight_type == RecommendationType.BUY:
                summary["buy_signals"].append({
                    "symbol": symbol,
                    "confidence": confidence,
                    "target_price": insight.get("target_price"),
                    "current_price": insight.get("current_price")
                })
            elif insight_type == RecommendationType.SELL:
                summary["sell_signals"].append({
                    "symbol": symbol,
                    "confidence": confidence,
                    "target_price": insight.get("target_price"),
                    "current_price": insight.get("current_price")
                })
            else:
                summary["hold_signals"].append({
                    "symbol": symbol,
                    "confidence": confidence,
                    "current_price": insight.get("current_price")
                })
            
            # Categorize by confidence
            if confidence > 0.7:
                summary["high_confidence"].append(symbol)
            elif confidence >= 0.5:
                summary["medium_confidence"].append(symbol)
            else:
                summary["low_confidence"].append(symbol)
        
        # Sort by confidence (highest first)
        summary["buy_signals"].sort(key=lambda x: x["confidence"], reverse=True)
        summary["sell_signals"].sort(key=lambda x: x["confidence"], reverse=True)
        summary["hold_signals"].sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "summary": summary,
            "detailed_insights": insights,
            "user_role": user_role,
            "generated_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting recommendation summary: {str(e)}"
        )