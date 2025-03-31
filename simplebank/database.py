from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
# Using SQLite for simplicity
SQLALCHEMY_DATABASE_URL = "sqlite:///./banking.db"
# Using Postgres for concurrency
SQLALCHEMY_DATABASE_URL_ASYNC = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

engine = create_engine(SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally: # Ensure the connection is closed after the request is finished
        db.close() 

# Create an asynchronous database driver
engine_async=create_async_engine(SQLALCHEMY_DATABASE_URL_ASYNC, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db_async():
    async with AsyncSessionLocal() as session:
        yield session