from pydantic import BaseModel, Field
from typing import Optional
from ..enums import order_enums

class OrderBase(BaseModel):
    event_id: int
    total_quantity: int = Field(..., gt=0, description="Total quantity must be greater than 0")
    price: int = Field(..., ge=1, le=10, description="Price must be between 1 and 10")
    type_of_share: order_enums.OrderShareType
    side: order_enums.OrderSide

class OrderCreate(OrderBase):
    # Only fields that the client can provide when creating
    # user_id will be set from current_user
    # filled_quantity defaults to 0
    # status defaults to INCOMPLETE
    pass

class OrderUpdate(BaseModel):
    event_id: Optional[int] = None
    total_quantity: Optional[int] = Field(None, gt=0, description="Total quantity must be greater than 0")
    filled_quantity: Optional[int] = Field(None, ge=0, description="Filled quantity must be non-negative")
    price: Optional[int] = Field(None, ge=1, le=10, description="Price must be between 1 and 10")
    type_of_share: Optional[order_enums.OrderShareType] = None
    side: Optional[order_enums.OrderSide] = None
    status: Optional[order_enums.OrderStatus] = None

class Order(OrderBase):
    # Response schema - includes auto-generated fields
    id: int
    user_id: int
    filled_quantity: int
    status: order_enums.OrderStatus
    
    class Config:
        from_attributes = True

class OrderWithRelations(Order):
    user: "User"  # Forward reference to User schema
    event: "Event"  # Forward reference to Event schema
    
    class Config:
        from_attributes = True

# If you need a simple order response without relation details
class OrderResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    total_quantity: int
    filled_quantity: int
    price: int
    type_of_share: order_enums.OrderShareType
    side: order_enums.OrderSide
    status: order_enums.OrderStatus
    
    class Config:
        from_attributes = True

# Schema for order status updates (commonly used in trading systems)
class OrderStatusUpdate(BaseModel):
    status: order_enums.OrderStatus
    filled_quantity: Optional[int] = Field(None, ge=0, description="Filled quantity must be non-negative")

# Schema for partial fill updates
class OrderFillUpdate(BaseModel):
    filled_quantity: int = Field(..., ge=0, description="Filled quantity must be non-negative")

# Schema for order summary/statistics
class OrderSummary(BaseModel):
    total_orders: int
    active_orders: int
    completed_orders: int
    cancelled_orders: int
    total_volume: int