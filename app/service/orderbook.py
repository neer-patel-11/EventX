from ..schemas import order_schema,trade_schema,user_schema,event_schema,portfolio_schema

from redis_service import addLock,addToMap,getFromMap,isLocked,isQueueEmpty,peekToQueue,popToQueue,pushToQueue , removeLock , removeFromMap , updateMap

from fastapi import Depends

from ..enums import order_enums , portfolio_enums

from order import update_order

from trade import create_trade

from portfolio import create_portfolio , update_portfolio_quantity , get_portfolio_by_user_event_share

from sqlalchemy.orm import Session

from ..database import get_db

from user import add_to_user_balance , deduct_from_user_balance

import asyncio

from ..routes.orderbook import broadcast_orderbook_update

from typing import Dict, List, Optional

def getQueueName(id , side , type , price):
    return str(id)+"X"+str(side)+"X"+str(type)+"X"+price


def addOrder(order:order_schema.Order):
    # add to memory
    
    addToMap(order,order.id)
    
    # check if we can execute the order

    excuteOrder(order)
    

    db = next(get_db())

    # check if order is execute whole or partial

    updatedOrder:order_schema.Order = getFromMap(order.id)

    # Get updated orderbook data
    update_data = get_orderbook_update_data(order.event_id, db)
        
    # Broadcast to all connected clients for this event
    asyncio.create_task(broadcast_orderbook_update(order.event_id, update_data))
     

    if updatedOrder.filled_quantity == updatedOrder.total_quantity :
        return persistOrderInDb(updatedOrder)
         
    else:
        if updatedOrder.filled_quantity == 0:
            updatedOrder.status = order_enums.OrderStatus.INCOMPLETE
        else:
            updatedOrder.status = order_enums.OrderStatus.PARTIALFILLED

        # add to queue

        return addOrderToQueue(updatedOrder)


def addOrderToQueue(order:order_schema.Order):

    queueName = getQueueName(order.event_id,order.side,order.type_of_share,order.price)

    # wait until we get the lock
    while True:
        isUnlockedLocked = addLock(queueName)

        if isUnlockedLocked:
            break
        
    
    result = pushToQueue(queueName,order.id)
    
    removeLock(queueName)

    db: Session = Depends(get_db)

    update_data = get_orderbook_update_data(order.event_id, db)
    asyncio.create_task(broadcast_orderbook_update(order.event_id, update_data))

    
    return result


def getBestQueue(price:int,side:str,type:str,event_id:int)->str:

    if side == order_enums.OrderSide.BUY:
        
        for i in range(1,price+1):
            if isQueueEmpty(getQueueName(event_id,order_enums.OrderSide.SELL,type,i)) == False:
                return getQueueName(event_id,order_enums.OrderSide.SELL,type,i)
    
    elif side == order_enums.OrderSide.SELL:

        for i in range(10,price-1 ,-1):
            if isQueueEmpty(getQueueName(event_id,order_enums.OrderSide.BUY,type,i)) == False:
                return getQueueName(event_id,order_enums.OrderSide.BUY,type,i)

    return None

def excuteOrder(order:order_schema.Order):

    # get all the non empty queue which has price less than equal to order.price
    
    while order.filled_quantity < order.total_quantity:

        # get best queue

        queueName = getBestQueue(order.price,order.side,order.type_of_share)

        if queueName == None:
            break
        
        while True:
                isUnlockedLocked = addLock(queueName)

                if isUnlockedLocked:
                    break

        while (isQueueEmpty(queueName) == False) and (order.filled_quantity < order.total_quantity) :
            
            curElementId = peekToQueue(queueName)

            curElement:order_schema.Order = getFromMap(curElementId)

            curElementRemainingQuant = curElement.total_quantity - curElement.filled_quantity

            tradedQuant = min(curElementRemainingQuant , (order.total_quantity - order.filled_quantity))

            addTrade(tradedQuant , curElement.price , curElement , order)
            
            order.filled_quantity += tradedQuant
            curElement.filled_quantity += tradedQuant

            updateMap(order, order.id)
            updateMap(curElement, curElement.id)


            if curElement.filled_quantity == curElement.total_quantity:
                popToQueue(queueName)
                # if poping from queue make changes in db
                persistOrderInDb(curElement)
                removeFromMap(curElement.id)

            else:
                # change status of order into partially filled
                order.status = order_enums.OrderStatus.PARTIALFILLED
                curElement.status = order_enums.OrderStatus.PARTIALFILLED
                updateMap(order, order.id)
                updateMap(curElement, curElement.id)

        
        removeLock(queueName)
            

