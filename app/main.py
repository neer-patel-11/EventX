from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .model import user_model
from .database import engine, get_db
from .routes import auth , event , portfolio , trade ,order
from .service import auth as auth_module

# Create database tables
user_model.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FastAPI JWT Auth",
    description="A FastAPI application with JWT authentication and PostgreSQL",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(event.router)
app.include_router(portfolio.router)
app.include_router(trade.router)
app.include_router(order.router)



@app.get("/")
def read_root():
    return {"message": "Welcome to Event based betting"}

@app.get("/protected")
async def protected_route(current_user: user_model.User = Depends(auth_module.get_current_active_user)):
    return {"message": f"Hello {current_user.username}, this is a protected route!"}