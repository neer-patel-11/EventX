from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import Optional, List

from ..enums import trade_enums
from ..model import trade_model
from ..schemas import trade_schema

def get_trade_by_id(db: Session, trade_id: int):
    """Get trade by ID"""
    return db.query(trade_model.Trade).filter(
        trade_model.Trade.id == trade_id
    ).first()

def get_trades_by_user(db: Session, user_id: int, event_id: Optional[int] = None, limit: int = 100):
    """Get all trades for a specific user (as buyer or seller)"""
    query = db.query(trade_model.Trade).filter(
        or_(
            trade_model.Trade.buyer_user_id == user_id,
            trade_model.Trade.seller_user_id == user_id
        )
    )
    
    if event_id:
        query = query.filter(trade_model.Trade.event_id == event_id)
    
    return query.order_by(desc(trade_model.Trade.executed_at)).limit(limit).all()

def get_trades_by_event(db: Session, event_id: int, limit: int = 100):
    """Get all trades for a specific event"""
    return db.query(trade_model.Trade).filter(
        trade_model.Trade.event_id == event_id
    ).order_by(desc(trade_model.Trade.executed_at)).limit(limit).all()

def get_latest_trades_by_event(db: Session, event_id: int, limit: int = 10):
    """Get latest trades for an event - useful for price discovery"""
    return db.query(trade_model.Trade).filter(
        trade_model.Trade.event_id == event_id
    ).order_by(desc(trade_model.Trade.executed_at)).limit(limit).all()

def get_trades_with_filters(db: Session, query_params: trade_schema.TradeHistoryQuery):
    """Get trades with various filters"""
    query = db.query(trade_model.Trade)
    
    if query_params.event_id:
        query = query.filter(trade_model.Trade.event_id == query_params.event_id)
    
    if query_params.user_id:
        query = query.filter(
            or_(
                trade_model.Trade.buyer_user_id == query_params.user_id,
                trade_model.Trade.seller_user_id == query_params.user_id
            )
        )
    
    if query_params.type_of_share:
        query = query.filter(trade_model.Trade.type_of_share == query_params.type_of_share)
    
    if query_params.start_date:
        query = query.filter(trade_model.Trade.executed_at >= query_params.start_date)
    
    if query_params.end_date:
        query = query.filter(trade_model.Trade.executed_at <= query_params.end_date)
    
    limit = query_params.limit or 100
    return query.order_by(desc(trade_model.Trade.executed_at)).limit(limit).all()

def create_trade(db: Session, trade_data: trade_schema.TradeCreate):
    """Create a new trade"""
    db_trade = trade_model.Trade(**trade_data.dict())
    
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

def update_trade(db: Session, trade_id: int, trade_update: trade_schema.TradeUpdate):
    """Update an existing trade (use with caution - trades are usually immutable)"""
    db_trade = db.query(trade_model.Trade).filter(
        trade_model.Trade.id == trade_id
    ).first()
    
    if not db_trade:
        return None
    
    # Update only the fields that are provided (not None)
    update_data = trade_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_trade, field, value)
    
    db.commit()
    db.refresh(db_trade)
    return db_trade

def delete_trade(db: Session, trade_id: int):
    """Delete a trade (use with extreme caution)"""
    db_trade = db.query(trade_model.Trade).filter(
        trade_model.Trade.id == trade_id
    ).first()
    
    if not db_trade:
        return None
    
    db.delete(db_trade)
    db.commit()
    return db_trade

def get_event_trade_summary(db: Session, event_id: int) -> trade_schema.EventTradeSummary:
    """Get trade summary for a specific event"""
    trades = db.query(trade_model.Trade).filter(
        trade_model.Trade.event_id == event_id
    ).all()
    
    if not trades:
        return trade_schema.EventTradeSummary(
            event_id=event_id,
            total_trades=0,
            total_volume=0,
            latest_price_yes=None,
            latest_price_no=None,
            price_trend=None
        )
    
    total_trades = len(trades)
    total_volume = sum([t.quantity for t in trades])
    
    # Get latest prices for YES and NO shares
    latest_yes_trade = db.query(trade_model.Trade).filter(
        and_(
            trade_model.Trade.event_id == event_id,
            trade_model.Trade.type_of_share == trade_enums.TradeShareType.YES
        )
    ).order_by(desc(trade_model.Trade.executed_at)).first()
    
    latest_no_trade = db.query(trade_model.Trade).filter(
        and_(
            trade_model.Trade.event_id == event_id,
            trade_model.Trade.type_of_share == trade_enums.TradeShareType.NO
        )
    ).order_by(desc(trade_model.Trade.executed_at)).first()
    
    latest_price_yes = latest_yes_trade.price if latest_yes_trade else None
    latest_price_no = latest_no_trade.price if latest_no_trade else None
    
    # Calculate price trend (simplified - you might want more sophisticated logic)
    price_trend = _calculate_price_trend(db, event_id)
    
    return trade_schema.EventTradeSummary(
        event_id=event_id,
        total_trades=total_trades,
        total_volume=total_volume,
        latest_price_yes=latest_price_yes,
        latest_price_no=latest_price_no,
        price_trend=price_trend
    )