def addTrade(quant:int , price:int, order1:order_schema.Order , order2:order_schema.Order)->bool:

    if (order1.event_id != order2.event_id) or (order1.type_of_share != order2.type_of_share):
        return False

    buyer_user_id = None , seller_user_id = None
    buyer_order_id = None , seller_order_id = None


    if(order1.side == order_enums.OrderSide.BUY and order2.side == order_enums.OrderSide.SELL):
        buyer_user_id = order1.user_id
        seller_user_id = order2.user_id

        buyer_order_id = order1.id
        seller_order_id = order2.id
        
    elif(order1.side == order_enums.OrderSide.SELL and order2.side == order_enums.OrderSide.BUY):
        buyer_user_id = order2.user_id
        seller_user_id = order1.user_id

        buyer_order_id = order2.id
        seller_order_id = order1.id
        

    else:
        return False
    
    trade:trade_schema.TradeCreate = trade_schema.TradeCreate(
        event_id= order1.event_id,
        price = price,
        quantity= quant,
        buyer_user_id = buyer_user_id,
        seller_user_id = seller_user_id,
        buyer_order_id=buyer_order_id,
        seller_order_id=seller_order_id
    )
    db: Session = Depends(get_db)

    create_trade(db , trade)


    # for buyer add the share to portfolio

    typeOfShare:portfolio_enums.ShareType = None

    if(order1.type_of_share == order_enums.OrderShareType.NO):
        typeOfShare = portfolio_enums.ShareType.NO
    elif(order1.type_of_share == order_enums.OrderShareType.YES):
        typeOfShare = portfolio_enums.ShareType.YES


    addToPortfolio(buyer_user_id , quant ,typeOfShare , order1.event_id )

    # for seller update share quant from portfolio

    updateProtfolio(seller_user_id,quant , typeOfShare , order1.event_id)


    # update current balance from both seller and buyer

    amount = quant * price
    db: Session = Depends(get_db)

    add_to_user_balance(db , seller_user_id , amount)

    deduct_from_user_balance(db , buyer_user_id , amount)


    update_data = get_orderbook_update_data(order1.event_id, db)
    asyncio.create_task(broadcast_orderbook_update(order1.event_id, update_data))

    

    return True

def addToPortfolio(user_id:int , quant:int , typeOfShare:portfolio_enums.ShareType , event_id:int):

    db: Session = Depends(get_db)

    portfolio = get_portfolio_by_user_event_share(db , user_id , event_id , typeOfShare)

    # if portfolio exist then add to current quant
    if portfolio != None :
        update_portfolio_quantity(db ,portfolio.id ,portfolio.quantity + quant)
        
    
    # if adding for first time then create a portfolio entry
    else :

        portfolio:portfolio_schema.PortfolioCreate = portfolio_schema.PortfolioCreate(
            event_id=event_id,
            quantity=quant,
            type_of_share=typeOfShare
        )
        

        create_portfolio(db ,portfolio,user_id)

def updateProtfolio(user_id:int, quant:int ,typeOfShare:portfolio_enums.ShareType , event_id:int ):

    db: Session = Depends(get_db)

    portfolio = get_portfolio_by_user_event_share(db , user_id , event_id , typeOfShare)

    update_portfolio_quantity(db ,portfolio.id ,portfolio.quantity - quant)
            
