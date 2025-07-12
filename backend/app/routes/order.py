# In your FastAPI endpoints:

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..schemas import order_schema, user_schema
from ..model import order_model
from ..service import auth, order , orderbook , event , user
from ..database import get_db
from ..enums import event_enums


router = APIRouter(prefix="/orders")


def validate_user(db:Session,user_id:int ,price:int , quant:int ):
    curUser = user.get_user_by_id(db,user_id)

    if curUser.current_balance >= price*quant:
        return True

    return False

def is_event_active(db:Session , event_id:int):
    curEnvent = event.get_event_by_id(db,event_id)

    if curEnvent.status == event_enums.EventStatus.ONGOING:
        return True
    
    return False

@router.post("/", response_model=order_schema.Order)
def create_order(order_data: order_schema.OrderCreate, 
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):
    
    if not validate_user(db, current_user.id ,order_data.price , order_data.total_quantity):
        return HTTPException("Insufficient balance")
    
    if not is_event_active(db,order_data.event_id):
        return HTTPException("Event is completed")

    
    db_order = order.create_order(db, order_data, current_user.id)

    
    return db_order


@router.get("/{order_id}", response_model=order_schema.Order)
def get_order(order_id: int,
              current_user: user_schema.User = Depends(auth.get_current_user),
              db: Session = Depends(get_db)):
    
    # take from memory
    db_order = order.get_order_by_id_from_memory(order_id)

    if db_order is None:
        db_order = order.get_order_by_id(db, order_id)
    
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns this order or is admin
    if db_order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return db_order

@router.get("/", response_model=list[order_schema.Order])
def get_user_orders(current_user: user_schema.User = Depends(auth.get_current_user),
                    db: Session = Depends(get_db)):
    
    return order.get_orders_by_user(db, current_user.id)

@router.get("/event/{event_id}", response_model=list[order_schema.Order])
def get_orders_by_event(event_id: int,
                        current_user: user_schema.User = Depends(auth.get_current_user),
                        db: Session = Depends(get_db)):
    
    if not current_user.is_admin:
        # Regular users can only see their own orders for an event
        return order.get_orders_by_user_and_event(db, current_user.id, event_id)
    else:
        # Admins can see all orders for an event
        return order.get_orders_by_event(db, event_id)


@router.put("/{order_id}", response_model=order_schema.Order)
def update_order(order_id: int,
                 order_update: order_schema.OrderUpdate,
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):
    
    if not is_event_active(db,order_data.event_id):
        return HTTPException("Event is completed")
    
    db_order = order.get_order_by_id(db, order_id)
    
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns this order or is admin
    if db_order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Prevent updating completed or cancelled orders
    if db_order.status in [order_schema.order_enums.OrderStatus.COMPLETELY_FILLED, 
                          order_schema.order_enums.OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update completed or cancelled orders"
        )

    updated_order = order.update_order(db, order_id, order_update)
    
    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return updated_order

@router.patch("/{order_id}/status", response_model=order_schema.Order)
def update_order_status(order_id: int,
                        status_update: order_schema.OrderStatusUpdate,
                        current_user: user_schema.User = Depends(auth.get_current_user),
                        db: Session = Depends(get_db)):
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can update order status"
        )
    
    updated_order = order.update_order_status(db, order_id, status_update)
    
    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return updated_order

@router.patch("/{order_id}/fill", response_model=order_schema.Order)
def update_order_fill(order_id: int,
                      fill_update: order_schema.OrderFillUpdate,
                      current_user: user_schema.User = Depends(auth.get_current_user),
                      db: Session = Depends(get_db)):
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can update order fills"
        )
    
    updated_order = order.update_order_fill(db, order_id, fill_update)
    
    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return updated_order

@router.delete("/{order_id}")
def cancel_order(order_id: int,
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):
    
    db_order = order.get_order_by_id(db, order_id)
    
    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns this order or is admin
    if db_order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Can only cancel incomplete or partially filled orders
    if db_order.status in [order_schema.order_enums.OrderStatus.COMPLETELY_FILLED, 
                          order_schema.order_enums.OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed or already cancelled orders"
        )

    cancelled_order = order.cancel_order(db, order_id)
    
    if not cancelled_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return {"message": "Order cancelled successfully"}

@router.get("/summary/user", response_model=order_schema.OrderSummary)
def get_user_order_summary(current_user: user_schema.User = Depends(auth.get_current_user),
                           db: Session = Depends(get_db)):
    
    return order.get_user_order_summary(db, current_user.id)