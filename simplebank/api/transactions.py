from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_

from simplebank.database import get_db
from simplebank.models import models, schemas
from simplebank.utils.security_deps import SecurityAudit

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

@router.get(
    "/accounts/{account_id}/transactions", 
    response_model=schemas.PaginatedTransactions
)
async def get_account_transactions(
    account_id: int,
    request: Request,
    response: Response,
    detail_level: str = Query("full", pattern="^(minimal|full)$"),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    expand: List[str] = Query(default=[]),
    db: Session = Depends(get_db),
    audit: SecurityAudit = Depends(transaction_audit)
):
    """
    Get transactions with configurable response format and pagination.
    """
    # First verify account exists
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    base_query = db.query(models.Transaction).filter(
        or_(
            models.Transaction.from_account_id == account_id,
            models.Transaction.to_account_id == account_id
        )
    ).order_by(models.Transaction.timestamp.desc())

    # Add debug logging
    print(f"Account ID: {account_id}")
    print(f"Cursor: {cursor}")
    print(f"Base query count: {base_query.count()}")

    # Apply cursor-based pagination
    from simplebank.utils.pagination import cursor_paginate, PaginationField
    transactions, next_cursor = cursor_paginate(
        query=base_query,
        cursor=cursor,
        limit=limit,
        pagination_fields=[
            PaginationField("timestamp", is_timestamp=True),
            PaginationField("id")
        ]
    )

    print(f"Returned transactions count: {len(transactions)}")

    # Format transactions based on detail level
    from simplebank.models.schemas import TransactionResponse, CounterpartyInfo
    results = []
    for tx in transactions:
        tx_data = {
            "id": tx.id,
            "amount": tx.amount,
            "timestamp": tx.timestamp,
            "is_credit": tx.to_account_id == account_id
        }

        if detail_level == "full":
            tx_data.update({
                "from_account_id": tx.from_account_id,
                "to_account_id": tx.to_account_id
            })

        # Handle expansions
        if expand and "counterparty" in expand:
            counterparty_id = tx.from_account_id if tx.to_account_id == account_id else tx.to_account_id
            counterparty_account = db.query(models.Account).filter(
                models.Account.id == counterparty_id
            ).first()
            
            if counterparty_account:
                counterparty = db.query(models.Customer).filter(
                    models.Customer.id == counterparty_account.customer_id
                ).first()
                tx_data["counterparty"] = CounterpartyInfo(
                    name=counterparty.name if counterparty else None,
                    account_id=counterparty_id
                )

        results.append(TransactionResponse(**tx_data))

    from simplebank.utils.cache import check_conditional_request
    response_data = schemas.PaginatedTransactions(
        items=results,
        next_cursor=next_cursor
    )

    # Apply caching strategy
    if check_conditional_request(request, response, response_data):
        response.status_code = 304
        return response_data

    response.headers["Cache-Control"] = "private, max-age=30"
    return response_data 