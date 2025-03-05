from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    accounts = relationship("Account", back_populates="owner")

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("Customer", back_populates="accounts")
    outgoing_transactions = relationship(
        "Transaction", 
        foreign_keys="Transaction.from_account_id",
        back_populates="from_account"
    )
    incoming_transactions = relationship(
        "Transaction", 
        foreign_keys="Transaction.to_account_id",
        back_populates="to_account"
    )

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"))
    to_account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    from_account = relationship(
        "Account", 
        foreign_keys=[from_account_id],
        back_populates="outgoing_transactions"
    )
    to_account = relationship(
        "Account", 
        foreign_keys=[to_account_id],
        back_populates="incoming_transactions"
    ) 