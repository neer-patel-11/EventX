# In your FastAPI endpoints:

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..schemas import event_schema, user_schema , portfolio_schema
from ..model import event_model
from ..service import auth, event , portfolio
from ..database import get_db
from ..enums import event_enums , portfolio_enums



router = APIRouter(prefix="/events")

@router.post("/", response_model=event_schema.Event)
def create_event(event_data: event_schema.EventCreate,
                 initial_quant:int, 
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):

    """Create a event """
    if current_user.is_admin == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can add Events"
        )
    # print(event_data)
    
    db_event = event_model.Event(
        **event_data.dict(),
        created_by=current_user.id
    )
    
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    event.flood_initial_shares(db,db_event,initial_quant,current_user.id)

            
    return db_event


@router.get("/{event_id}", response_model=event_schema.Event)
def get_event(event_id: int,
              current_user: user_schema.User = Depends(auth.get_current_user),
              db: Session = Depends(get_db)):
    db_event = event.get_event_by_id(db, event_id)
    
    if not db_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return db_event

@router.get("/", response_model=list[event_schema.Event])
def get_all_events(current_user: user_schema.User = Depends(auth.get_current_user),
                   db: Session = Depends(get_db)):
    
    return event.get_all_events(db)

@router.put("/{event_id}", response_model=event_schema.Event)
def update_event(event_id: int,
                 event_update: event_schema.EventUpdate,
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):
    
    if current_user.is_admin == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can edit events"
        )

    updated_event = event.update_event(db, event_id, event_update)
    
    if not updated_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    return updated_event

@router.put("/event_completed/{event_id}")
def completed_event(event_id: int,
                 event_update: event_schema.EventUpdate,
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):
    
    if current_user.is_admin == False or event_update.status != event_enums.EventStatus.COMPLETED or event_update.result == None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can edit events"
        )

    updated_event = event.update_event(db, event_id, event_update)

    if not updated_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    result = event.event_completed(db ,event_id, event_update , current_user)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not able to update"
        )
    
    return {"message":"Event completed succesfully"}



@router.delete("/{event_id}")
def delete_event(event_id: int,
                 current_user: user_schema.User = Depends(auth.get_current_user),
                 db: Session = Depends(get_db)):
    
    if current_user.is_admin == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete events"
        )

    deleted_event = event.delete_event(db, event_id)
    
    if not deleted_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    return {"message": "Event deleted successfully"}