"""
Stock Market Prediction App - FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config.settings import settings
from api.middleware.security import SecurityMiddleware, rate_limit_handler
# Import only health route for now, others commented until modules are ready
from api.routes import health
# from api.routes import predictions, stocks, auth, portfolio, goals, recommendations, websocket
# from api.database import mongodb, postgresql

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Stock Market Prediction API...")
    
    # Initialize MongoDB connection
    from api.database.mongodb import mongodb
    await mongodb.connect()
    
    yield
    
    # Shutdown
    print("Shutting down Stock Market Prediction API...")
    from api.database.mongodb import mongodb
    await mongodb.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Stock Market Prediction API",
    description="AI-powered stock market prediction and analysis API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(SecurityMiddleware)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
from api.routes import stocks, predictions, auth, watchlist, ai_insights, xp_goals, dashboard, simple_paper_trading, admin
app.include_router(stocks.router, prefix="/api/v1", tags=["Stocks"])
app.include_router(predictions.router, prefix="/api/v1", tags=["Predictions"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(watchlist.router, prefix="/api/v1", tags=["Watchlist"])
app.include_router(ai_insights.router, prefix="/api/v1", tags=["AI Insights"])
app.include_router(simple_paper_trading.router, prefix="/api/v1", tags=["Simple Paper Trading"])
app.include_router(xp_goals.router, prefix="/api/v1/xp", tags=["XP & Goals"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])
# app.include_router(websocket.router, prefix="/api/v1", tags=["WebSocket"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Stock Market Prediction API",
        "version": "2.0.0",
        "description": "AI-powered stock market prediction with multiple models, AI insights, and paper trading",
        "features": {
            "prediction_models": ["Moving Average", "LSTM", "ARIMA", "Linear Regression", "Random Forest", "XGBoost", "SVR"],
            "ai_insights": "Buy/Sell/Hold recommendations with confidence scores",
            "paper_trading": "Virtual portfolio management and trading simulation",
            "user_roles": ["Beginner", "Casual", "Paper Trader"],
            "real_time_data": "Live stock prices and market data"
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/api/v1/health",
            "predictions": "/api/v1/predictions",
            "ai_insights": "/api/v1/insights",
            "paper_trading": "/api/v1/paper-trading",
            "stocks": "/api/v1/stocks",
            "auth": "/api/v1/auth"
        }
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """General exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug_mode,
        log_level=settings.log_level.lower()
    )
