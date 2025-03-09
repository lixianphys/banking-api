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
pytest simplebank/tests/
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
## Security Features

The API implements several security measures to protect against common threats:

### API Key Authentication
- All endpoints require a valid API key via the `X-API-Key` header
- Protects against unauthorized access to sensitive banking operations

### Rate Limiting
- Limits the number of requests from a single IP address
- Prevents brute force attacks and API abuse
- Configurable via environment variables

### Security Headers
- Implements standard security headers on all responses:
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Cache-Control
  - Pragma

### Request Auditing
- Logs all API operations with client IP, method, path, status code, and duration
- Provides an audit trail for security monitoring and troubleshooting

### Caching
- Implements ETag-based caching for efficient resource retrieval
- Supports conditional requests with 304 Not Modified responses
- Reduces bandwidth usage and improves API performance
- Automatically generates ETags based on response content

### Response Customization
- Supports different detail levels (minimal/full) for resource representations
- Allows clients to request only the data they need
- Reduces payload size and improves performance
- Example: `GET /api/accounts/{account_id}?detail_level=minimal`

### Resource Expansion
- Supports expanding related resources in a single request
- Reduces the number of API calls needed for common operations
- Example: `GET /api/accounts/{account_id}?expand=customer,recent_transactions`

### Cursor-based Pagination
- Implements efficient cursor-based pagination for large result sets
- Provides consistent results even when data changes between requests
- Includes `next_cursor` in responses for easy navigation
- Example: `GET /api/accounts/{account_id}/transactions?cursor=eyJ0aW1lc3RhbXAiOiIyMDIzLTA1LTAxVDEyOjM0OjU2IiwiaWQiOjEyM30=&limit=20`


## Future Improvements

