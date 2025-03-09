from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import List, Optional, Any

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

# Response models for mobile API
class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# Account response models for different detail levels
class AccountMinimal(BaseResponse):
    id: int
    balance: float

class AccountFull(AccountMinimal):
    customer_id: int
    created_at: datetime

# Account response with optional expanded fields
class AccountResponse(AccountFull):
    customer: Optional[lambda: CustomerInfo] = None # lambda: CustomerInfo is a forward reference
    recent_transactions: Optional[List[lambda: TransactionSummary]] = None # lambda: TransactionSummary is a forward reference

# Customer info for expansion
class CustomerInfo(BaseResponse):
    id: int
    name: str

# Transaction summary for expansion
class TransactionSummary(BaseResponse):
    id: int
    amount: float
    timestamp: datetime
    is_credit: bool

# Transaction response models
class TransactionMinimal(BaseResponse):
    id: int
    amount: float
    timestamp: datetime
    is_credit: bool

class TransactionFull(TransactionMinimal):
    from_account_id: int
    to_account_id: int

class CounterpartyInfo(BaseResponse):
    name: Optional[str]
    account_id: int

class TransactionResponse(TransactionFull):
    counterparty: Optional[CounterpartyInfo] = None

# Paginated response
class PaginatedResponse(BaseModel):
    items: List[Any]
    next_cursor: Optional[str] = None
    
class PaginatedTransactions(PaginatedResponse):
    items: List[TransactionResponse]
    next_cursor: Optional[str] = None 