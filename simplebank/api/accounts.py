from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from sqlalchemy.orm import Session
from typing import List, Union

from simplebank.database import get_db
from simplebank.models import models, schemas
from simplebank.utils.security_deps import SecurityAudit
from simplebank.utils.cache import check_conditional_request
from simplebank.models.schemas import (
    AccountMinimal, AccountFull, CustomerInfo, TransactionSummary, AccountResponse, BalanceResponse
)

router = APIRouter()
read_account_audit = SecurityAudit(operation_name="Account API")


@router.post("/accounts", response_model=schemas.Account)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db),audit: SecurityAudit = Depends(read_account_audit)):
    """
    Create a new account for a customer.
    Protected by API key via global dependency.
    Audit logging via read_account_audit dependency.
    """
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
    """
    Get all accounts.
    Protected by API key via global dependency.
    Audit logging via read_account_audit dependency.
    """
    accounts = db.query(models.Account).offset(skip).limit(limit).all()
    return accounts

@router.get(
    "/accounts/{account_id}",
    response_model=Union[AccountMinimal, AccountFull],
    response_model_exclude_none=True
)
def read_account(
    account_id: int, 
    request: Request,
    response: Response,
    detail_level: str = Query("full", pattern="^(minimal|full)$"),
    expand: List[str] = Query(default=[]),
    db: Session = Depends(get_db),
    audit: SecurityAudit = Depends(read_account_audit)
):
    """
    Get account details with configurable response format. This endpoint supports caching.
    Protected by API key via global dependency.
    Audit logging via read_account_audit dependency.
    """
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Create base response data
    response_data = {
        "id": account.id,
        "balance": account.balance,
    }

    # Add fields based on detail level
    if detail_level == "full":
        response_data.update({
            "customer_id": account.customer_id,
            "created_at": account.created_at
        })

    # Handle expansions
    if expand:
        if "customer" in expand:
            customer = db.query(models.Customer).filter(
                models.Customer.id == account.customer_id
            ).first()
            if customer:
                response_data["customer"] = CustomerInfo(
                    id=customer.id,
                    name=customer.name
                )
        
        if "recent_transactions" in expand:
            recent_tx = db.query(models.Transaction).filter(
                (models.Transaction.from_account_id == account_id) |
                (models.Transaction.to_account_id == account_id)
            ).order_by(models.Transaction.timestamp.desc()).limit(5).all()
            
            response_data["recent_transactions"] = [
                TransactionSummary(
                    id=tx.id,
                    amount=tx.amount,
                    timestamp=tx.timestamp,
                    is_credit=tx.to_account_id == account_id
                )
                for tx in recent_tx
            ]

    # Apply caching strategy
    if check_conditional_request(request, response, response_data):
        return Response(status_code=304, headers=dict(response.headers))

    # Set cache headers based on detail level
    if detail_level == "minimal":
        response.headers["Cache-Control"] = "private, max-age=60"
    else:
        response.headers["Cache-Control"] = "private, max-age=30"

    # Return appropriate response model based on detail level
    if detail_level == "minimal":
        return AccountMinimal(**response_data)
    elif detail_level == "full" and not expand:
        return AccountFull(**response_data)
    else:
        return AccountResponse(**response_data)

@router.get("/accounts/{account_id}/balance", response_model=BalanceResponse)
def read_account_balance(account_id: int, db: Session = Depends(get_db),audit: SecurityAudit = Depends(read_account_audit)):
    """
    Get the balance of an account.
    Protected by API key via global dependency.
    Audit logging via read_account_audit dependency.
    """
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return BalanceResponse(account_id=account_id, balance=account.balance)

@router.get("/customers/{customer_id}/accounts", response_model=List[schemas.Account])
def read_customer_accounts(customer_id: int, db: Session = Depends(get_db),audit: SecurityAudit = Depends(read_account_audit)):
    """
    Get all accounts for a customer.    
    Protected by API key via global dependency.
    Audit logging via read_account_audit dependency.
    """
    # Check if customer exists
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    accounts = db.query(models.Account).filter(models.Account.customer_id == customer_id).all()
    return accounts 