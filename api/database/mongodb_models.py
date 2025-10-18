"""
Database models for MongoDB using Motor (async MongoDB driver)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from pydantic_core import core_schema
from bson import ObjectId
from enum import Enum
from typing import Any

# Custom ObjectId type for Pydantic v2
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [
                            core_schema.str_schema(),
                            core_schema.no_info_plain_validator_function(cls.validate),
                        ]
                    ),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError('Invalid ObjectId')

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    # Use Case roles
    BEGINNER = "beginner"
    CASUAL = "casual"
    PAPER_TRADER = "paper_trader"

class RecommendationType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class TradeType(str, Enum):
    BUY = "buy"
    SELL = "sell"

class PredictionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class XPActivityType(str, Enum):
    PREDICTION_USED = "prediction_used"
    STOCK_ADDED_WATCHLIST = "stock_added_watchlist"
    DAILY_LOGIN = "daily_login"
    AI_INSIGHT_VIEWED = "ai_insight_viewed"
    PROFILE_COMPLETED = "profile_completed"
    QUIZ_PASSED = "quiz_passed"
    TRADING_ACTION = "trading_action"
    ROLE_UPGRADED = "role_upgraded"

# User Models
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.BEGINNER
    is_verified: bool = False
    status: UserStatus = UserStatus.ACTIVE
    profile_picture: Optional[str] = None

class UserCreate(UserBase):
    password: str
    quiz_answers: Optional[Dict[int, int]] = None  # Quiz answers for role determination

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_verified: Optional[bool] = None
    status: Optional[UserStatus] = None

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    profile_picture: Optional[str] = None

class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    quiz_answers: Optional[Dict[int, int]] = None  # Store quiz answers
    
    # XP and Goals System
    total_xp: int = 0
    current_role_xp: int = 0  # XP within current role
    last_daily_xp: Optional[datetime] = None  # Last daily XP reward
    last_daily_checkin_date: Optional[datetime] = None  # Last daily check-in date for validation
    role_progression_history: List[Dict[str, Any]] = []  # Track role changes
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    account_locked_until: Optional[datetime] = None
    email_verification_token: Optional[str] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

class UserResponse(UserBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True
    )

# Stock Data Models
class StockPrice(BaseModel):
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None
    dividend_amount: Optional[float] = None
    split_coefficient: Optional[float] = None

class StockInfo(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    description: Optional[str] = None
    currency: str = "USD"
    exchange: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    employees: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# Prediction Models
class PredictionRequest(BaseModel):
    symbol: str
    model_type: str  # "lstm", "arima", "ensemble"
    prediction_days: int = Field(default=30, ge=1, le=365)
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99)
    user_id: Optional[str] = None

class PredictionResult(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: Optional[PyObjectId] = None
    symbol: str
    model_type: str
    prediction_days: int
    confidence_level: float
    predictions: List[Dict[str, Any]]  # List of predicted values with dates
    metadata: Dict[str, Any]  # Model parameters, accuracy metrics, etc.
    status: PredictionStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# Portfolio Models
class PortfolioHolding(BaseModel):
    symbol: str
    shares: float
    average_cost: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_percent: Optional[float] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Portfolio(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    name: str
    description: Optional[str] = None
    holdings: List[PortfolioHolding] = []
    total_value: Optional[float] = None
    total_cost: Optional[float] = None
    total_gain_loss: Optional[float] = None
    total_gain_loss_percent: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# Watchlist Models
class WatchlistItem(BaseModel):
    symbol: str
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None

class Watchlist(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    name: str
    description: Optional[str] = None
    items: List[WatchlistItem] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# Audit Log Models
class AuditLog(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: Optional[PyObjectId] = None
    action: str  # "login", "logout", "prediction_request", "portfolio_update", etc.
    resource: Optional[str] = None  # What was accessed/modified
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# API Usage Tracking
class APIUsage(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: Optional[PyObjectId] = None
    endpoint: str
    method: str
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    response_time_ms: Optional[float] = None
    status_code: int
    rate_limit_key: Optional[str] = None  # For rate limiting
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# Authentication Models
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# Extended User Profile with Role System and Gamification
class UserProfile(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId  # Reference to main User
    role: UserRole = UserRole.BEGINNER
    xp_points: int = 0
    level: int = 1
    
    # Role progression tracking
    predictions_made: int = 0
    successful_predictions: int = 0
    days_active: int = 0
    current_streak: int = 0
    max_streak: int = 0
    
    # Paper trading stats (for Paper Trader role)
    virtual_portfolio_value: float = 10000.0  # Starting amount
    total_trades: int = 0
    successful_trades: int = 0
    total_profit_loss: float = 0.0
    
    # Role upgrade eligibility (based on XP thresholds)
    role_upgrade_eligible: bool = False
    next_role: Optional[UserRole] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# Investment Goals (from Use Case: Set Investment Goals)
class InvestmentGoal(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    goal_name: str
    target_amount: float
    current_amount: float = 0.0
    target_date: Optional[datetime] = None
    category: str = "general"  # savings, retirement, house, etc.
    is_active: bool = True
    is_achieved: bool = False
    progress_percentage: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# AI Insights and Recommendations (from Use Case: A.I. Insight, Buy/Sell/Hold Recommendations)
class AIInsight(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    symbol: str
    insight_type: RecommendationType
    confidence_score: float  # 0.0 to 1.0
    reasoning: str
    
    # Supporting data from multiple models
    model_predictions: List[Dict[str, Any]] = []
    technical_indicators: Dict[str, float] = {}
    market_sentiment: str = "neutral"  # bullish, bearish, neutral
    
    # Price targets
    current_price: float
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    
    # Insight metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24))
    accuracy_score: Optional[float] = None  # Filled after validation

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# Paper Trading Portfolio (from Use Case: Simulate Trades)
class PaperTradingPortfolio(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    
    # Portfolio summary
    total_value: float = 10000.0  # Starting with $10,000 virtual money
    available_cash: float = 10000.0
    invested_amount: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Portfolio performance
    total_return_percent: float = 0.0
    daily_return_percent: float = 0.0
    best_performing_stock: Optional[str] = None
    worst_performing_stock: Optional[str] = None
    
    # Trading statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Risk metrics
    portfolio_beta: float = 1.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# Paper Trading Holdings
class PaperTradingHolding(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    portfolio_id: PyObjectId
    
    # Stock information
    symbol: str
    company_name: str
    
    # Position details
    quantity: int
    average_buy_price: float
    current_price: float = 0.0
    
    # Position value
    total_invested: float
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    
    # Position metadata
    first_purchase_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_trade_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# Trade History (from Use Case: Simulate Trades)
class TradeHistory(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    portfolio_id: PyObjectId
    
    # Trade details
    symbol: str
    trade_type: TradeType
    quantity: int
    price: float
    total_amount: float
    
    # Trade execution
    order_type: str = "market"  # market, limit, stop
    trade_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_price: float  # Actual execution price
    
    # Trade analysis
    profit_loss: Optional[float] = None  # For sell trades
    profit_loss_percent: Optional[float] = None
    holding_period_days: Optional[int] = None
    
    # Trade reasoning (optional)
    trade_reason: Optional[str] = None
    ai_recommendation_id: Optional[PyObjectId] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

# XP Activity Tracking
class XPActivity(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    
    # Activity details
    activity_type: XPActivityType
    activity_description: str
    xp_earned: int
    
    # Activity metadata
    related_entity_id: Optional[str] = None  # e.g., stock symbol, prediction ID
    related_entity_type: Optional[str] = None  # e.g., "stock", "prediction"
    multiplier: float = 1.0  # For bonus XP events
    
    # Timestamps
    earned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


# User Activity Log (for analytics and gamification)
class UserActivity(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    
    # Activity details
    activity_type: str  # login, prediction, trade, goal_complete, etc.
    activity_description: str
    
    # Activity metadata
    related_symbol: Optional[str] = None
    related_amount: Optional[float] = None
    xp_earned: int = 0
    
    # Session info
    session_duration: Optional[int] = None  # in minutes
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
