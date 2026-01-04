# Banking API

A simple banking API (version 0.1.0) built with FastAPI that allows users to manage bank accounts and transactions.


## Features

#### Basics
- Create bank accounts for customers with initial deposits.A single customer may have multiple bank accounts.
- Transfer money between accounts (including between different customers)
- Retrieve account balances
- Retrieve transaction history for accounts

#### Advanced
- Security: JWT authentication, Redis-based rate limiting, security headers, request auditing, token blacklisting
- Mobile performance optimization: Redis caching, response customization, cursor-based pagination, resource expansion

## Getting Started

#### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Redis 7+ (for caching and rate limiting)

#### Installation

```bash
pip install -r requirements.txt
```

#### Running the Application

**Using Docker Compose (Recommended):**
```bash
docker-compose up
```

**Manual Setup:**
1. Start Redis:
```bash
redis-server
```

2. Set environment variables (optional, defaults provided):
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export JWT_SECRET_KEY=your_secret_key_here
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
export JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

3. Start the server:
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

> **Note**: All endpoints (except authentication endpoints) require JWT authentication via `Authorization: Bearer <token>` header.

#### Authentication (Public Endpoints)
- `POST /api/auth/register` - Register a new user (username, email, password)
- `POST /api/auth/login` - Login and receive JWT access and refresh tokens
- `POST /api/auth/refresh` - Refresh access token using refresh token
- `POST /api/auth/logout` - Logout and blacklist access token (requires JWT)
- `GET /api/auth/me` - Get current authenticated user information (requires JWT)

#### Customers (Requires JWT)
- `GET /api/customers` - Get all customers
- `GET /api/customers/{customer_id}` - Get a specific customer
- `POST /api/customers` - Create a new customer

#### Accounts (Requires JWT)
- `POST /api/accounts` - Create a new account with initial deposit
- `GET /api/accounts` - Get all accounts
- `GET /api/accounts/{account_id}` - Get a specific account (optimized for mobile by caching and pagination)
- `GET /api/accounts/{account_id}/balance` - Get the balance of an account
- `GET /api/customers/{customer_id}/accounts` - Get all accounts for a customer

#### Transactions (Requires JWT)
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

#### JWT Authentication
- **Required for all API endpoints** - All endpoints require JWT authentication
- User registration and login endpoints (publicly accessible)
- JWT access tokens (short-lived, default 15 minutes)
- JWT refresh tokens (long-lived, default 7 days)
- Token blacklisting on logout
- Access tokens via `Authorization: Bearer <token>` header
- All business endpoints require valid JWT token for access

#### Rate Limiting
- Redis-based rate limiting per user (identified by user ID from JWT token)
- Sliding window algorithm for accurate rate limiting
- Prevents brute force attacks and API abuse
- Configurable via environment variables (`RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW`)

#### Security Headers
- Implements standard security headers on all responses:
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Cache-Control
  - Pragma

#### Request Auditing
- Logs all API operations with client IP, method, path, status code, and duration
- Provides an audit trail for security monitoring and troubleshooting

#### Token Management
- JWT tokens are blacklisted on logout using Redis
- Refresh tokens stored in Redis for validation
- Automatic token expiration and validation

## Mobile Performance Optimization

#### Redis Caching
- Server-side caching using Redis for improved performance
- User-specific cache keys to prevent data leakage
- Automatic cache invalidation on data mutations
- Configurable TTL per endpoint type:
  - Account data: 60 seconds (default)
  - Transaction data: 30 seconds (default)
- Cache hit/miss handling for optimal performance
- Reduces database load and improves response times

#### ETag-based Caching
- Implements ETag-based HTTP caching for efficient resource retrieval
- Supports conditional requests with 304 Not Modified responses
- Reduces bandwidth usage and improves API performance
- Automatically generates ETags based on response content

#### Response Customization
- Supports different detail levels (minimal/full) for resource representations
- Allows clients to request only the data they need
- Reduces payload size and improves performance
- Example: `GET /api/accounts/{account_id}?detail_level=minimal`

#### Resource Expansion
- Supports expanding related resources in a single request
- Reduces the number of API calls needed for common operations
- Example: `GET /api/accounts/{account_id}?expand=customer,recent_transactions`

#### Cursor-based Pagination
- Implements efficient cursor-based pagination for large result sets
- Provides consistent results even when data changes between requests (better than offset)
- Includes `next_cursor` in responses for easy navigation
- Example: `GET /api/accounts/{account_id}/transactions?cursor={next_cursor}&limit=20`

## Authentication Examples

#### Register a New User
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

#### Login and Get Tokens
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "securepassword123"
  }'
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Use JWT Token for API Access
```bash
# All API endpoints require JWT authentication
curl -X GET "http://localhost:8000/api/customers" \
  -H "Authorization: Bearer <access_token>"

curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

#### Refresh Access Token
```bash
curl -X POST "http://localhost:8000/api/auth/refresh" \
  -H "Refresh-Token: <refresh_token>"
```

#### Logout
```bash
curl -X POST "http://localhost:8000/api/auth/logout" \
  -H "Authorization: Bearer <access_token>"
```

## Environment Variables

The following environment variables can be configured:

#### Redis Configuration
- `REDIS_HOST` - Redis host (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `REDIS_PASSWORD` - Redis password (optional)
- `REDIS_DB` - Redis database number (default: 0)

#### JWT Configuration
- `JWT_SECRET_KEY` - Secret key for JWT signing (required in production)
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Access token TTL in minutes (default: 15)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token TTL in days (default: 7)

#### Cache Configuration
- `CACHE_TTL_ACCOUNTS` - Cache TTL for account endpoints in seconds (default: 60)
- `CACHE_TTL_TRANSACTIONS` - Cache TTL for transaction endpoints in seconds (default: 30)

#### Rate Limiting
- `RATE_LIMIT_MAX` - Maximum requests per window (default: 60)
- `RATE_LIMIT_WINDOW` - Time window in seconds (default: 60)

