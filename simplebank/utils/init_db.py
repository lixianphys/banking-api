from sqlalchemy.orm import Session
from simplebank.database import engine, SessionLocal
from simplebank.models.models import Base
from simplebank.models import models
from datetime import datetime
initial_customers = [
    {"id": 1, "name": "Arisha Barron"},
    {"id": 2, "name": "Branden Gibson"},
    {"id": 3, "name": "Rhonda Church"},
    {"id": 4, "name": "Georgina Hazel"}
]

initial_accounts = [
    {"id": 1, "customer_id": 1, "balance": 5000.00, "created_at": datetime.utcnow()},
    {"id": 2, "customer_id": 1, "balance": 10000.00, "created_at": datetime.utcnow()},
    {"id": 3, "customer_id": 2, "balance": 2500.00, "created_at": datetime.utcnow()},
    {"id": 4, "customer_id": 3, "balance": 7500.00, "created_at": datetime.utcnow()},
    {"id": 5, "customer_id": 4, "balance": 15000.00, "created_at": datetime.utcnow()}
]

initial_transactions = [
    {"from_account_id": 1, "to_account_id": 3, "amount": 250.00, "timestamp": datetime.utcnow()},
    {"from_account_id": 3, "to_account_id": 4, "amount": 100.00, "timestamp": datetime.utcnow()},
    {"from_account_id": 2, "to_account_id": 5, "amount": 500.00, "timestamp": datetime.utcnow()},
    {"from_account_id": 4, "to_account_id": 1, "amount": 75.50, "timestamp": datetime.utcnow()},
    {"from_account_id": 5, "to_account_id": 2, "amount": 300.00, "timestamp": datetime.utcnow()}
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
            # Initialize sample accounts
            print("Initializing sample accounts...")

            for account_data in initial_accounts:
                account = models.Account(**account_data)
                db.add(account)
                db.flush()
            
            # Initialize sample transactions
            print("Initializing sample transactions...")
 
            
            for transaction_data in initial_transactions:
                transaction = models.Transaction(**transaction_data)
                db.add(transaction)
                db.flush()
            db.commit()
            print("Sample data initialized successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    db = SessionLocal()
    init_db()
    init_customers(db)