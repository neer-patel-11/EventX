from sqlalchemy.orm import Session

from ..schemas import event_schema
from ..model import event_model


def get_event_by_id(db: Session, id: int):
    return db.query(event_model.Event).filter(event_model.Event.id == id).first()

def get_all_events(db: Session):
    events = db.query(event_model.Event).all()
    return events

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