# Banking API

## System Architecture Overview

```mermaid
graph TB
    %% External Layer
    Client[Client Applications<br/>Web/Mobile/API]
    
    %% Load Balancer/Reverse Proxy
    LB[Load Balancer<br/>Nginx/HAProxy]
    
    %% Application Layer
    subgraph "FastAPI Application"
        Main[main.py<br/>FastAPI App]
        
        %% Security Layer
        subgraph "Security & Middleware"
            Auth[API Key Authentication<br/>verify_api_key]
            RateLimit[Rate Limiting<br/>check_rate_limit]
            CORS[CORS Middleware]
            Audit[Request Auditing<br/>SecurityAudit]
            Headers[Security Headers]
        end
        
        %% API Layer
        subgraph "API Endpoints"
            CustomerAPI[customers.py<br/>Customer Management]
            AccountAPI[accounts.py<br/>Account Operations]
            TransactionAPI[transactions.py<br/>Money Transfers]
        end
        
        %% Business Logic Layer
        subgraph "Business Logic"
            Schemas[Pydantic Schemas<br/>Data Validation]
            Utils[Utilities<br/>Cache, Pagination, Init]
        end
    end
    
    %% Data Layer
    subgraph "Data Layer"
        DB[(SQLite Database<br/>banking.db)]
    end
    
    %% Database Models
    subgraph "Database Models"
        CustomerModel[Customer<br/>id, name]
        AccountModel[Account<br/>id, customer_id, balance, created_at]
        TransactionModel[Transaction<br/>id, from_account_id, to_account_id, amount, timestamp]
    end
    
    %% Deployment
    subgraph "Deployment"
        Docker[Docker Container]
        Compose[Docker Compose]
    end
    
    %% Connections
    Client --> LB
    LB --> Main
    Main --> Auth
    Auth --> RateLimit
    RateLimit --> CORS
    CORS --> Audit
    Audit --> Headers
    Headers --> CustomerAPI
    Headers --> AccountAPI
    Headers --> TransactionAPI
    
    CustomerAPI --> Schemas
    AccountAPI --> Schemas
    TransactionAPI --> Schemas
    
    Schemas --> Utils
    Utils --> DB
    
    DB --> CustomerModel
    DB --> AccountModel
    DB --> TransactionModel
    
    CustomerModel -.->|1:N| AccountModel
    AccountModel -.->|1:N| TransactionModel
    
    Main --> Docker
    Docker --> Compose
```

## API Flow Architecture

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Security
    participant API
    participant Database
    
    Client->>FastAPI: HTTP Request
    FastAPI->>Security: Verify API Key
    Security->>Security: Check Rate Limit
    Security->>Security: Add Security Headers
    Security->>API: Route to Endpoint
    API->>API: Validate Request (Pydantic)
    API->>Database: Query Data
    Database-->>API: Return Data
    API->>API: Generate ETag
    alt ETag Match (If-None-Match header)
        API-->>Client: 304 Not Modified
    else ETag Mismatch
        API-->>Client: Fresh Response with ETag
    end
```


## Key Architecture Components

### 1. **FastAPI Application** (`main.py`)
- Main application entry point
- CORS middleware configuration
- Router registration with security dependencies
- Application lifespan management

### 2. **Security Layer** (`utils/security_deps.py`)
- API key authentication via `X-API-Key` header
- Rate limiting per IP address
- Security headers injection
- Request auditing and logging

### 3. **API Endpoints**
- **Customers** (`api/customers.py`): Customer CRUD operations
- **Accounts** (`api/accounts.py`): Account management with mobile optimizations
- **Transactions** (`api/transactions.py`): Money transfer operations

### 4. **Data Models** (`models/`)
- **SQLAlchemy Models** (`models.py`): Database schema definitions
- **Pydantic Schemas** (`schemas.py`): API request/response validation

### 5. **Database Layer** (`database.py`)
- SQLite for development (with PostgreSQL async support)
- Session management with dependency injection
- Connection pooling and lifecycle management

### 6. **Utilities** (`utils/`)
- **Cache** (`cache.py`): ETag-based HTTP caching for mobile optimization
- **Pagination** (`pagination.py`): Cursor-based pagination
- **Database Init** (`init_db.py`): Database initialization and seeding

### 7. **Deployment**
- Docker containerization
- Docker Compose for orchestration
- Environment-based configuration

## Key Features

### Security
- API key authentication
- Rate limiting
- Security headers
- Request auditing
- CORS protection

### Performance
- ETag-based HTTP caching (client-side)
- Response customization
- Resource expansion
- Cursor-based pagination

### Scalability
- Async database support
- Connection pooling
- Stateless design
- Containerized deployment
