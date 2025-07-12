from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum, CheckConstraint
from ..database import Base
from ..enums import order_enums

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    total_quantity = Column(Integer, nullable=False)
    filled_quantity = Column(Integer, nullable=False, default=0)
    price = Column(Integer, nullable=False)
    type_of_share = Column(Enum(order_enums.OrderShareType), nullable=False)
    side = Column(Enum(order_enums.OrderSide), nullable=False)
    status = Column(Enum(order_enums.OrderStatus), nullable=False, default=order_enums.OrderStatus.INCOMPLETE)
    
    __table_args__ = (
        CheckConstraint('price >= 1 AND price <= 10', name='check_price_range'),
    )