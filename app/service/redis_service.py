import redis
import pickle
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

import time
from datetime import datetime


# Load environment variables
load_dotenv()

# Get Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.from_url(redis_url, decode_responses=True)

# Global dictionary to store locks
locks: Dict[str, redis.lock.Lock] = {}
LOCK_TIMEOUT = 30  # Lock timeout in seconds





def _get_lock_key(queue_name: str) -> str:
    """Generate lock key for queue"""
    return f"lock:{queue_name}"

def _get_queue_key(queue_name: str) -> str:
    """Generate queue key"""
    return f"queue:{queue_name}"

def _get_map_key(id: int) -> str:
    """Generate map key for orders"""
    return f"order:{id}"

def isLocked(queue_name: str) -> bool:
    """Check if a queue is locked by this process"""
    return queue_name in locks

def addLock(queue_name: str) -> bool:
    """Add a distributed lock to a queue. Returns False if already locked by another process"""
    try:
        # Check if we already have this lock
        if queue_name in locks:
            return False
        
        lock_key = _get_lock_key(queue_name)
        lock = redis_client.lock(lock_key, timeout=LOCK_TIMEOUT)
        
        # Try to acquire the lock (non-blocking)
        if lock.acquire(blocking=False):
            locks[queue_name] = lock
            return True
        else:
            return False
    except Exception as e:
        print(f"Error adding lock to queue {queue_name}: {e}")
        return False

def removeLock(queue_name: str) -> bool:
    """Remove lock from a queue if it's locked by this process"""
    try:
        if queue_name in locks:
            lock = locks[queue_name]
            lock.release()
            del locks[queue_name]
            return True
        return False
    except Exception as e:
        print(f"Error removing lock from queue {queue_name}: {e}")
        return False


def pushToQueue(queue_name: str, id: int) -> bool:
    """Push an ID to the queue (only if queue is locked)"""
    try:
        if not isLocked(queue_name):
            print(f"Queue {queue_name} is not locked by this process")
            return False
        
        queue_key = _get_queue_key(queue_name)
        redis_client.lpush(queue_key, id)
        return True
    except Exception as e:
        print(f"Error pushing to queue {queue_name}: {e}")
        return False

def peekToQueue(queue_name: str) -> int:
    """Peek at the next item in queue without removing it"""
    try:
        if not isLocked(queue_name):
            print(f"Queue {queue_name} is not locked by this process")
            return -1
        
        queue_key = _get_queue_key(queue_name)
        result = redis_client.lindex(queue_key, -1)  # Get last item (FIFO)
        
        if result is None:
            return -1
        return int(result)
    except Exception as e:
        print(f"Error peeking queue {queue_name}: {e}")
        return -1

def popToQueue(queue_name: str) -> bool:
    """Pop an item from the queue"""
    try:
        if not isLocked(queue_name):
            print(f"Queue {queue_name} is not locked by this process")
            return False
        
        queue_key = _get_queue_key(queue_name)
        result = redis_client.rpop(queue_key)  # Remove from right (FIFO)
        
        return result is not None
    except Exception as e:
        print(f"Error popping from queue {queue_name}: {e}")
        return False

def isQueueEmpty(queue_name: str) -> bool:
    """Check if queue is empty"""
    try:
        if not isLocked(queue_name):
            print(f"Queue {queue_name} is not locked by this process")
            return True
        
        queue_key = _get_queue_key(queue_name)
        length = redis_client.llen(queue_key)
        return length == 0
    except Exception as e:
        print(f"Error checking if queue {queue_name} is empty: {e}")
        return True
    

def addToMap(order, id: int) -> bool:
    """Add an Order object to the map with given ID"""
    try:
        map_key = _get_map_key(id)
        order_data = pickle.dumps(order)
        redis_client.set(map_key, order_data)
        return True
    except Exception as e:
        print(f"Error adding order to map with ID {id}: {e}")
        return False

def getFromMap(id: int):
    """Get an Order object from the map by ID"""
    try:
        map_key = _get_map_key(id)
        order_data = redis_client.get(map_key)
        
        if order_data is None:
            return None
        
        return pickle.loads(order_data)
    except Exception as e:
        print(f"Error getting order from map with ID {id}: {e}")
        return None
    



# class MockOrder:
#     def __init__(self, symbol, quantity, price):
#         self.symbol = symbol
#         self.quantity = quantity
#         self.price = price
#         self.timestamp = datetime.now()

#     def __repr__(self):
#         return f"Order({self.symbol}, {self.quantity}, {self.price}, {self.timestamp})"


# def test_queue_flow():
#     queue_name = "test_queue"
    
#     print("Step 1: Add Lock")
#     if not addLock(queue_name):
#         print("Failed to acquire lock.")
#         return

#     print("Step 2: Push items to queue")
#     for i in range(5):
#         pushToQueue(queue_name, i)
#         print(f"Pushed ID: {i}")

    
#     print("Step 3: Peek next item")
#     peeked = peekToQueue(queue_name)
#     print(f"Peeked ID: {peeked}")

#     print("Step 4: Pop items from queue")
#     while not isQueueEmpty(queue_name):
#         popped = popToQueue(queue_name)
#         print(f"Popped: {popped}")
#         time.sleep(0.2)

#     if not addLock(queue_name):
#         print("Failed to acquire lock.")
    

#     print("Step 5: Remove Lock")
#     removeLock(queue_name)


# def test_order_map():
#     order = MockOrder("AAPL", 10, 185.50)
#     id = 12345

#     print("Step 1: Add to order map")
#     success = addToMap(order, id)
#     print(f"Added order: {success}")

#     print("Step 2: Get from order map")
#     fetched_order = getFromMap(id)
#     print(f"Fetched order: {fetched_order}")


# if __name__ == "__main__":
    print("==== Running Queue Test ====")
    test_queue_flow()

    print("\n==== Running Order Map Test ====")
    test_order_map()