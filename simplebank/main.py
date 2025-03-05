from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/")
async def root():
    return {"message": "Welcome to the Simple Banking API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simplebank.main:app", host="0.0.0.0", port=8000, reload=True) 