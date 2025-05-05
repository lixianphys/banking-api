from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from simplebank.utils.security_deps import SecurityAudit
from simplebank.database import get_db
from simplebank.models import models, schemas


router = APIRouter()
customer_audit = SecurityAudit(operation_name="Customer API")


@router.get("/customers", response_model=List[schemas.Customer])
def read_customers(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    audit: SecurityAudit = Depends(customer_audit)):
    """Get all customers.
    
    Protected by API key via global dependency.
    Audit logging via customer_audit dependency.
    """
    customers = db.query(models.Customer).offset(skip).limit(limit).all()
    return customers

@router.get("/customers/{customer_id}", response_model=schemas.Customer)
def read_customer(
    customer_id: int, 
    db: Session = Depends(get_db),
    audit: SecurityAudit = Depends(customer_audit)):
    """Get a customer by ID.
    
    Protected by API key via global dependency.
    Audit logging via customer_audit dependency.
    """
    customer = db.get(models.Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.post("/customers", response_model=Dict[str, str])
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db),audit: SecurityAudit = Depends(customer_audit)):
    """
    Create a new customer.
    
    Protected by API key via global dependency.
    Audit logging via customer_audit dependency.
    """
    db_customer = models.Customer(name=customer.name)
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return {"message": "Customer created successfully"}

