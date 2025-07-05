from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Dict, List
import json
import asyncio
from datetime import datetime

from ..schemas import user_schema
from ..service import auth, orderbook
from ..database import get_db

router = APIRouter(prefix="/orderbook")

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        # event_id -> list of websocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, event_id: int):
        await websocket.accept()
        if event_id not in self.active_connections:
            self.active_connections[event_id] = []
        self.active_connections[event_id].append(websocket)
        
    def disconnect(self, websocket: WebSocket, event_id: int):
        if event_id in self.active_connections:
            if websocket in self.active_connections[event_id]:
                self.active_connections[event_id].remove(websocket)
            if not self.active_connections[event_id]:
                del self.active_connections[event_id]
                
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            pass
            
    async def broadcast_to_event(self, message: str, event_id: int):
        if event_id in self.active_connections:
            connections_to_remove = []
            for connection in self.active_connections[event_id]:
                try:
                    await connection.send_text(message)
                except:
                    connections_to_remove.append(connection)
            
            # Remove dead connections
            for connection in connections_to_remove:
                self.disconnect(connection, event_id)

manager = ConnectionManager()

@router.websocket("/live/{event_id}")
async def websocket_orderbook(websocket: WebSocket, 
                            event_id: int,
                            db: Session = Depends(get_db)):
    """
    WebSocket endpoint for live orderbook data for a specific event
    """
    await manager.connect(websocket, event_id)
    
    try:
        # Send initial orderbook data
        initial_data = orderbook.get_orderbook_snapshot(event_id, db)
        await websocket.send_text(json.dumps({
            "type": "snapshot",
            "event_id": event_id,
            "data": initial_data,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Keep connection alive and handle any incoming messages
        while True:
            try:
                # Wait for any message from client (like ping/pong)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                elif message.get("type") == "refresh":
                    # Send fresh orderbook data
                    fresh_data = orderbook.get_orderbook_snapshot(event_id, db)
                    await websocket.send_text(json.dumps({
                        "type": "snapshot",
                        "event_id": event_id,
                        "data": fresh_data,
                        "timestamp": datetime.now().isoformat()
                    }))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error in websocket: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, event_id)

@router.get("/{event_id}/snapshot")
async def get_orderbook_snapshot(event_id: int,
                               current_user: user_schema.User = Depends(auth.get_current_user),
                               db: Session = Depends(get_db)):
    """
    REST endpoint to get current orderbook snapshot for an event
    """
    try:
        orderbook_data = orderbook.get_orderbook_snapshot(event_id, db)
        return {
            "event_id": event_id,
            "data": orderbook_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching orderbook: {str(e)}"
        )

@router.get("/{event_id}/depth")
async def get_orderbook_depth(event_id: int,
                            depth: int = 10,
                            current_user: user_schema.User = Depends(auth.get_current_user),
                            db: Session = Depends(get_db)):
    """
    REST endpoint to get orderbook depth (top N levels) for an event
    """
    try:
        orderbook_data = orderbook.get_orderbook_depth(event_id, depth, db)
        return {
            "event_id": event_id,
            "depth": depth,
            "data": orderbook_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching orderbook depth: {str(e)}"
        )

# Function to broadcast orderbook updates (call this after order execution)
async def broadcast_orderbook_update(event_id: int, update_data: dict):
    """
    Function to broadcast orderbook updates to all connected clients
    Call this function after order execution/modification
    """
    message = json.dumps({
        "type": "update",
        "event_id": event_id,
        "data": update_data,
        "timestamp": datetime.now().isoformat()
    })
    await manager.broadcast_to_event(message, event_id)