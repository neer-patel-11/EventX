# In your FastAPI endpoints:

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional

from ..schemas import trade_schema, user_schema
from ..model import trade_model
from ..service import auth, trade
from ..database import get_db
from ..enums import trade_enums


router = APIRouter(prefix="/trades")

@router.post("/", response_model=trade_schema.Trade)
def create_trade(trade_data: trade_schema.TradeCreate, 
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):
    """
    Create a new trade - Usually called by trading engine, not directly by users
    Only admins can create trades directly
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can create trades directly"
        )
    
    print("Creating trade request received")
    print(trade_data)
    
    db_trade = trade.create_trade(db, trade_data)
    return db_trade


@router.get("/{trade_id}", response_model=trade_schema.Trade)
def get_trade(trade_id: int,
              current_user: user_schema.User = Depends(auth.get_current_user),
              db: Session = Depends(get_db)):
    
    db_trade = trade.get_trade_by_id(db, trade_id)
    
    if not db_trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found"
        )
    
    # Users can only see trades they were involved in, admins can see all
    if (db_trade.buyer_user_id != current_user.id and 
        db_trade.seller_user_id != current_user.id and 
        not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return db_trade

@router.get("/", response_model=list[trade_schema.Trade])
def get_trades(event_id: Optional[int] = Query(None, description="Filter by event ID"),
               user_id: Optional[int] = Query(None, description="Filter by user ID (admin only)"),
               type_of_share: Optional[trade_enums.TradeShareType] = Query(None, description="Filter by share type"),
               limit: int = Query(100, ge=1, le=1000, description="Number of trades to return"),
               current_user: user_schema.User = Depends(auth.get_current_user),
               db: Session = Depends(get_db)):
    """
    Get trades with optional filters
    Regular users can only see their own trades
    Admins can see all trades and filter by any user
    """
    
    # If user_id filter is provided and user is not admin, deny access
    if user_id is not None and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can filter by user ID"
        )
    
    # If no user_id specified and user is not admin, show only their trades
    if user_id is None and not current_user.is_admin:
        user_id = current_user.id
    
    query_params = trade_schema.TradeHistoryQuery(
        event_id=event_id,
        user_id=user_id,
        type_of_share=type_of_share,
        limit=limit
    )
    
    return trade.get_trades_with_filters(db, query_params)

@router.get("/event/{event_id}", response_model=list[trade_schema.Trade])
def get_trades_by_event(event_id: int,
                        limit: int = Query(100, ge=1, le=1000),
                        current_user: user_schema.User = Depends(auth.get_current_user),
                        db: Session = Depends(get_db)):
    """Get all trades for a specific event - public endpoint"""
    
    return trade.get_trades_by_event(db, event_id, limit)

@router.get("/user/my-trades", response_model=list[trade_schema.Trade])
def get_my_trades(event_id: Optional[int] = Query(None),
                  limit: int = Query(100, ge=1, le=1000),
                  current_user: user_schema.User = Depends(auth.get_current_user),
                  db: Session = Depends(get_db)):
    """Get all trades for the current user"""
    
    return trade.get_trades_by_user(db, current_user.id, event_id, limit)

@router.get("/user/{user_id}/trades", response_model=list[trade_schema.Trade])
def get_user_trades(user_id: int,
                    event_id: Optional[int] = Query(None),
                    limit: int = Query(100, ge=1, le=1000),
                    current_user: user_schema.User = Depends(auth.get_current_user),
                    db: Session = Depends(get_db)):
    """Get trades for a specific user - admin only"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can view other users' trades"
        )
    
    return trade.get_trades_by_user(db, user_id, event_id, limit)

@router.get("/summary/event/{event_id}", response_model=trade_schema.EventTradeSummary)
def get_event_trade_summary(event_id: int,
                            current_user: user_schema.User = Depends(auth.get_current_user),
                            db: Session = Depends(get_db)):
    """Get trade summary for a specific event - public endpoint"""
    
    return trade.get_event_trade_summary(db, event_id)

@router.get("/summary/user", response_model=trade_schema.UserTradeSummary)
def get_user_trade_summary(event_id: Optional[int] = Query(None),
                           current_user: user_schema.User = Depends(auth.get_current_user),
                           db: Session = Depends(get_db)):
    """Get trade summary for the current user"""
    
    return trade.get_user_trade_summary(db, current_user.id, event_id)

@router.get("/summary/user/{user_id}", response_model=trade_schema.UserTradeSummary)
def get_specific_user_trade_summary(user_id: int,
                                    event_id: Optional[int] = Query(None),
                                    current_user: user_schema.User = Depends(auth.get_current_user),
                                    db: Session = Depends(get_db)):
    """Get trade summary for a specific user - admin only"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can view other users' trade summaries"
        )
    
    return trade.get_user_trade_summary(db, user_id, event_id)

@router.get("/latest/event/{event_id}", response_model=list[trade_schema.Trade])
def get_latest_trades_by_event(event_id: int,
                               limit: int = Query(10, ge=1, le=100),
                               current_user: user_schema.User = Depends(auth.get_current_user),
                               db: Session = Depends(get_db)):
    """Get latest trades for an event - useful for price discovery"""
    
    return trade.get_latest_trades_by_event(db, event_id, limit)

@router.put("/{trade_id}", response_model=trade_schema.Trade)
def update_trade(trade_id: int,
                 trade_update: trade_schema.TradeUpdate,
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):
    """
    Update a trade - Usually trades are immutable, only admin can update
    Use with extreme caution as it affects historical data
    """
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can update trades"
        )
    
    updated_trade = trade.update_trade(db, trade_id, trade_update)
    
    if not updated_trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found"
        )

    return updated_trade

@router.delete("/{trade_id}")
def delete_trade(trade_id: int,
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):
    """
    Delete a trade - Use with extreme caution as it affects historical data
    Only admin can delete trades
    """
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete trades"
        )

    deleted_trade = trade.delete_trade(db, trade_id)
    
    if not deleted_trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found"
        )

    return {"message": "Trade deleted successfully"}