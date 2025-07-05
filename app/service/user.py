from sqlalchemy.orm import Session
from sqlalchemy import or_
from passlib.context import CryptContext
from typing import Optional

from ..schemas import user_schema
from ..model import user_model

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_user_by_id(db: Session, id: int):
    """Get user by ID"""
    return db.query(user_model.User).filter(user_model.User.id == id).first()

def get_user_by_username(db: Session, username: str):
    """Get user by username"""
    return db.query(user_model.User).filter(user_model.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    """Get user by email"""
    return db.query(user_model.User).filter(user_model.User.email == email).first()

def get_user_by_username_or_email(db: Session, username_or_email: str):
    """Get user by username or email (useful for login)"""
    return db.query(user_model.User).filter(
        or_(
            user_model.User.username == username_or_email,
            user_model.User.email == username_or_email
        )
    ).first()

def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all users with pagination"""
    return db.query(user_model.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: user_schema.UserCreate):
    """Create a new user"""
    # Hash the password
    hashed_password = hash_password(user.password)
    
    # Create user instance
    db_user = user_model.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_admin=user.is_admin
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user with username and password"""
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def update_user_balance(db: Session, user_id: int, new_balance: int):
    """Update user's current balance"""
    db_user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    
    if not db_user:
        return None
    
    db_user.current_balance = new_balance
    db.commit()
    db.refresh(db_user)
    return db_user

def add_to_user_balance(db: Session, user_id: int, amount: int):
    """Add amount to user's current balance"""
    db_user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    
    if not db_user:
        return None
    
    db_user.current_balance += amount
    db.commit()
    db.refresh(db_user)
    return db_user

def deduct_from_user_balance(db: Session, user_id: int, amount: int):
    """Deduct amount from user's current balance"""
    db_user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    
    if not db_user:
        return None
    
    # Check if user has sufficient balance
    if db_user.current_balance < amount:
        return False  # Insufficient balance
    
    db_user.current_balance -= amount
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_admin_status(db: Session, user_id: int, is_admin: bool):
    """Update user's admin status"""
    db_user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    
    if not db_user:
        return None
    
    db_user.is_admin = is_admin
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_password(db: Session, user_id: int, new_password: str):
    """Update user's password"""
    db_user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    
    if not db_user:
        return None
    
    # Hash the new password
    hashed_password = hash_password(new_password)
    db_user.hashed_password = hashed_password
    
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    """Delete a user"""
    db_user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    
    if not db_user:
        return None
    
    db.delete(db_user)
    db.commit()
    return db_user

def get_users_by_admin_status(db: Session, is_admin: bool, skip: int = 0, limit: int = 100):
    """Get users filtered by admin status"""
    return db.query(user_model.User).filter(
        user_model.User.is_admin == is_admin
    ).offset(skip).limit(limit).all()

def search_users(db: Session, search_term: str, skip: int = 0, limit: int = 100):
    """Search users by username or email"""
    return db.query(user_model.User).filter(
        or_(
            user_model.User.username.ilike(f"%{search_term}%"),
            user_model.User.email.ilike(f"%{search_term}%")
        )
    ).offset(skip).limit(limit).all()

def check_user_exists(db: Session, username: str, email: str) -> dict:
    """Check if user exists by username or email"""
    username_exists = db.query(user_model.User).filter(
        user_model.User.username == username
    ).first() is not None
    
    email_exists = db.query(user_model.User).filter(
        user_model.User.email == email
    ).first() is not None
    
    return {
        "username_exists": username_exists,
        "email_exists": email_exists
    }

def get_user_count(db: Session) -> int:
    """Get total count of users"""
    return db.query(user_model.User).count()

def get_admin_count(db: Session) -> int:
    """Get total count of admin users"""
    return db.query(user_model.User).filter(user_model.User.is_admin == True).count()

def get_users_with_balance_above(db: Session, min_balance: int, skip: int = 0, limit: int = 100):
    """Get users with balance above specified amount"""
    return db.query(user_model.User).filter(
        user_model.User.current_balance > min_balance
    ).offset(skip).limit(limit).all()

def get_users_with_balance_below(db: Session, max_balance: int, skip: int = 0, limit: int = 100):
    """Get users with balance below specified amount"""
    return db.query(user_model.User).filter(
        user_model.User.current_balance < max_balance
    ).offset(skip).limit(limit).all()