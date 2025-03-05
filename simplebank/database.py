from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Using SQLite for simplicity
SQLALCHEMY_DATABASE_URL = "sqlite:///./banking.db"

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