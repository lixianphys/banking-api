from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from simplebank.database import get_db
from simplebank.models import models, schemas
from simplebank.api.security_deps import SecurityAudit

router = APIRouter()
read_account_audit = SecurityAudit(operation_name="Account API")


@router.post("/accounts", response_model=schemas.Account)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db),audit: SecurityAudit = Depends(read_account_audit)):
    # Check if customer exists
    customer = db.query(models.Customer).filter(models.Customer.id == account.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Create new account with initial deposit
    db_account = models.Account(
        customer_id=account.customer_id,
        balance=account.initial_deposit
    )
    
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/accounts", response_model=List[schemas.Account])
def read_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),audit: SecurityAudit = Depends(read_account_audit)):
    accounts = db.query(models.Account).offset(skip).limit(limit).all()
    return accounts

@router.get("/accounts/{account_id}", response_model=schemas.Account)
def read_account(account_id: int, db: Session = Depends(get_db),audit: SecurityAudit = Depends(read_account_audit)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.get("/accounts/{account_id}/balance", response_model=schemas.BalanceResponse)
def read_account_balance(account_id: int, db: Session = Depends(get_db),audit: SecurityAudit = Depends(read_account_audit)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account_id": account_id, "balance": account.balance}

@router.get("/customers/{customer_id}/accounts", response_model=List[schemas.Account])
def read_customer_accounts(customer_id: int, db: Session = Depends(get_db),audit: SecurityAudit = Depends(read_account_audit)):
    # Check if customer exists
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    accounts = db.query(models.Account).filter(models.Account.customer_id == customer_id).all()
    return accounts 