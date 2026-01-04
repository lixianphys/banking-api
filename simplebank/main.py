from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from simplebank.api import customers,accounts,transactions,auth
from simplebank.utils.init_db import init_db, init_customers
from simplebank.database import SessionLocal
from simplebank.utils.redis_client import get_redis_client, close_redis
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan for the FastAPI app.
    This is used to initialize the database, customers, and Redis.
    """
    # Startup code
    db = SessionLocal()
    init_db()
    init_customers(db)
    db.close()
    
    # Initialize Redis connection
    try:
        get_redis_client()
    except Exception as e:
        # Log error but don't fail startup if Redis is unavailable
        # The app can still run without Redis (with degraded functionality)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Redis connection failed: {e}. App will continue without Redis caching.")
    
    yield
    
    # Shutdown code
    close_redis()
    

app = FastAPI(
    title="Simple Banking API",
    description="A simple banking API for managing accounts and transactions",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(customers.router, prefix="/api", tags=["customers"])
app.include_router(accounts.router, prefix="/api", tags=["accounts"])
app.include_router(transactions.router, prefix="/api", tags=["transactions"])


@app.get("/")
async def root():
    return {"message": "Welcome to the Simple Banking API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simplebank.main:app", host="0.0.0.0", port=8000, reload=True) 