def persistOrderInDb(updatedOrder:order_schema.Order):
    if updatedOrder.filled_quantity == updatedOrder.total_quantity :
        updatedOrder.status = order_enums.OrderStatus.COMPLETELYFILLED
        # update this order in db and the remove from redis

        if removeFromMap(updatedOrder.id) == True:
            # now change this in db
            db: Session = Depends(get_db)

            updateOrderObj:order_schema.OrderUpdate=order_schema.OrderUpdate(
                event_id= updatedOrder.event_id,
                total_quantity=updatedOrder.total_quantity,
                filled_quantity=updatedOrder.filled_quantity,
                price=updatedOrder.price,
                type_of_share=updatedOrder.type_of_share,
                side= updatedOrder.side,
                status= updatedOrder.status
            )

            update_order(db,updatedOrder.id,updateOrderObj)
        
        else:
            raise Exception("Not able to delete from memory")
        
        return True
    
    return False

            



# websocket code

def get_orderbook_snapshot(event_id: int, db: Session) -> Dict:
    """
    Get complete L2 orderbook snapshot for an event
    Returns both YES and NO orderbooks
    """
    try:
        orderbook = {
            "YES": {
                "bids": [],  # Buy orders
                "asks": []   # Sell orders
            },
            "NO": {
                "bids": [],  # Buy orders  
                "asks": []   # Sell orders
            }
        }
        
        # Get orderbook for YES shares
        yes_orderbook = _get_orderbook_for_share_type(event_id, order_enums.OrderShareType.YES)
        orderbook["YES"] = yes_orderbook
        
        # Get orderbook for NO shares
        no_orderbook = _get_orderbook_for_share_type(event_id, order_enums.OrderShareType.NO)
        orderbook["NO"] = no_orderbook
        
        # Add market summary
        orderbook["market_summary"] = _get_market_summary(orderbook)
        
        return orderbook
        
    except Exception as e:
        print(f"Error getting orderbook snapshot: {e}")
        return {
            "YES": {"bids": [], "asks": []},
            "NO": {"bids": [], "asks": []},
            "market_summary": {}
        }

def get_orderbook_depth(event_id: int, depth: int, db: Session) -> Dict:
    """
    Get orderbook depth (top N levels) for an event
    """
    try:
        full_orderbook = get_orderbook_snapshot(event_id, db)
        
        # Limit depth
        limited_orderbook = {
            "YES": {
                "bids": full_orderbook["YES"]["bids"][:depth],
                "asks": full_orderbook["YES"]["asks"][:depth]
            },
            "NO": {
                "bids": full_orderbook["NO"]["bids"][:depth],
                "asks": full_orderbook["NO"]["asks"][:depth]
            }
        }
        
        # Add market summary
        limited_orderbook["market_summary"] = full_orderbook.get("market_summary", {})
        
        return limited_orderbook
        
    except Exception as e:
        print(f"Error getting orderbook depth: {e}")
        return {
            "YES": {"bids": [], "asks": []},
            "NO": {"bids": [], "asks": []},
            "market_summary": {}
        }

def _get_orderbook_for_share_type(event_id: int, share_type: str) -> Dict:
    """
    Get orderbook for a specific share type (YES or NO)
    """
    bids = []  # Buy orders
    asks = []  # Sell orders
    
    try:
        # Scan through all possible price levels (1 to 10)
        for price in range(1, 11):
            # Get buy orders at this price level
            buy_queue_name = getQueueName(event_id, order_enums.OrderSide.BUY, share_type, price)
            buy_quantity = _get_total_quantity_in_queue(buy_queue_name)
            
            if buy_quantity > 0:
                bids.append({
                    "price": price,
                    "quantity": buy_quantity,
                    "side": "BUY"
                })
            
            # Get sell orders at this price level
            sell_queue_name = getQueueName(event_id, order_enums.OrderSide.SELL, share_type, price)
            sell_quantity = _get_total_quantity_in_queue(sell_queue_name)
            
            if sell_quantity > 0:
                asks.append({
                    "price": price,
                    "quantity": sell_quantity,
                    "side": "SELL"
                })
        
        # Sort bids by price (highest first)
        bids.sort(key=lambda x: x["price"], reverse=True)
        
        # Sort asks by price (lowest first)
        asks.sort(key=lambda x: x["price"])
        
        return {
            "bids": bids,
            "asks": asks
        }
        
    except Exception as e:
        print(f"Error getting orderbook for share type {share_type}: {e}")
        return {"bids": [], "asks": []}

