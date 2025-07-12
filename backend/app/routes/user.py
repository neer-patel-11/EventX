from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from ..schemas import user_schema
from ..service import user, auth
from ..database import get_db

router = APIRouter(prefix="/users", tags=["Users"])
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

@router.get("/", response_model=list[user_schema.User])
def get_all_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user.get_all_users(db, skip, limit)

@router.get("/{user_id}", response_model=user_schema.User)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = user.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    deleted = user.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


@router.put("/{user_id}/password")
def update_password(user_id: int, new_password: str, db: Session = Depends(get_db)):
    updated = user.update_user_password(db, user_id, new_password)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Password updated successfully"}

@router.put("/{user_id}/admin")
def update_admin_status(user_id: int, is_admin: bool, db: Session = Depends(get_db)):
    updated = user.update_user_admin_status(db, user_id, is_admin)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Admin status updated"}


@router.put("/{user_id}/balance/set")
def set_balance(user_id: int, new_balance: int, db: Session = Depends(get_db)):
    updated = user.update_user_balance(db, user_id, new_balance)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated

@router.put("/{user_id}/balance/add")
def add_balance(user_id: int, amount: int, db: Session = Depends(get_db)):
    updated = user.add_to_user_balance(db, user_id, amount)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated

@router.put("/{user_id}/balance/deduct")
def deduct_balance(user_id: int, amount: int, db: Session = Depends(get_db)):
    updated = user.deduct_from_user_balance(db, user_id, amount)
    if updated is False:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@router.get("/search/", response_model=list[user_schema.User])
def search_users(term: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user.search_users(db, term, skip, limit)

@router.get("/admin", response_model=list[user_schema.User])
def get_admins(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user.get_users_by_admin_status(db, True, skip, limit)

@router.get("/balance/above", response_model=list[user_schema.User])
def get_users_with_high_balance(min_balance: int, db: Session = Depends(get_db)):
    return user.get_users_with_balance_above(db, min_balance)

@router.get("/balance/below", response_model=list[user_schema.User])
def get_users_with_low_balance(max_balance: int, db: Session = Depends(get_db)):
    return user.get_users_with_balance_below(db, max_balance)


@router.get("/count/total")
def total_users(db: Session = Depends(get_db)):
    return {"total_users": user.get_user_count(db)}

@router.get("/count/admin")
def total_admins(db: Session = Depends(get_db)):
    return {"total_admins": user.get_admin_count(db)}

