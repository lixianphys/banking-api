from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import os

from simplebank.utils.security_deps import SecurityAudit, verify_jwt_token
from simplebank.database import get_db
from simplebank.models import models, schemas
from simplebank.models.models import User
from simplebank.utils.redis_cache import (
    get_cache_key, get_cached_response, set_cached_response, invalidate_user_cache
)

CACHE_TTL_ACCOUNTS = int(os.getenv("CACHE_TTL_ACCOUNTS", "60"))


router = APIRouter()
customer_audit = SecurityAudit(operation_name="Customer API")


@router.get("/customers", response_model=List[schemas.Customer])
def read_customers(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    audit: SecurityAudit = Depends(customer_audit),
    jwt_user: Optional[User] = Depends(verify_jwt_token)
):
    """Get all customers.
    
    Protected by API key via global dependency.
    Audit logging via customer_audit dependency.
    """
    user_id = jwt_user.id if jwt_user else None
    cache_key = get_cache_key("/api/customers", {"skip": skip, "limit": limit}, user_id=user_id)
    
    # Try to get from cache
    cached_data = get_cached_response(cache_key)
    if cached_data is not None:
        return [schemas.Customer(**cust) for cust in cached_data]
    
    customers = db.query(models.Customer).offset(skip).limit(limit).all()
    customers_data = [schemas.Customer.model_validate(cust) for cust in customers]
    
    # Cache the response
    set_cached_response(cache_key, [cust.model_dump() for cust in customers_data], ttl=CACHE_TTL_ACCOUNTS)
    
    return customers_data

@router.get("/customers/{customer_id}", response_model=schemas.Customer)
def read_customer(
    customer_id: int, 
    db: Session = Depends(get_db),
    audit: SecurityAudit = Depends(customer_audit),
    jwt_user: Optional[User] = Depends(verify_jwt_token)
):
    """Get a customer by ID.
    
    Protected by API key via global dependency.
    Audit logging via customer_audit dependency.
    """
    user_id = jwt_user.id if jwt_user else None
    cache_key = get_cache_key(f"/api/customers/{customer_id}", {}, user_id=user_id)
    
    # Try to get from cache
    cached_data = get_cached_response(cache_key)
    if cached_data is not None:
        return schemas.Customer(**cached_data)
    
    customer = db.get(models.Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer_data = schemas.Customer.model_validate(customer)
    
    # Cache the response
    set_cached_response(cache_key, customer_data.model_dump(), ttl=CACHE_TTL_ACCOUNTS)
    
    return customer_data

@router.post("/customers", response_model=Dict[str, str])
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(get_db),
    audit: SecurityAudit = Depends(customer_audit),
    jwt_user: Optional[User] = Depends(verify_jwt_token)
):
    """
    Create a new customer.
    
    Protected by API key via global dependency.
    Audit logging via customer_audit dependency.
    """
    db_customer = models.Customer(name=customer.name)
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    # Invalidate cache for customers list
    invalidate_user_cache(None, endpoint="/api/customers")
    
    return {"message": "Customer created successfully"}