def _get_total_quantity_in_queue(queue_name: str) -> int:
    """
    Get total quantity of all orders in a queue
    """
    try:
        # Try to acquire lock
        if not addLock(queue_name):
            return 0
        
        total_quantity = 0
        
        # Check if queue is empty
        if isQueueEmpty(queue_name):
            removeLock(queue_name)
            return 0
        
        # Get all orders in the queue and sum their remaining quantities
        # Note: This is a simplified approach. You might need to implement
        # a more efficient way to get all queue items
        
        # For now, we'll estimate based on queue length
        # You might want to implement a function to get all queue items
        queue_key = f"queue:{queue_name}"
        from redis_service import redis_client
        
        # Get all order IDs in the queue
        order_ids = redis_client.lrange(queue_key, 0, -1)
        
        for order_id in order_ids:
            order = getFromMap(int(order_id))
            if order:
                remaining_quantity = order.total_quantity - order.filled_quantity
                total_quantity += remaining_quantity
        
        removeLock(queue_name)
        return total_quantity
        
    except Exception as e:
        print(f"Error getting total quantity in queue {queue_name}: {e}")
        if queue_name in ['locks']:  # Check if we have the lock
            removeLock(queue_name)
        return 0

def _get_market_summary(orderbook: Dict) -> Dict:
    """
    Generate market summary from orderbook data
    """
    try:
        summary = {
            "YES": {
                "best_bid": None,
                "best_ask": None,
                "bid_ask_spread": None,
                "total_bid_volume": 0,
                "total_ask_volume": 0
            },
            "NO": {
                "best_bid": None,
                "best_ask": None,
                "bid_ask_spread": None,
                "total_bid_volume": 0,
                "total_ask_volume": 0
            }
        }
        
        # Calculate summary for YES shares
        if orderbook["YES"]["bids"]:
            summary["YES"]["best_bid"] = orderbook["YES"]["bids"][0]["price"]
            summary["YES"]["total_bid_volume"] = sum(bid["quantity"] for bid in orderbook["YES"]["bids"])
            
        if orderbook["YES"]["asks"]:
            summary["YES"]["best_ask"] = orderbook["YES"]["asks"][0]["price"]
            summary["YES"]["total_ask_volume"] = sum(ask["quantity"] for ask in orderbook["YES"]["asks"])
            
        if summary["YES"]["best_bid"] and summary["YES"]["best_ask"]:
            summary["YES"]["bid_ask_spread"] = summary["YES"]["best_ask"] - summary["YES"]["best_bid"]
        
        # Calculate summary for NO shares
        if orderbook["NO"]["bids"]:
            summary["NO"]["best_bid"] = orderbook["NO"]["bids"][0]["price"]
            summary["NO"]["total_bid_volume"] = sum(bid["quantity"] for bid in orderbook["NO"]["bids"])
            
        if orderbook["NO"]["asks"]:
            summary["NO"]["best_ask"] = orderbook["NO"]["asks"][0]["price"]
            summary["NO"]["total_ask_volume"] = sum(ask["quantity"] for ask in orderbook["NO"]["asks"])
            
        if summary["NO"]["best_bid"] and summary["NO"]["best_ask"]:
            summary["NO"]["bid_ask_spread"] = summary["NO"]["best_ask"] - summary["NO"]["best_bid"]
        
        return summary
        
    except Exception as e:
        print(f"Error generating market summary: {e}")
        return {
            "YES": {"best_bid": None, "best_ask": None, "bid_ask_spread": None, "total_bid_volume": 0, "total_ask_volume": 0},
            "NO": {"best_bid": None, "best_ask": None, "bid_ask_spread": None, "total_bid_volume": 0, "total_ask_volume": 0}
        }

def get_orderbook_update_data(event_id: int, db: Session) -> Dict:
    """
    Get orderbook update data (used for broadcasting)
    This is a lighter version that only includes changed data
    """
    try:
        # For now, return full snapshot
        # You can optimize this later to only return changed data
        return get_orderbook_snapshot(event_id, db)
        
    except Exception as e:
        print(f"Error getting orderbook update data: {e}")
        return {
            "YES": {"bids": [], "asks": []},
            "NO": {"bids": [], "asks": []},
            "market_summary": {}
        }

