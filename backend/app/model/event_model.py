from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text , Boolean , Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
from ..enums import event_enums


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(event_enums.EventStatus), default=event_enums.EventStatus.ONGOING, nullable=False)
    result = Column(Enum(event_enums.EventResult),nullable=True)
    # Relationship to User model
    creator = relationship("User", back_populates="events")