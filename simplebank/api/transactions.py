from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from sqlalchemy import or_
import os

from simplebank.database import get_db
from simplebank.models import models, schemas
from simplebank.models.models import User
from simplebank.utils.security_deps import SecurityAudit, verify_jwt_token
from simplebank.utils.cache import check_conditional_request
from simplebank.utils.pagination import cursor_paginate, PaginationField
from simplebank.utils.redis_cache import (
    get_cache_key, get_cached_response, set_cached_response, invalidate_user_cache
)
from simplebank.models.schemas import TransactionResponse, CounterpartyInfo

CACHE_TTL_TRANSACTIONS = int(os.getenv("CACHE_TTL_TRANSACTIONS", "30"))

router = APIRouter()
transaction_audit = SecurityAudit(operation_name="Transaction API")

@router.post("/transactions", response_model=Dict[str, str],dependencies=[Depends(transaction_audit)])
def create_transaction(
    transaction: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    jwt_user: Optional[User] = Depends(verify_jwt_token)
):
    """
    Create a new transaction
    Protected by API key via global dependency.
    Audit logging via transaction_audit dependency.
    """
    # Check if both accounts exist
    from_account = db.get(models.Account, transaction.from_account_id)
    to_account = db.get(models.Account, transaction.to_account_id)
    
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

    try:
        db.commit()
        db.refresh(db_transaction)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    # Invalidate cache for both accounts' transactions and balances
    invalidate_user_cache(transaction.from_account_id, endpoint="/api/accounts")
    invalidate_user_cache(transaction.to_account_id, endpoint="/api/accounts")
    
    return {"message": "Transaction created successfully"}

@router.get("/transactions", response_model=List[schemas.Transaction],dependencies=[Depends(transaction_audit)])
def read_transactions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    jwt_user: Optional[User] = Depends(verify_jwt_token)
):
    """
    Get all transactions.
    Protected by API key via global dependency.
    Audit logging via transaction_audit dependency.
    """
    user_id = jwt_user.id if jwt_user else None
    cache_key = get_cache_key("/api/transactions", {"skip": skip, "limit": limit}, user_id=user_id)
    
    # Try to get from cache
    cached_data = get_cached_response(cache_key)
    if cached_data is not None:
        return [schemas.Transaction(**tx) for tx in cached_data]
    
    transactions = db.query(models.Transaction).offset(skip).limit(limit).all()
    transactions_data = [schemas.Transaction.model_validate(tx) for tx in transactions]
    
    # Cache the response
    set_cached_response(cache_key, [tx.model_dump() for tx in transactions_data], ttl=CACHE_TTL_TRANSACTIONS)
    
    return transactions_data

@router.get(
    "/accounts/{account_id}/transactions", 
    response_model=schemas.PaginatedTransactions
)
def get_account_transactions(
    account_id: int,
    request: Request,
    response: Response,
    detail_level: str = Query("full", pattern="^(minimal|full)$"),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    expand: List[str] = Query(default=[]),
    db: Session = Depends(get_db),
    audit: SecurityAudit = Depends(transaction_audit),
    jwt_user: Optional[User] = Depends(verify_jwt_token)
):
    """
    Get transactions with configurable response format and pagination.
    This endpoint supports caching and pagination.
    Protected by API key via global dependency.
    Audit logging via transaction_audit dependency.
    """
    user_id = jwt_user.id if jwt_user else None
    cache_key = get_cache_key(
        f"/api/accounts/{account_id}/transactions",
        {"detail_level": detail_level, "cursor": cursor, "limit": limit, "expand": expand},
        user_id=user_id
    )
    
    # Try to get from cache (only if no cursor, as paginated results are dynamic)
    if cursor is None:
        cached_data = get_cached_response(cache_key)
        if cached_data is not None:
            return schemas.PaginatedTransactions(**cached_data)
    
    # First verify account exists
    account = db.get(models.Account, account_id)
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
    
    response_data = schemas.PaginatedTransactions(
        items=results,
        next_cursor=next_cursor
    )

    # Apply caching strategy
    if check_conditional_request(request, response, response_data):
        response.status_code = 304
        return response_data

    # Cache the response (only first page without cursor)
    if cursor is None:
        set_cached_response(cache_key, response_data.model_dump(), ttl=CACHE_TTL_TRANSACTIONS)

    response.headers["Cache-Control"] = "private, max-age=30"
    return response_data 