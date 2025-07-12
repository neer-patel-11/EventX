# In your FastAPI endpoints:

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..schemas import portfolio_schema, user_schema
from ..model import portfolio_model
from ..service import auth, portfolio
from ..database import get_db


router = APIRouter(prefix="/portfolio")

@router.post("/", response_model=portfolio_schema.Portfolio)
def create_portfolio(portfolio_data: portfolio_schema.PortfolioCreate, 
                     current_user: user_schema.User = Depends(auth.get_current_user),
                     db: Session = Depends(get_db)):

    print("got the request")
    print(portfolio_data)
    
    # Check if user already has a portfolio entry for this event and share type
    existing_portfolio = portfolio.get_portfolio_by_user_event_share(
        db, current_user.id, portfolio_data.event_id, portfolio_data.type_of_share
    )
    
    if existing_portfolio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio entry already exists for this event and share type"
        )
    
    db_portfolio = portfolio_model.Portfolio(
        **portfolio_data.dict(),
        user_id=current_user.id
    )
    
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio


@router.get("/{portfolio_id}", response_model=portfolio_schema.Portfolio)
def get_portfolio(portfolio_id: int,
                  current_user: user_schema.User = Depends(auth.get_current_user),
                  db: Session = Depends(get_db)):
    db_portfolio = portfolio.get_portfolio_by_id(db, portfolio_id)
    
    if not db_portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Check if user owns this portfolio or is admin
    if db_portfolio.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return db_portfolio

@router.get("/", response_model=list[portfolio_schema.Portfolio])
def get_user_portfolios(current_user: user_schema.User = Depends(auth.get_current_user),
                        db: Session = Depends(get_db)):
    
    return portfolio.get_portfolios_by_user(db, current_user.id)


@router.put("/{portfolio_id}", response_model=portfolio_schema.Portfolio)
def update_portfolio(portfolio_id: int,
                     portfolio_update: portfolio_schema.PortfolioUpdate,
                     current_user: user_schema.User = Depends(auth.get_current_user),
                     db: Session = Depends(get_db)):
    
    db_portfolio = portfolio.get_portfolio_by_id(db, portfolio_id)
    
    if not db_portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Check if user owns this portfolio or is admin
    if db_portfolio.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    updated_portfolio = portfolio.update_portfolio(db, portfolio_id, portfolio_update)
    
    if not updated_portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    return updated_portfolio

@router.delete("/{portfolio_id}")
def delete_portfolio(portfolio_id: int,
                     current_user: user_schema.User = Depends(auth.get_current_user),
                     db: Session = Depends(get_db)):
    
    db_portfolio = portfolio.get_portfolio_by_id(db, portfolio_id)
    
    if not db_portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Check if user owns this portfolio or is admin
    if db_portfolio.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    deleted_portfolio = portfolio.delete_portfolio(db, portfolio_id)
    
    if not deleted_portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    return {"message": "Portfolio deleted successfully"}