from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from ..enums import event_enums

class EventBase(BaseModel):
    title: str
    status: event_enums.EventStatus = event_enums.EventStatus.ONGOING
    result: Optional[event_enums.EventResult] = None

class EventCreate(EventBase):
    # Only fields that the client can provide when creating
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[event_enums.EventStatus] = None
    result: Optional[event_enums.EventResult] = None

class Event(EventBase):
    # Response schema - includes auto-generated fields
    id: int
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class EventWithCreator(Event):
    creator: "User"  # Forward reference to User schema
    
    class Config:
        from_attributes = True

# If you need a simple event response without creator details
class EventResponse(BaseModel):
    id: int
    title: str
    status: event_enums.EventStatus
    result: Optional[event_enums.EventResult]
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True