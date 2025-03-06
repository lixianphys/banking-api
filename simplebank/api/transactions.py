from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import or_

from simplebank.database import get_db
from simplebank.models import models, schemas
from simplebank.api.security_deps import SecurityAudit

router = APIRouter()
transaction_audit = SecurityAudit(operation_name="Transaction API")

@router.post("/transactions", response_model=schemas.Transaction,dependencies=[Depends(transaction_audit)])
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    # Check if both accounts exist``
    from_account = db.query(models.Account).filter(models.Account.id == transaction.from_account_id).first()
    to_account = db.query(models.Account).filter(models.Account.id == transaction.to_account_id).first()
    
    if not from_account:
        raise HTTPException(status_code=404, detail="Source account not found")
    if not to_account:
        raise HTTPException(status_code=404, detail="Destination account not found")
    
    # Check if the source account has sufficient funds
    if from_account.balance < transaction.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds in source account")
    
    # Update account balances
    from_account.balance -= transaction.amount
    to_account.balance += transaction.amount
    
    # Create transaction record
    db_transaction = models.Transaction(
        from_account_id=transaction.from_account_id,
        to_account_id=transaction.to_account_id,
        amount=transaction.amount
    )
    
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    return db_transaction

@router.get("/transactions", response_model=List[schemas.Transaction],dependencies=[Depends(transaction_audit)])
def read_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).offset(skip).limit(limit).all()
    return transactions

@router.get("/accounts/{account_id}/transactions", response_model=schemas.TransferHistoryResponse,dependencies=[Depends(transaction_audit)])
def read_account_transactions(account_id: int, db: Session = Depends(get_db)):
    # Check if account exists
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Get transactions where the account is either source or destination
    transactions = db.query(models.Transaction).filter(
        or_(
            models.Transaction.from_account_id == account_id,
            models.Transaction.to_account_id == account_id
        )
    ).all()
    
    return {"account_id": account_id, "transactions": transactions} 