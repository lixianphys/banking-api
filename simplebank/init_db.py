from sqlalchemy.orm import Session
from simplebank.database import engine, SessionLocal
from simplebank.models.models import Base
from simplebank.models import models

initial_customers = [
    {"id": 1, "name": "Arisha Barron"},
    {"id": 2, "name": "Branden Gibson"},
    {"id": 3, "name": "Rhonda Church"},
    {"id": 4, "name": "Georgina Hazel"}
]

def init_db():
    # Create tables
    Base.metadata.create_all(bind=engine)


def init_customers(db: Session):
    try:
        # Check if we already have customers
        existing_customers = db.query(models.Customer).count()
        
        if existing_customers == 0:
            print("Initializing sample customers...")
            
            for customer_data in initial_customers:
                customer = models.Customer(**customer_data)
                db.add(customer)
                db.flush()
            
            db.commit()
            print("Sample data initialized successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    db = SessionLocal()
    init_db()
    init_customers(db)