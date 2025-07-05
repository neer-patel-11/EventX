from sqlalchemy.orm import Session

from ..enums import portfolio_enums
from ..model import portfolio_model
from ..schemas import portfolio_schema

def get_portfolio_by_user_event_share(db: Session, user_id: int, event_id: int, share_type: portfolio_enums.ShareType):
    """Get portfolio entry by user ID, event ID, and share type"""
    return db.query(portfolio_model.Portfolio).filter(
        portfolio_model.Portfolio.user_id == user_id,
        portfolio_model.Portfolio.event_id == event_id,
        portfolio_model.Portfolio.type_of_share == share_type
    ).first()

def get_portfolio_by_id(db: Session, portfolio_id: int):
    """Get portfolio entry by ID"""
    return db.query(portfolio_model.Portfolio).filter(
        portfolio_model.Portfolio.id == portfolio_id
    ).first()

def get_portfolios_by_user(db: Session, user_id: int):
    """Get all portfolio entries for a specific user"""
    return db.query(portfolio_model.Portfolio).filter(
        portfolio_model.Portfolio.user_id == user_id
    ).all()

def get_portfolios_by_event(db: Session, event_id: int):
    """Get all portfolio entries for a specific event"""
    return db.query(portfolio_model.Portfolio).filter(
        portfolio_model.Portfolio.event_id == event_id
    ).all()


def create_portfolio(db: Session, portfolio_data: portfolio_schema.PortfolioCreate, user_id: int):
    """Create a new portfolio entry"""
    db_portfolio = portfolio_model.Portfolio(
        **portfolio_data.dict(),
        user_id=user_id
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def update_portfolio(db: Session, portfolio_id: int, portfolio_update: portfolio_schema.PortfolioUpdate):
    """Update an existing portfolio entry"""
    db_portfolio = db.query(portfolio_model.Portfolio).filter(
        portfolio_model.Portfolio.id == portfolio_id
    ).first()
    
    if not db_portfolio:
        return None
    
    # Update only the fields that are provided (not None)
    update_data = portfolio_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_portfolio, field, value)
    
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def delete_portfolio(db: Session, portfolio_id: int):
    """Delete a portfolio entry"""
    db_portfolio = db.query(portfolio_model.Portfolio).filter(
        portfolio_model.Portfolio.id == portfolio_id
    ).first()
    
    if not db_portfolio:
        return None
    
    db.delete(db_portfolio)
    db.commit()
    return db_portfolio

def get_user_portfolio_summary(db: Session, user_id: int):
    """Get portfolio summary for a user (grouped by event)"""
    return db.query(portfolio_model.Portfolio).filter(
        portfolio_model.Portfolio.user_id == user_id
    ).all()

def get_portfolio_by_user_and_event(db: Session, user_id: int, event_id: int):
    """Get all portfolio entries for a user in a specific event"""
    return db.query(portfolio_model.Portfolio).filter(
        portfolio_model.Portfolio.user_id == user_id,
        portfolio_model.Portfolio.event_id == event_id
    ).all()

def update_portfolio_quantity(db: Session, portfolio_id: int, new_quantity: int):
    """Update only the quantity of a portfolio entry"""
    db_portfolio = db.query(portfolio_model.Portfolio).filter(
        portfolio_model.Portfolio.id == portfolio_id
    ).first()
    
    if not db_portfolio:
        return None
    
    db_portfolio.quantity = new_quantity
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio