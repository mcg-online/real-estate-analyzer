# Real Estate Analyzer - System Architecture

## System Overview

The Real Estate Analyzer is a full-stack real estate investment analysis platform consisting of:

- **Backend**: Flask REST API with Python
- **Frontend**: React Single Page Application (SPA)
- **Database**: MongoDB for persistent data storage
- **Infrastructure**: Docker Compose for containerized deployment

This architecture enables users to browse properties, analyze investment metrics, and make data-driven real estate investment decisions.

## Data Flow

```
1. User browses properties on React frontend
   ↓
2. Frontend calls Flask API via Axios
   ↓
3. API queries MongoDB via PyMongo
   ↓
4. Analysis endpoints compute financial metrics on-the-fly
   ↓
5. Background scheduler:
   - Daily: Scrapes Zillow for property updates
   - Weekly: Updates market data
```

## Backend Architecture

### Entry Point: app.py and config.py

The Flask application uses an application factory pattern for testability and environment-based configuration.

**Flask Factory Pattern (v1.6.0):**
- `create_app(config)` factory function in `app.py` accepts a config object
- `config.py` defines four config classes:
  - `BaseConfig` — shared defaults (JWT, CORS, rate limiting settings)
  - `DevelopmentConfig` — debug mode, relaxed limits
  - `TestingConfig` — `TESTING=True`, scheduler startup skipped
  - `ProductionConfig` — strict secrets, no debug
- Backward compatible: `gunicorn app:app` and all existing imports unchanged
- Scheduler startup skipped automatically when `TESTING=True`

**Features:**
- Flask application factory pattern (`create_app`)
- JWT authentication (Flask-JWT-Extended)
- CORS support for frontend communication
- Rate limiting (200 requests/day, 50 requests/hour per IP)
- Response caching
- Request logging middleware (request ID + latency tracking)
- Health check endpoints for container orchestration
- Background scheduler thread for automated data collection
- Production deployment: Gunicorn with 4 workers

**Health Endpoints:**
- `GET /health` - Overall health status
- `GET /health/ready` - Readiness probe (checks database connectivity)
- `GET /health/live` - Liveness probe (checks basic responsiveness)

### Models Layer (models/)

**Property Model**
- MongoDB document representing a real estate listing
- Fields: address, city, state, zip_code, price, bedrooms, bathrooms, sqft, year_built, property_type, lot_size, listing_url, source, latitude, longitude, images, description, created_at, updated_at, metrics, score, user_id
- user_id: String identifying the property owner (set on POST, validated on PUT/DELETE)
- Indexes: listing_url (unique), state, (state, city), zip_code
- Defensive deserialization handles corrupted documents gracefully to prevent API crashes
- CRUD operations with validation

**Market Model**
- Location-based market data aggregation
- Fields: name, market_type, state, county, city, zip_code, population, median_income, unemployment_rate, metrics, property_tax_rate, price_to_rent_ratio, vacancy_rate, appreciation_rate, median_home_price, median_rent, price_per_sqft, days_on_market, school_rating, crime_rating, walk_score, transit_score, avg_hoa_fee, tax_benefits, financing_programs
- Indexes: market_type, zip_code, (state, city)
- Query methods for state, city, and zip code level aggregations
- Aggregation pipelines with safety filters

### Routes Layer (routes/)

**Dual-Path Registration**
- All routes available at both `/api/v1/*` (new) and legacy `/api/*` paths for backward compatibility
- Home endpoint returns `api_versions` metadata with supported versions

**properties.py - Property Management**
- `GET /properties` - List all properties with filtering, pagination, sorting (paginated envelope response)
  - Query parameter validation: all numeric filters validated (returns 400 on malformed input)
  - Pagination bounds: limit clamped [1,100], page clamped >= 1
  - Cursor-based pagination: `?cursor=<objectid>&limit=50` returns `{data, next_cursor, has_more, limit}` for efficient traversal of large datasets (v1.6.0)
- `GET /properties/<id>` - Retrieve single property details
- `POST /properties` - Create new property listing with ownership tracking
  - Captures `user_id` from JWT identity (identifies property owner)
  - Null/invalid body handling via `require_json_body` decorator (returns 400)
- `PUT /properties/<id>` - Update property information with ownership enforcement
  - Null/invalid body handling via `require_json_body` decorator (returns 400)
  - Mass assignment prevention: whitelists updatable fields (address, city, state, zip_code, price, bedrooms, bathrooms, sqft, year_built, property_type, lot_size, listing_url, description, images, latitude, longitude)
  - Ownership enforcement: returns 403 if `user_id` mismatch (backward-compatible for legacy properties without user_id)
- `DELETE /properties/<id>` - Remove property from system
  - Ownership enforcement: returns 403 if user is not the property owner (backward-compatible for legacy properties)
- ObjectId format validation via `validate_objectid` decorator on all ID-based endpoints (returns 400 on invalid IDs)
- Property ownership model enables per-user property management while maintaining backward compatibility

**analysis.py - Investment Analysis**
- Composes multiple analysis services
- Converts Market objects to dictionaries for service layer compatibility
- POST parameter bounds validation on analysis endpoints:
  - down_payment_percentage: [0.01, 0.99]
  - interest_rate: [0.001, 0.30]
  - term_years: [1, 40]
  - holding_period: [1, 30]
  - appreciation_rate: [-0.10, 0.20]
  - tax_bracket: [0.0, 0.50]
  - TopMarkets limit validation with 400 on non-numeric input
- Endpoints:
  - `GET /analysis/financial/<property_id>` - Financial metrics
  - `GET /analysis/risk/<property_id>` - Risk assessment
  - `GET /analysis/tax-benefits/<property_id>` - Tax benefit analysis
  - `GET /analysis/financing/<property_id>` - Financing options
  - `GET /analysis/score/<property_id>` - Opportunity scoring
  - `GET /analysis/comparison/<property_ids>` - Compare multiple properties

**users.py - Authentication**
- `POST /auth/register` - User registration
  - Username validation: 3-64 characters, regex pattern [a-zA-Z0-9_.-], stripped before validation
- `POST /auth/login` - User authentication and JWT token generation
- JWT auth with bcrypt password hashing
- Token validation on protected routes

### Services Layer (services/)

Analysis services accept (property_obj, market_dict) pairs and return computed results.

**financial_metrics.py**
- Calculates investment financial metrics
- Metrics:
  - ROI (Return on Investment) with zero-investment guard (returns 0 when down_payment + closing_costs <= 0)
  - Cap Rate (Capitalization Rate)
  - Cash-on-Cash Return
  - Break-Even Analysis
  - Mortgage calculations
- Division-by-zero guards prevent calculation errors
- Input validation for all financial inputs

**opportunity_scoring.py**
- Composite scoring algorithm (0-100 scale)
- Weighting:
  - Financial metrics: 40%
  - Market conditions: 30%
  - Risk factors: 20%
  - Tax benefits: 10%
- Normalized component scores for consistency
- Identifies top investment opportunities

**risk_assessment.py**
- Multi-dimensional risk analysis
- Risk dimensions:
  - Market volatility risk
  - Vacancy risk
  - Property condition risk
  - Financing risk
- Risk score aggregation (0-100)
- Mitigation recommendations
- Dynamic `_current_year()` method replaces stale `_CURRENT_YEAR` class constant

**tax_benefits.py**
- Tax advantage calculations for real estate investments
- IRS depreciation schedules (27.5-year residential)
- Deductions:
  - Mortgage interest deduction
  - Property tax deduction
  - Local incentives and credits
- Tax benefit projections over investment timeline

**financing_options.py**
- Multiple loan program analysis
- Programs:
  - Conventional loans (20% down, 10% down options)
  - FHA loans (3.5% down payment)
  - VA loans (0% down payment)
- Calculations:
  - PMI (Private Mortgage Insurance)
  - MIP (Mortgage Insurance Premium for FHA)
  - Funding fees (VA loans)
  - Zero interest rate division-by-zero guards in all three calculator methods
- Monthly payment estimation
- Total cost of borrowing analysis

**market_aggregator.py**
- MongoDB aggregation pipeline construction
- State and city level market analysis
- Safety filters (sqft > 0) prevent MongoDB calculation errors
- Performance optimized queries
- Market trend calculations
- Fixed field names: `avg_bedrooms` and `avg_bathrooms` (previously misleadingly named `median_*`)

**Data Collection Services**

**zillow_scraper.py**
- Asynchronous web scraper using aiohttp
- User-agent rotation for reliability
- Backoff retry logic for failed requests
- Rate limiting respect
- Handles pagination and dynamic content

**data_collection_service.py**
- Orchestration layer for data collection
- Coordinates multiple data sources
- Error handling and recovery
- Logging and monitoring

**scheduler.py**
- Background job scheduling
- Daily property update collection
- Weekly market data aggregation
- Runs in separate daemon thread to prevent blocking API requests
- Watchdog with heartbeat tracking: auto-restarts if thread dies
- Health status exposed via `/health/ready` endpoint

### Utils Layer (utils/)

**request_validators.py - Validation Middleware (v1.6.0)**
- Reusable decorators that eliminate inline validation boilerplate from route handlers:
  - `require_json_body` — parses and validates the JSON request body; injects `data` dict into the handler; returns 400 on missing or non-dict body
  - `validate_objectid(param_name)` — validates a URL path parameter as a 24-character hex MongoDB ObjectId; returns 400 with a human-readable label on failure
  - `require_entity(model_class, param_name, inject_as)` — combines ObjectId validation with a `find_by_id` database lookup; injects the loaded entity under `inject_as`; returns 400 on invalid ID or 404 if not found
- Compatible with Flask-RESTful `Resource` methods; stacking order follows standard Python decorator semantics (bottom-up)
- `require_entity` subsumes `validate_objectid`; do not stack both for the same parameter

**circuit_breaker.py - Circuit Breaker Pattern (v1.6.0)**
- Protects external HTTP calls (primarily ZillowScraper) from cascading failures
- Three-state machine:
  - `CLOSED` — normal operation; failures tracked against threshold
  - `OPEN` — requests immediately rejected; downstream service given recovery time
  - `HALF_OPEN` — single probe request allowed; success closes circuit, failure re-opens it
- Default parameters: `failure_threshold=5`, `recovery_timeout=300` seconds
- Thread-safe; `reset()` method available for tests or manual recovery
- Raises `CircuitOpenError` when OPEN; callers catch and skip the request gracefully

**auth.py - JWT Token Blocklist**
- Redis-backed token blocklist with lazy initialization and in-memory fallback
- `add_token_to_blocklist(jti)` - Revoke a JWT by its JTI claim
- `is_token_revoked(jti)` - Check if a token has been revoked (checks Redis first, falls back to in-memory)
- Integrated with Flask-JWT-Extended's `token_in_blocklist_loader`
- Gracefully handles Redis unavailability with in-memory fallback

**errors.py - Error Response Helpers**
- `error_response(message, code, status)` - Structured error JSON responses
- Returns `{"error": {"code": "...", "message": "..."}}` format

**validation.py - Shared Input Validation**
- `_is_valid_objectid(id_string)` - Validates MongoDB ObjectId format (extracted from routes layer)
- Ensures all ID-based endpoints return 400 on invalid ObjectId format

**database.py - Database Connection Management**
- Thread-safe MongoDB connection pooling
- Connection health checks via ping on every get_db() call
- Automatic reconnection with exponential backoff
- URI parsing via Python's urlparse module
- Connection pool configuration:
  - maxPoolSize: 50 connections
  - Connection timeout: 30 seconds
  - Retry logic with configurable backoff
- Performance indexes:
  - properties collection: listing_url (unique), state, (state, city), zip_code
  - markets collection: market_type, zip_code, (state, city)
  - users collection: username (unique)
- Graceful degradation when database is unavailable at startup (warns but doesn't crash)

## Frontend Architecture

### Technology Stack
- **Framework**: React 18 (React Hooks for state management, createRoot API for DOM rendering)
- **Routing**: React Router v6 (Routes/element API)
- **HTTP Client**: Centralized apiClient (services/api.js) with JWT interceptors — all components use this instead of raw axios
- **Styling**: Tailwind CSS
- **Charts**: Chart.js via react-chartjs-2; consolidated registration in `src/chartSetup.js` (v1.6.0) eliminates duplicate `ChartJS.register()` calls
- **Maps**: Interactive Leaflet maps (raw Leaflet.js, not react-leaflet wrapper)
- **Testing**: React Testing Library — 132 tests across 14 suites (v1.6.0); `src/setupTests.js` configures the test environment

### Routes
- `/` - Dashboard (property overview and search)
- `/property/:id` - Property detail page
- `/login` - Authentication

### Component Architecture (15 Components)

**Page Components:**
- **Dashboard** - Main property browsing interface with search and filtering
- **PropertyDetail** - Comprehensive property analysis view with URL scheme validation (http/https only)
- **Login** - User authentication form

**Feature Components:**
- **MapView** - Interactive property location map with XSS prevention (escapeHtml() sanitizes map popups); uses separate useEffect hooks for init (runs once) vs marker update (runs on data change)
- **MarketMetricsChart** - Market trends visualization
- **PropertyCard** - Compact property display card
- **FilterPanel** - Advanced property filtering interface with programmatically associated form labels (accessibility improvements)
- **InvestmentSummary** - High-level investment metrics
- **InvestmentMetrics** - Detailed financial metrics display
- **PropertyGallery** - Image carousel for property photos
- **TopMarketsTable** - Market comparison table
- **ComparisonTable** - Side-by-side property comparison
- **TaxBenefits** - Tax advantage breakdown
- **FinancingCalculator** - Loan program comparison tool with debounced interest rate calculations
- **ErrorBoundary** - Component-level error handling to prevent white-screen crashes

### API Integration (services/api.js)
- Centralized apiClient: single source of truth for all HTTP requests across the application
- Axios HTTP client with request/response interceptors
- Automatic JWT token injection on authenticated requests
- Centralized error handling with structured error responses
- Base URL configuration for API endpoints
- Methods for all backend API operations
- Consistent response envelope handling (data, total, page, limit, pages)

## Database Schema

### properties Collection
```
{
  address: String,
  city: String,
  state: String,
  zip_code: String,
  price: Number,
  bedrooms: Number,
  bathrooms: Number,
  sqft: Number,
  year_built: Number,
  property_type: String,
  lot_size: Number,
  listing_url: String (unique index),
  source: String,
  latitude: Number,
  longitude: Number,
  images: [String],
  description: String,
  created_at: Date,
  updated_at: Date,
  user_id: String,
  metrics: {
    roi: Number,
    cap_rate: Number,
    cash_on_cash: Number
  },
  score: Number
}
```

**Indexes:**
- `listing_url` (unique)
- `state`
- `(state, city)`
- `zip_code`

### markets Collection
```
{
  name: String,
  market_type: String,
  state: String,
  county: String,
  city: String,
  zip_code: String,
  population: Number,
  median_income: Number,
  unemployment_rate: Number,
  metrics: {
    appreciation_rate: Number,
    vacancy_rate: Number,
    price_to_rent_ratio: Number
  },
  property_tax_rate: Number,
  price_to_rent_ratio: Number,
  vacancy_rate: Number,
  appreciation_rate: Number,
  median_home_price: Number,
  median_rent: Number,
  price_per_sqft: Number,
  days_on_market: Number,
  school_rating: Number,
  crime_rating: Number,
  walk_score: Number,
  transit_score: Number,
  avg_hoa_fee: Number,
  tax_benefits: Object,
  financing_programs: [Object]
}
```

**Indexes:**
- `market_type`
- `zip_code`
- `(state, city)`

### users Collection
```
{
  username: String (unique index),
  password: String (bcrypt hash)
}
```

**Indexes:**
- `username` (unique)

## Security

### Authentication & Authorization
- **JWT Authentication** (Flask-JWT-Extended)
  - Token generation on successful login with configurable expiration (default 1 hour via JWT_ACCESS_TOKEN_EXPIRES)
  - Token validation on protected routes
  - JWT_SECRET_KEY configured and validated at startup
  - Redis-backed token blocklist for logout support with in-memory fallback
- **Password Security**
  - Bcrypt hashing via werkzeug.security
  - Salted hashes prevent rainbow table attacks
  - No plaintext passwords stored
- **Property Ownership Authorization**
  - PUT /properties/<id> enforces user_id ownership (403 Forbidden if user is not owner)
  - DELETE /properties/<id> enforces user_id ownership (403 Forbidden if user is not owner)
  - Backward-compatible: legacy properties without user_id remain accessible
  - Prevents unauthorized property modifications across users

### Rate Limiting & Caching
- Redis-backed rate limiting: 200 requests per day, 50 requests per hour per IP address
- In-memory fallback when Redis unavailable
- Redis-backed response caching for expensive calculations
- Protects against brute force and DoS attacks

### Input Validation & Sanitization
- **XSS Prevention**: HTML escaping via `escapeHtml()` sanitizes all user data in map popups
- **URL Scheme Validation**: Listing URLs restricted to http/https schemes only
- **Username Format Validation**: 3-64 characters, regex pattern [a-zA-Z0-9_.-], stripped before validation
- **Analysis Parameter Bounds**: All financial inputs validated against safe ranges (down_payment_percentage, interest_rate, term_years, holding_period, appreciation_rate, tax_bracket)
- **Null Body Handling**: POST/PUT endpoints return 400 on missing or invalid JSON (prevents 500 errors)
- **Mass Assignment Prevention**: PUT /properties whitelists updatable fields to prevent unintended attribute modification
- **Query Parameter Type Validation**: All numeric filter parameters validated, malformed input returns 400
- **Pagination Bounds Enforcement**: limit clamped [1,100], page clamped >= 1

### Request Security
- CORS enabled for frontend communication
- Input validation on all required fields
- Request ID tracking for audit trails
- Latency monitoring for performance issues

### Data Protection
- Defensive deserialization prevents corrupted documents from crashing the API
- Division-by-zero guards in all financial calculations
- Input validation before database operations
- Aggregation pipeline filters (sqft > 0) prevent MongoDB calculation errors

### Security Headers
- **Content-Security-Policy**: default-src 'self'; frame-ancestors 'none'
- **X-Content-Type-Options**: nosniff (prevents MIME sniffing attacks)
- **X-Frame-Options**: DENY (prevents clickjacking)
- **X-XSS-Protection**: 1; mode=block (legacy XSS protection)
- **Referrer-Policy**: strict-origin-when-cross-origin (controls referrer leakage)
- **Strict-Transport-Security**: enforced in production only (HSTS preload ready)

## Resilience & Reliability

### Database Resilience
- **Auto-Reconnection**: Automatic database reconnection with exponential backoff
- **Connection Health Checks**: Ping on every get_db() call
- **Thread-Safe Operations**: Mutex locking for concurrent requests
- **Connection Pooling**: maxPoolSize=50 for concurrent request handling
- **Graceful Degradation**: Startup warnings if database unavailable (doesn't crash)

### Calculation Safety
- Division-by-zero guards in all financial calculations
- Aggregation pipelines filter sqft > 0 to prevent MongoDB errors
- Input validation before mathematical operations
- Error messages returned to frontend without crashing backend

### Data Quality
- Defensive deserialization handles corrupted documents
- Validation on all data model operations
- Safe defaults for missing required fields
- Logging of data issues for monitoring

## Deployment

### Docker Compose Configuration
- Separate containers for Flask API, React frontend, MongoDB, and Redis 7 Alpine
- Network isolation between services
- Volume mounts for data persistence
- Environment variable configuration
- Health checks for container orchestration
- Redis 7 Alpine for token blocklist, rate limiting, and response caching

### Production Deployment
- Gunicorn application server with 4 worker processes
- Load balancing across workers
- Graceful shutdown handling
- Resource limits and monitoring

## Performance Optimization

### Database Performance
- Strategic indexing on frequently queried fields
- Aggregation pipelines for complex queries
- Connection pooling reduces connection overhead
- Query optimization through indexes

### Caching Strategy
- Response caching for expensive calculations
- Cache invalidation on data updates
- Frontend caching of API responses

### Frontend Performance
- React component optimization (memoization)
- Code splitting via React Router
- Lazy loading of images and components
- Tailwind CSS for minimal CSS payload

## Monitoring & Observability

### Health Checks
- `/health` - Overall system health
- `/health/ready` - Database connectivity + scheduler health
- `/health/live` - API responsiveness

### Request Logging
- Request ID tracking through entire request lifecycle
- Latency measurement and logging
- Error tracking and reporting
- Performance monitoring

### Data Collection Monitoring
- Scheduler execution logging
- Data scraping error tracking
- Collection completion notifications

## Testing

### Test Coverage
- **687 backend tests** across 15 test files (pytest); **132 frontend tests** across 14 suites (React Testing Library) — **819 total, all passing**
- Backend test files: test_routes.py, test_financial_metrics.py, test_financing_options.py, test_opportunity_scoring.py, test_risk_assessment.py, test_tax_benefits.py, test_validation.py, test_auth.py, test_data_collection.py, test_database.py, test_scheduler.py, test_integration.py, test_contracts.py, test_cursor_pagination.py, test_request_validators.py
- v1.6.0 additions: test_integration.py (64 cross-endpoint flows), test_contracts.py (50 API contract tests), test_cursor_pagination.py (36 cursor pagination tests), test_request_validators.py (33 decorator unit tests)
- v1.5.0 additions: test_auth.py, test_data_collection.py, test_database.py, test_scheduler.py
- All backend tests run without MongoDB (fully mocked with MagicMock)
- No external dependencies required to run backend test suite
- Load tests: Locust `tests/load/locustfile.py` with 3 user profiles (BrowsingUser, AuthenticatedUser, HeavyAnalysisUser)

### Test Patterns
- JWT authentication mocked in protected route tests
- Database operations fully mocked (no live MongoDB required)
- Financial calculations use pytest.approx() for floating-point comparison
- Redis availability tested with fallback scenarios

## Configuration

### Environment Variables
- `FLASK_ENV` - Development or production
- `JWT_SECRET_KEY` - JWT token signing key (required)
- `MONGODB_URI` - MongoDB connection string
- `REDIS_URL` - Redis connection string for token blocklist, rate limiting, and caching
- `REACT_APP_API_URL` - Frontend API endpoint
- Database connection parameters
- Rate limiting thresholds
- CORS allowed origins

### Configuration Files
- `backend/config.py` — Flask config classes (BaseConfig, DevelopmentConfig, TestingConfig, ProductionConfig)
- React environment files (`.env.local`, `.env.example`)
- Docker Compose configuration
- Database connection parameters
