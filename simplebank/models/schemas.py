from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import List

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


# Transaction schemas
class TransactionBase(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float = Field(..., gt=0.0)

    @field_validator('to_account_id')
    def accounts_must_be_different(cls, v, info):
        if 'from_account_id' in info.data and v == info.data['from_account_id']:
            raise ValueError('cannot transfer to the same account')
        return v

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime

class TransactionWithAccounts(Transaction):
    from_account: Account
    to_account: Account

    model_config = ConfigDict(from_attributes=True)

class TransferHistoryResponse(BaseModel):
    account_id: int
    transactions: List[Transaction] 