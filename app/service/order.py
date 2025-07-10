from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..enums import order_enums
from ..model import order_model
from ..schemas import order_schema
from ..service.redis_service import getFromMap


def get_order_by_id_from_memory(order_id:int)->order_model.Order:
    return getFromMap(order_id)



def get_order_by_id(db: Session, order_id: int):
    """Get order by ID"""
    return db.query(order_model.Order).filter(
        order_model.Order.id == order_id
    ).first()

def get_orders_by_user(db: Session, user_id: int):
    """Get all orders for a specific user"""
    return db.query(order_model.Order).filter(
        order_model.Order.user_id == user_id
    ).order_by(order_model.Order.id.desc()).all()

def get_orders_by_event(db: Session, event_id: int):
    """Get all orders for a specific event"""
    return db.query(order_model.Order).filter(
        order_model.Order.event_id == event_id
    ).order_by(order_model.Order.id.desc()).all()

def get_orders_by_user_and_event(db: Session, user_id: int, event_id: int):
    """Get all orders for a user in a specific event"""
    return db.query(order_model.Order).filter(
        and_(
            order_model.Order.user_id == user_id,
            order_model.Order.event_id == event_id
        )
    ).order_by(order_model.Order.id.desc()).all()

def get_active_orders_by_user(db: Session, user_id: int):
    """Get all active (incomplete/partially filled) orders for a user"""
    return db.query(order_model.Order).filter(
        and_(
            order_model.Order.user_id == user_id,
            or_(
                order_model.Order.status == order_enums.OrderStatus.INCOMPLETE,
                order_model.Order.status == order_enums.OrderStatus.PARTIAL_FILLED
            )
        )
    ).order_by(order_model.Order.id.desc()).all()

def get_active_orders_by_event(db: Session, event_id: int):
    """Get all active orders for a specific event"""
    return db.query(order_model.Order).filter(
        and_(
            order_model.Order.event_id == event_id,
            or_(
                order_model.Order.status == order_enums.OrderStatus.INCOMPLETE,
                order_model.Order.status == order_enums.OrderStatus.PARTIAL_FILLED
            )
        )
    ).order_by(order_model.Order.price.desc(), order_model.Order.id.asc()).all()

def create_order(db: Session, order_data: order_schema.OrderCreate, user_id: int):
    """Create a new order"""
    db_order = order_model.Order(
        **order_data.dict(),
        user_id=user_id,
        filled_quantity=0,
        status=order_enums.OrderStatus.INCOMPLETE
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    return db_order

def update_order(db: Session, order_id: int, order_update: order_schema.OrderUpdate):
    """Update an existing order"""
    db_order = db.query(order_model.Order).filter(
        order_model.Order.id == order_id
    ).first()
    
    if not db_order:
        return None
    
    # Update only the fields that are provided (not None)
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)
    
    # Auto-update status based on filled quantity if filled_quantity is updated
    if 'filled_quantity' in update_data:
        db_order.status = _calculate_order_status(db_order.total_quantity, db_order.filled_quantity)
    
    db.commit()
    db.refresh(db_order)
    return db_order

def update_order_status(db: Session, order_id: int, status_update: order_schema.OrderStatusUpdate):
    """Update order status and optionally filled quantity"""
    db_order = db.query(order_model.Order).filter(
        order_model.Order.id == order_id
    ).first()
    
    if not db_order:
        return None
    
    db_order.status = status_update.status
    
    if status_update.filled_quantity is not None:
        db_order.filled_quantity = status_update.filled_quantity
        # Validate that status matches filled quantity
        calculated_status = _calculate_order_status(db_order.total_quantity, db_order.filled_quantity)
        if status_update.status != calculated_status and status_update.status != order_enums.OrderStatus.CANCELLED:
            db_order.status = calculated_status
    
    db.commit()
    db.refresh(db_order)
    return db_order

def update_order_fill(db: Session, order_id: int, fill_update: order_schema.OrderFillUpdate):
    """Update order filled quantity and auto-calculate status"""
    db_order = db.query(order_model.Order).filter(
        order_model.Order.id == order_id
    ).first()
    
    if not db_order:
        return None
    
    # Validate filled quantity doesn't exceed total quantity
    if fill_update.filled_quantity > db_order.total_quantity:
        raise ValueError("Filled quantity cannot exceed total quantity")
    
    db_order.filled_quantity = fill_update.filled_quantity
    db_order.status = _calculate_order_status(db_order.total_quantity, db_order.filled_quantity)
    
    db.commit()
    db.refresh(db_order)
    return db_order

def cancel_order(db: Session, order_id: int):
    """Cancel an order"""
    db_order = db.query(order_model.Order).filter(
        order_model.Order.id == order_id
    ).first()
    
    if not db_order:
        return None
    
    db_order.status = order_enums.OrderStatus.CANCELLED
    db.commit()
    db.refresh(db_order)
    return db_order

def delete_order(db: Session, order_id: int):
    """Delete an order (use with caution - usually prefer cancelling)"""
    db_order = db.query(order_model.Order).filter(
        order_model.Order.id == order_id
    ).first()
    
    if not db_order:
        return None
    
    db.delete(db_order)
    db.commit()
    return db_order

def get_user_order_summary(db: Session, user_id: int):
    """Get order summary statistics for a user"""
    orders = db.query(order_model.Order).filter(
        order_model.Order.user_id == user_id
    ).all()
    
    total_orders = len(orders)
    active_orders = len([o for o in orders if o.status in [
        order_enums.OrderStatus.INCOMPLETE, 
        order_enums.OrderStatus.PARTIAL_FILLED
    ]])
    completed_orders = len([o for o in orders if o.status == order_enums.OrderStatus.COMPLETELY_FILLED])
    cancelled_orders = len([o for o in orders if o.status == order_enums.OrderStatus.CANCELLED])
    total_volume = sum([o.total_quantity for o in orders])
    
    return order_schema.OrderSummary(
        total_orders=total_orders,
        active_orders=active_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        total_volume=total_volume
    )

def get_matching_orders(db: Session, event_id: int, share_type: order_enums.OrderShareType, 
                       side: order_enums.OrderSide, price: int):
    """Get orders that can potentially match with a new order (for trading engine)"""
    opposite_side = order_enums.OrderSide.SELL if side == order_enums.OrderSide.BUY else order_enums.OrderSide.BUY
    
    query = db.query(order_model.Order).filter(
        and_(
            order_model.Order.event_id == event_id,
            order_model.Order.type_of_share == share_type,
            order_model.Order.side == opposite_side,
            or_(
                order_model.Order.status == order_enums.OrderStatus.INCOMPLETE,
                order_model.Order.status == order_enums.OrderStatus.PARTIAL_FILLED
            )
        )
    )
    
    # For buy orders, match with sell orders at or below the price
    # For sell orders, match with buy orders at or above the price
    if side == order_enums.OrderSide.BUY:
        query = query.filter(order_model.Order.price <= price)
        query = query.order_by(order_model.Order.price.asc(), order_model.Order.id.asc())
    else:
        query = query.filter(order_model.Order.price >= price)
        query = query.order_by(order_model.Order.price.desc(), order_model.Order.id.asc())
    
    return query.all()

def _calculate_order_status(total_quantity: int, filled_quantity: int) -> order_enums.OrderStatus:
    """Helper function to calculate order status based on quantities"""
    if filled_quantity == 0:
        return order_enums.OrderStatus.INCOMPLETE
    elif filled_quantity < total_quantity:
        return order_enums.OrderStatus.PARTIAL_FILLED
    else:
        return order_enums.OrderStatus.COMPLETELY_FILLED