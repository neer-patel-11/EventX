from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text , Boolean , Enum
from ..database import Base
from ..enums import portfolio_enums

class Portfolio(Base):
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer , ForeignKey("events.id"),nullable=False)
    quantity = Column(Integer , nullable=False)
    type_of_share = Column(Enum(portfolio_enums.ShareType),nullable=False)