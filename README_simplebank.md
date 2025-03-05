# Banking API

A simple banking API (version 0.1.0) built with FastAPI that allows users to manage bank accounts and transactions.


## Features

- Create bank accounts for customers with initial deposits.A single customer may have multiple bank accounts.
- Transfer money between accounts (including between different customers)
- Retrieve account balances
- Retrieve transaction history for accounts


## Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

```bash
pip install -r requirements.txt
```

### Running the Application

Start the server with:
```bash
python run.py
```

The API will be available at: http://localhost:8000

You can access the interactive API documentation at: http://localhost:8000/docs

### Running Tests

To run the tests:
```bash
pytest app/tests/
```

## API Endpoints

### Customers
- `GET /api/customers` - Get all customers
- `GET /api/customers/{customer_id}` - Get a specific customer
- `POST /api/customers` - Create a new customer

### Accounts
- `POST /api/accounts` - Create a new account with initial deposit
- `GET /api/accounts` - Get all accounts
- `GET /api/accounts/{account_id}` - Get a specific account
- `GET /api/accounts/{account_id}/balance` - Get the balance of an account
- `GET /api/customers/{customer_id}/accounts` - Get all accounts for a customer

### Transactions
- `POST /api/transactions` - Create a new transaction (transfer money)
- `GET /api/transactions` - Get all transactions
- `GET /api/accounts/{account_id}/transactions` - Get transaction history for an account

## Design Decisions

- **Framework**: Used FastAPI for its performance, automatic OpenAPI documentation, data validation, and ease of use.
- **Database**: Used SQLAlchemy with SQLite for simplicity. In a production environment, a more robust database like PostgreSQL would be appropriate.
- **Error Handling**: Implemented basic error handling for common scenarios like insufficient funds and non-existent accounts.
- **Validation**: Used Pydantic models for data validation and serialization.

## Future Improvements

### Security
- Add authentication layer (JWT-based)
- Add Role- and resource-level access control
- Apply dependencies to routes

### Optimization for mobile clients
- Add pagination for list endpoints
- Add caching strategies

### Handle concurrency
