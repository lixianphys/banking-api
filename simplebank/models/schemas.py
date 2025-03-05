from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

# Customer schemas
class CustomerBase(BaseModel):
    name: str

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

# Account schemas
class AccountBase(BaseModel):
    customer_id: int

class AccountCreate(AccountBase):
    initial_deposit: float = Field(..., gt=0.0) # greater than 0.0

class Account(AccountBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    balance: float
    created_at: datetime

class AccountWithCustomer(Account):
    model_config = ConfigDict(from_attributes=True)
    owner: Customer

# Response schemas
class BalanceResponse(BaseModel):
    account_id: int
    balance: float