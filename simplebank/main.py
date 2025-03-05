from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from simplebank.api import customers,accounts,transactions   

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

app.include_router(customers.router, prefix="/api", tags=["customers"])
app.include_router(accounts.router, prefix="/api", tags=["accounts"])
app.include_router(transactions.router, prefix="/api", tags=["transactions"])


@app.get("/")
async def root():
    return {"message": "Welcome to the Simple Banking API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simplebank.main:app", host="0.0.0.0", port=8000, reload=True) 