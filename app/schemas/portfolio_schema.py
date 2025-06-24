from pydantic import BaseModel
from typing import Optional
from ..enums import potfolio_enums

class PortfolioBase(BaseModel):
    user_id: int
    event_id: int
    quantity: int 
    type_of_share: potfolio_enums.ShareType

class PortfolioCreate(BaseModel):
    event_id: int
    quantity: int 
    type_of_share: potfolio_enums.ShareType
    

class PortfolioUpdate(BaseModel):
    user_id: Optional[int] = None
    event_id: Optional[int] = None
    quantity: Optional[int] = None
    type_of_share: Optional[potfolio_enums.ShareType] = None

class Portfolio(PortfolioBase):
    # Response schema - includes auto-generated fields
    id: int
    
    class Config:
        from_attributes = True

class PortfolioWithRelations(Portfolio):
    user: "User"  # Forward reference to User schema
    event: "Event"  # Forward reference to Event schema
    
    class Config:
        from_attributes = True

# If you need a simple portfolio response without relation details
class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    quantity: int
    type_of_share: potfolio_enums.ShareType
    
    class Config:
        from_attributes = True