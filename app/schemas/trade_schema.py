from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from ..enums import trade_enums

class TradeBase(BaseModel):
    event_id: int
    price: int = Field(..., ge=1, le=10, description="Price must be between 1 and 10")
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")
    type_of_share: trade_enums.TradeShareType
    buyer_user_id: int
    seller_user_id: int

class TradeCreate(TradeBase):
    # Used internally by the trading engine - not exposed to users directly
    pass

class TradeUpdate(BaseModel):
    # Usually trades are immutable once executed, but keeping for completeness
    event_id: Optional[int] = None
    price: Optional[int] = Field(None, ge=1, le=10, description="Price must be between 1 and 10")
    quantity: Optional[int] = Field(None, gt=0, description="Quantity must be greater than 0")
    type_of_share: Optional[trade_enums.TradeShareType] = None
    buyer_user_id: Optional[int] = None
    seller_user_id: Optional[int] = None

class Trade(TradeBase):
    # Response schema - includes auto-generated fields
    id: int
    executed_at: datetime
    
    class Config:
        from_attributes = True

class TradeWithRelations(Trade):
    event: "Event"  # Forward reference to Event schema
    buyer: "User"   # Forward reference to User schema
    seller: "User"  # Forward reference to User schema
    
    class Config:
        from_attributes = True

# Simple trade response without relation details
class TradeResponse(BaseModel):
    id: int
    event_id: int
    price: int
    quantity: int
    type_of_share: trade_enums.TradeShareType
    buyer_user_id: int
    seller_user_id: int
    executed_at: datetime
    
    class Config:
        from_attributes = True

# Schema for trade statistics/summary
class TradeSummary(BaseModel):
    total_trades: int
    total_volume: int
    total_value: int
    average_price: float
    yes_trades: int
    no_trades: int

# Schema for user trade summary
class UserTradeSummary(BaseModel):
    user_id: int
    total_bought: int
    total_sold: int
    total_bought_value: int
    total_sold_value: int
    net_position: int

# Schema for event trade summary
class EventTradeSummary(BaseModel):
    event_id: int
    total_trades: int
    total_volume: int
    latest_price_yes: Optional[int] = None
    latest_price_no: Optional[int] = None
    price_trend: Optional[str] = None  # "up", "down", "stable"

# Schema for trade history query
class TradeHistoryQuery(BaseModel):
    event_id: Optional[int] = None
    user_id: Optional[int] = None
    type_of_share: Optional[trade_enums.TradeShareType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Limit must be between 1 and 1000")