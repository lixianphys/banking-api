from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from simplebank.api import customers,accounts,transactions   
from simplebank.api.security_deps import verify_api_key
from simplebank.init_db import init_db, init_customers
from simplebank.database import SessionLocal

app = FastAPI(
    title="Simple Banking API",
    description="A simple banking API for managing accounts and transactions",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers.router, prefix="/api", tags=["customers"],dependencies=[Depends(verify_api_key)])
app.include_router(accounts.router, prefix="/api", tags=["accounts"],dependencies=[Depends(verify_api_key)])
app.include_router(transactions.router, prefix="/api", tags=["transactions"],dependencies=[Depends(verify_api_key)])


@app.get("/")
async def root():
    return {"message": "Welcome to the Simple Banking API"}

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    init_db()
    init_customers(db)
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simplebank.main:app", host="0.0.0.0", port=8000, reload=True) 