from sqlalchemy.orm import Session

from ..schemas import event_schema , portfolio_schema , trade_schema , order_schema
from ..model import event_model , user_model
from ..service.trade import create_trade
from ..service.portfolio import get_portfolios_by_event , create_portfolio
from ..service.user import add_to_user_balance , deduct_from_user_balance
from ..enums import portfolio_enums , event_enums , trade_enums , order_enums
from ..service.order import cancel_order , get_active_orders_by_event , create_order
from ..service.redis_service import removeFromMap , freeQueue
import asyncio
from ..routes import orderbook  


def get_event_by_id(db: Session, id: int):
    return db.query(event_model.Event).filter(event_model.Event.id == id).first()

def get_all_events(db: Session):
    events = db.query(event_model.Event).all()
    return events

def getQueueName(id , side , type , price):
    return str(id)+"X"+str(side)+"X"+str(type)+"X"+price

def update_event(db: Session, id: int, event: event_schema.EventUpdate):
    # Get the existing event
    db_event = db.query(event_model.Event).filter(event_model.Event.id == id).first()
    
    if not db_event:
        return None
    
    # Update only the fields that are provided (not None)
    update_data = event.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_event, field, value)
    
    db.commit()
    db.refresh(db_event)
    return db_event

def delete_event(db: Session, id: int):
    db_event = db.query(event_model.Event).filter(event_model.Event.id == id).first()
    
    if not db_event:
        return None
    
    db.delete(db_event)
    db.commit()
    return db_event


def event_completed(db:Session,event_id:int,event:event_schema.EventUpdate , admin_id:int):

    # give money to the winners and remove trade from portfolio (add a trade object with admin)
    remove_from_portfolio(db,event_id,event,admin_id)

    # cancel all the current incompleted order's -> free memory
    cancel_all_order(db,event_id)

    free_all_queue(event_id)

    return True

def free_all_queue(event_id:int):
    for i in range(1,11):
        freeQueue(getQueueName(event_id,order_enums.OrderSide.BUY,order_enums.OrderShareType.NO , i))
        freeQueue(getQueueName(event_id,order_enums.OrderSide.BUY,order_enums.OrderShareType.YES , i))
        freeQueue(getQueueName(event_id,order_enums.OrderSide.SELL,order_enums.OrderShareType.YES , i))
        freeQueue(getQueueName(event_id,order_enums.OrderSide.SELL,order_enums.OrderShareType.NO , i))

def cancel_all_order(db:Session , event_id:int):
    # get all active orders

    orders:list[order_schema.Order]=get_active_orders_by_event(db,event_id)

    asyncio.create_task(orderbook.close_event_connections(event_id))

    for order in orders:
        # change status to cancel
        cancel_order(db , order.id)

        # remove from memory
        removeFromMap(order.id)


def remove_from_portfolio(db:Session ,event_id:int , event: event_schema.EventUpdate , admin_id:int):

    # retreive all the portfolio associated with event_id

    portfolios:list[portfolio_schema.Portfolio] = get_portfolios_by_event(db,event_id)

    for portfolio in portfolios:
        

        if event.result == event_enums.EventResult.DRAW:
            # add 5 to everyone

            type_of_share = trade_enums.TradeShareType.YES

            if portfolio.type_of_share == portfolio_enums.ShareType.NO :
                type_of_share = trade_enums.TradeShareType.NO

            # both are on same side
            trade_data = trade_schema.TradeCreate(
                event_id = event_id,
                price= 5,
                quantity =portfolio.quantity,
                type_of_share = type_of_share,
                buyer_user_id = admin_id,
                seller_user_id = portfolio.user_id,
                buyer_order_id = None,
                seller_order_id= None

            )

            create_trade(db,trade_data)

            # add money to user account

            amount = 5 * portfolio.quantity
            
            # add balance to user 
            add_to_user_balance(db , portfolio.user_id , amount)
            # deduct from admin
            deduct_from_user_balance(db , admin_id , amount)




        # share and result are on the same side

        elif (portfolio.type_of_share == portfolio_enums.ShareType.NO and event.result == event_enums.EventResult.NO) or (portfolio.type_of_share == portfolio_enums.ShareType.YES and event.result == event_enums.EventResult.YES):

            type_of_share = trade_enums.TradeShareType.YES

            if portfolio.type_of_share == portfolio_enums.ShareType.NO :
                type_of_share = trade_enums.TradeShareType.NO


            # both are on same side
            trade_data = trade_schema.TradeCreate(
                event_id = event_id,
                price= 10,
                quantity =portfolio.quantity,
                type_of_share = type_of_share,
                buyer_user_id = admin_id,
                seller_user_id = portfolio.user_id,
                buyer_order_id = None,
                seller_order_id= None

            )

            create_trade(db,trade_data)

            # add money to user account

            amount = 10 * portfolio.quantity
            
            # add balance to user 
            add_to_user_balance(db , portfolio.user_id , amount)
            # deduct from admin
            deduct_from_user_balance(db , admin_id , amount)

        else:

            type_of_share = trade_enums.TradeShareType.YES

            if portfolio.type_of_share == portfolio_enums.ShareType.NO :
                type_of_share = trade_enums.TradeShareType.NO


            # both are on same side
            trade_data = trade_schema.TradeCreate(
                event_id = event_id,
                price= 0,
                quantity =portfolio.quantity,
                type_of_share = type_of_share,
                buyer_user_id = admin_id,
                seller_user_id = portfolio.user_id,
                buyer_order_id = None,
                seller_order_id= None

            )

            create_trade(db,trade_data)

            # add money to user account

            amount = 10 * portfolio.quantity
            
            # add balance to admin
            add_to_user_balance(db , admin_id , amount)
            # deduct from user
            deduct_from_user_balance(db , portfolio.user_id , amount)


def flood_initial_shares(db:Session , event:event_schema.Event , initial_quant:int , user_id:int):

    # add share in admin portfolio
    create_portfolio(db,portfolio_schema.PortfolioCreate(event.id,initial_quant ,portfolio_enums.ShareType.YES ),user_id)

    create_portfolio(db,portfolio_schema.PortfolioCreate(event.id,initial_quant ,portfolio_enums.ShareType.NO ),user_id)

    # flood them all and sell share at 5 each
    create_order(db,order_schema.OrderCreate(event.id , initial_quant,5,order_enums.OrderShareType.NO,order_enums.OrderSide.SELL),user_id)

    create_order(db,order_schema.OrderCreate(event.id , initial_quant,5,order_enums.OrderShareType.YES,order_enums.OrderSide.SELL),user_id)





