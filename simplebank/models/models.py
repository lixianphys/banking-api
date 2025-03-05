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