def get_user_trade_summary(db: Session, user_id: int, event_id: Optional[int] = None) -> trade_schema.UserTradeSummary:
    """Get trade summary for a specific user"""
    query = db.query(trade_model.Trade).filter(
        or_(
            trade_model.Trade.buyer_user_id == user_id,
            trade_model.Trade.seller_user_id == user_id
        )
    )
    
    if event_id:
        query = query.filter(trade_model.Trade.event_id == event_id)
    
    trades = query.all()
    
    bought_trades = [t for t in trades if t.buyer_user_id == user_id]
    sold_trades = [t for t in trades if t.seller_user_id == user_id]
    
    total_bought = sum([t.quantity for t in bought_trades])
    total_sold = sum([t.quantity for t in sold_trades])
    total_bought_value = sum([t.quantity * t.price for t in bought_trades])
    total_sold_value = sum([t.quantity * t.price for t in sold_trades])
    
    net_position = total_bought - total_sold
    
    return trade_schema.UserTradeSummary(
        user_id=user_id,
        total_bought=total_bought,
        total_sold=total_sold,
        total_bought_value=total_bought_value,
        total_sold_value=total_sold_value,
        net_position=net_position
    )

def get_trade_summary(db: Session, event_id: Optional[int] = None) -> trade_schema.TradeSummary:
    """Get overall trade summary"""
    query = db.query(trade_model.Trade)
    
    if event_id:
        query = query.filter(trade_model.Trade.event_id == event_id)
    
    trades = query.all()
    
    if not trades:
        return trade_schema.TradeSummary(
            total_trades=0,
            total_volume=0,
            total_value=0,
            average_price=0.0,
            yes_trades=0,
            no_trades=0
        )
    
    total_trades = len(trades)
    total_volume = sum([t.quantity for t in trades])
    total_value = sum([t.quantity * t.price for t in trades])
    average_price = total_value / total_volume if total_volume > 0 else 0.0
    
    yes_trades = len([t for t in trades if t.type_of_share == trade_enums.TradeShareType.YES])
    no_trades = len([t for t in trades if t.type_of_share == trade_enums.TradeShareType.NO])
    
    return trade_schema.TradeSummary(
        total_trades=total_trades,
        total_volume=total_volume,
        total_value=total_value,
        average_price=average_price,
        yes_trades=yes_trades,
        no_trades=no_trades
    )

def get_price_history(db: Session, event_id: int, share_type: trade_enums.TradeShareType, limit: int = 100):
    """Get price history for a specific event and share type"""
    return db.query(trade_model.Trade).filter(
        and_(
            trade_model.Trade.event_id == event_id,
            trade_model.Trade.type_of_share == share_type
        )
    ).order_by(desc(trade_model.Trade.executed_at)).limit(limit).all()

def get_volume_by_price(db: Session, event_id: int, share_type: trade_enums.TradeShareType):
    """Get volume traded at each price point"""
    result = db.query(
        trade_model.Trade.price,
        func.sum(trade_model.Trade.quantity).label('total_volume')
    ).filter(
        and_(
            trade_model.Trade.event_id == event_id,
            trade_model.Trade.type_of_share == share_type
        )
    ).group_by(trade_model.Trade.price).all()
    
    return [{"price": r.price, "volume": r.total_volume} for r in result]

def _calculate_price_trend(db: Session, event_id: int) -> Optional[str]:
    """Calculate price trend for an event (simplified logic)"""
    recent_trades = db.query(trade_model.Trade).filter(
        trade_model.Trade.event_id == event_id
    ).order_by(desc(trade_model.Trade.executed_at)).limit(10).all()
    
    if len(recent_trades) < 2:
        return "stable"
    
    # Compare average price of first 5 vs last 5 trades
    if len(recent_trades) >= 10:
        recent_avg = sum([t.price for t in recent_trades[:5]]) / 5
        older_avg = sum([t.price for t in recent_trades[5:10]]) / 5
        
        if recent_avg > older_avg * 1.05:  # 5% threshold
            return "up"
        elif recent_avg < older_avg * 0.95:  # 5% threshold
            return "down"
        else:
            return "stable"
    
    return "stable"