from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
from ..enums import trade_enums


class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    type_of_share = Column(Enum(trade_enums.TradeShareType), nullable=False)
    buyer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    buyer_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    seller_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    event = relationship("Event")
    buyer = relationship("User", foreign_keys=[buyer_user_id])
    seller = relationship("User", foreign_keys=[seller_user_id])
    buy_order = relationship("Order", foreign_keys=[buyer_order_id])
    sell_order = relationship("Order", foreign_keys=[seller_order_id])
