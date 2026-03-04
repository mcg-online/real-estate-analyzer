# Real Estate Analyzer - Code Map

**Version:** 1.4.0
**Last Updated:** 2026-03-03

This document provides a comprehensive map of the Real Estate Analyzer codebase, including all source files, their purposes, key classes/functions, and data flows. Use this as a reference for understanding system architecture and navigating the code.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Dependency Graph](#dependency-graph)
3. [Backend: Entry Point](#backend-entry-point)
4. [Backend: Data Models](#backend-data-models)
5. [Backend: API Routes](#backend-api-routes)
6. [Backend: Analysis Services](#backend-analysis-services)
7. [Backend: Data Collection](#backend-data-collection)
8. [Backend: Utilities](#backend-utilities)
9. [Frontend: Application Structure](#frontend-application-structure)
10. [Test Coverage Map](#test-coverage-map)
11. [Key Data Flows](#key-data-flows)
12. [Configuration Reference](#configuration-reference)

---

## Architecture Overview

Real Estate Analyzer is a full-stack application composed of three main layers:

- **Backend (Flask REST API)**: Property management, financial analysis, market data aggregation
- **Frontend (React SPA)**: Interactive dashboards, property details, analysis visualization
- **Database (MongoDB)**: Persistent storage for properties, markets, and user accounts

The backend exposes REST endpoints for all operations. The frontend communicates exclusively through the API client (`api.js`). All data flows between frontend and backend are mediated by the API layer.

---

## Dependency Graph

```
Frontend (React)
    ├── App.js (Router entry point)
    ├── services/api.js (API client with interceptors)
    ├── components/
    │   ├── Dashboard (main view)
    │   ├── PropertyDetail (property analysis)
    │   ├── FinancingCalculator (loan scenario analysis)
    │   ├── MapView (Leaflet map)
    │   └── ErrorBoundary (error handling)
    └── (supports React Router v5)

Backend (Flask + MongoDB)
    ├── app.py (Flask app, middleware, scheduler)
    ├── routes/ (REST endpoints)
    │   ├── properties.py (PropertyListResource, PropertyResource)
    │   ├── analysis.py (analysis endpoints)
    │   └── users.py (auth endpoints)
    ├── models/ (ORM-like classes)
    │   ├── property.py (Property model)
    │   └── market.py (Market model)
    ├── services/ (business logic)
    │   ├── analysis/ (financial, risk, scoring, tax, financing)
    │   ├── geographic/ (market aggregation)
    │   ├── data_collection/ (Zillow scraper, data service)
    │   └── scheduler.py (scheduled property & market updates)
    └── utils/ (shared utilities)
        ├── database.py (MongoDB connection)
        ├── auth.py (JWT blocklist)
        ├── validation.py (ObjectId validation)
        └── errors.py (error response formatting)

Data Flow:
  User Action → Frontend API call → Flask Route → Service Logic → MongoDB
  ↓
  Response → JSON → axios interceptor → Component state → DOM
```

---

## Backend: Entry Point

### File: `/backend/app.py`

**Purpose:** Flask application initialization, middleware setup, route registration, scheduler management, and health checks.

**Key Globals:**
- `__version__ = '1.4.0'`
- `app`: Flask application instance
- `jwt`: JWTManager for token validation
- `limiter`: Rate limiter (200 req/day, 50 req/hour)
- `cache`: SimpleCache for response caching
- `_scheduler_thread`: Background task thread for scheduled property/market updates
- `_scheduler_last_heartbeat`: Timestamp of last scheduler heartbeat
- `_scheduler_lock`: Thread lock for safe scheduler access

**Routes Registered:**
- `GET /` - Home endpoint with version info
- `GET /health` - Shallow health check (always 200)
- `GET /health/live` - Liveness probe (always 200)
- `GET /health/ready` - Deep readiness check (200 if MongoDB connected and scheduler healthy)
- `GET /api/properties` - List properties (filters, pagination, sorting)
- `POST /api/properties` - Create property (requires auth)
- `GET /api/properties/<property_id>` - Get single property
- `PUT /api/properties/<property_id>` - Update property (requires auth)
- `DELETE /api/properties/<property_id>` - Delete property (requires auth)
- `GET /api/analysis/property/<property_id>` - Analyze single property
- `POST /api/analysis/property/<property_id>` - Custom analysis with params
- `GET /api/analysis/market/<market_id>` - Analyze market area
- `POST /api/analysis/market/<market_id>` - Custom market analysis
- `GET /api/markets/top` - Top markets by ROI or cap rate
- `POST /api/auth/register` - Register new user (3/hour limit)
- `POST /api/auth/login` - Login (5/minute limit)
- `POST /api/auth/logout` - Logout (revoke token)

**Middleware:**
- **CORS**: Allows configurable origins (default: `http://localhost:3000`)
- **Request Logging**: Logs `request_id`, `method`, `path`, `status`, `latency_ms`
- **Security Headers**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy: default-src 'self'`
  - `Strict-Transport-Security: max-age=31536000` (production only)

**Configuration:**
- JWT secret from `JWT_SECRET` env var (random 32-byte hex if missing)
- JWT expiry from `JWT_EXPIRY_SECONDS` (default: 3600)
- Database URI from `DATABASE_URL` env var
- CORS origins from `CORS_ORIGINS` env var (comma-separated)

**Scheduler:**
- `run_scheduled_tasks()`: Starts background thread that runs schedule.run_pending() every 60 seconds
- `update_property_data()`: Scheduled daily at 01:00
- `update_market_data()`: Scheduled weekly
- `_ensure_scheduler_running()`: Auto-restarts scheduler if thread dies (checked during `/health/ready`)

---

## Backend: Data Models

### File: `/backend/models/property.py`

**Purpose:** MongoDB model for real estate properties with persistence and query methods.

**Class: Property**

**Attributes:**
```python
_id: ObjectId (auto-generated on save)
address: str (required)
city: str (optional, default: '')
state: str (optional, default: '')
zip_code: str (optional, default: '')
price: float (required, > 0)
bedrooms: float (required)
bathrooms: float (required)
sqft: float (required, > 0)
year_built: int (required)
property_type: str (required, one of: single_family, condo, townhouse, multi_family, land, commercial)
lot_size: float
listing_url: str (unique per property)
source: str (e.g., 'Zillow')
latitude: float (optional, for mapping)
longitude: float (optional, for mapping)
images: list[str] (optional, URLs to property images)
description: str (optional)
created_at: datetime (UTC timezone)
updated_at: datetime (UTC timezone)
metrics: dict (cached financial analysis results)
score: float (investment opportunity score 0-100)
```

**Class Methods:**
- `__init__()` - Initialize property with fields
- `save()` - Insert or update in MongoDB (handles duplicates by listing_url)
- `find_by_id(property_id)` - Get single property by ObjectId
- `find_all(filters, limit, skip, sort_by, sort_order)` - Query with filtering, pagination, sorting
- `to_dict()` - Serialize to JSON (converts datetime to ISO format, ObjectId to str in responses)
- `from_dict(data)` - Deserialize from dict (defensive, returns None on error)

**MongoDB Collection:** `properties`

**Indexes:**
- `listing_url` (unique)
- `state`
- `(state, city)` (compound)
- `zip_code`

---

### File: `/backend/models/market.py`

**Purpose:** MongoDB model for geographic markets with tax/financing data and aggregated metrics.

**Class: Market**

**Attributes:**
```python
_id: ObjectId (auto-generated on save)
name: str (market display name)
market_type: str (one of: state, county, city, zip_code)
state: str (2-char state code, e.g., 'CA')
county: str (optional)
city: str (optional)
zip_code: str (optional)
population: int (optional)
median_income: float (optional)
unemployment_rate: float (optional)
metrics: dict (aggregated property metrics)
created_at: datetime (UTC timezone)
updated_at: datetime (UTC timezone)
property_tax_rate: float (% of property value)
price_to_rent_ratio: float (market rent multiplier)
vacancy_rate: float (% vacancy)
appreciation_rate: float (annual % appreciation)
median_home_price: float
median_rent: float
price_per_sqft: float
days_on_market: float
school_rating: float (0-10)
crime_rating: float (0-10, higher = safer)
walk_score: float (0-100)
transit_score: float (0-100)
avg_hoa_fee: float (monthly average)
tax_benefits: dict (local tax incentives)
financing_programs: list (local financing programs)
```

**Class Methods:**
- `__init__()` - Initialize market with fields
- `save()` - Insert or update in MongoDB
- `find_by_id(market_id)` - Get single market by ObjectId
- `find_by_location(location_type, location_value)` - Query by state/city/zip
- `find_all(filters, limit, skip)` - Query with filtering and pagination
- `to_dict()` - Serialize to JSON
- `from_dict(data)` - Deserialize from dict (preserves ObjectId as ObjectId)

**MongoDB Collection:** `markets`

**Indexes:**
- `market_type`
- `zip_code`
- `(state, city)` (compound)

---

## Backend: API Routes

### File: `/backend/routes/properties.py`

**Purpose:** REST endpoints for CRUD operations on properties and list queries with filtering.

**Helper Functions:**
- `validate_property_data(data, require_all=True)` - Validates property fields (returns (is_valid, error_message))
  - Checks address (non-empty string)
  - Checks price, sqft (positive numbers)
  - Checks bedrooms, bathrooms (non-negative)
  - Checks year_built (1800 to current year + 1)
  - Checks property_type (enum validation)
  - Checks state (2-char uppercase, optional unless provided)

**Class: PropertyListResource**

Methods:
- `GET /api/properties` - List properties with filtering and pagination
  - Query params: `minPrice`, `maxPrice`, `minBedrooms`, `minBathrooms`, `minScore`, `propertyType`, `city`, `state`, `zipCode`
  - Pagination: `page` (default 1), `limit` (default 50, max 100)
  - Sorting: `sortBy` (default 'price'), `sortOrder` ('asc'|'desc')
  - Response: `{data, total, page, limit, pages}` (paginated envelope)
  - Status: 200 on success, 400 on validation error, 500 on error

- `POST /api/properties` - Create new property (requires JWT)
  - Required fields: address, price, bedrooms, bathrooms, sqft, year_built, property_type, lot_size, listing_url, source
  - Optional fields: city, state, zip_code, latitude, longitude, images, description
  - Returns: Created property dict with _id
  - Status: 201 on success, 400 on validation, 500 on error

**Class: PropertyResource**

Methods:
- `GET /api/properties/<property_id>` - Get single property by ID
  - Validates ObjectId format before query
  - Returns: Property dict
  - Status: 200 on success, 400 if ID invalid, 404 if not found, 500 on error

- `PUT /api/properties/<property_id>` - Update property (requires JWT)
  - Partial updates allowed (validates only provided fields)
  - Updatable fields: address, city, state, zip_code, price, bedrooms, bathrooms, sqft, year_built, property_type, lot_size, listing_url, source, latitude, longitude, images, description
  - Returns: Updated property dict
  - Status: 200 on success, 400 on validation, 404 if not found, 500 on error

- `DELETE /api/properties/<property_id>` - Delete property (requires JWT)
  - Validates ObjectId format
  - Returns: `{message: 'Property deleted successfully'}`
  - Status: 200 on success, 400 if ID invalid, 404 if not found, 500 on error

---

### File: `/backend/routes/analysis.py`

**Purpose:** REST endpoints for property and market analysis with financial and risk metrics.

**Helper Functions:**
- `_get_market_dict(property_obj)` - Looks up market data for a property
  - First tries zip_code, then city+state, then state-level market
  - Falls back to DEFAULT_MARKET_DATA if no market found
  - Returns dict (not Market object) for compatibility with analysis services

**Class: PropertyAnalysisResource**

Methods:
- `GET /api/analysis/property/<property_id>` - Get comprehensive property analysis
  - Performs: financial analysis, tax benefits analysis, financing options analysis
  - Returns:
    ```json
    {
      "property_id": str,
      "financial_analysis": {...},
      "tax_benefits": {...},
      "financing_options": {...},
      "market_data": {...}
    }
    ```
  - Status: 200 on success, 400 if ID invalid, 404 if not found, 500 on error

- `POST /api/analysis/property/<property_id>` - Run custom analysis with user parameters
  - Request body (all optional):
    ```json
    {
      "down_payment_percentage": 0.20,
      "interest_rate": 0.045,
      "term_years": 30,
      "holding_period": 5,
      "appreciation_rate": 0.03,
      "tax_bracket": 0.22,
      "credit_score": 720,
      "veteran": false,
      "first_time_va": true
    }
    ```
  - Bounds and validates all numeric parameters
  - Returns: Same structure as GET with user-supplied parameters
  - Status: 200 on success, 400 on validation, 404 if not found, 500 on error

**Class: MarketAnalysisResource**

Methods:
- `GET /api/analysis/market/<market_id>` - Get market analysis with aggregated property data
  - Calls MarketAggregator to aggregate by market_type (state/city/zip)
  - Returns:
    ```json
    {
      "market_id": str,
      "market_name": str,
      "market_type": str,
      "aggregate_data": {...},
      "market_metrics": {...}
    }
    ```
  - Status: 200 on success, 400 if ID invalid, 404 if not found, 500 on error

- `POST /api/analysis/market/<market_id>` - Custom market analysis (same as GET)

**Class: OpportunityScoringResource**

Methods:
- `GET /api/analysis/score/<property_id>` - Get investment opportunity score (0-100) with letter grade
  - Runs OpportunityScoring with 4-category composite scoring
  - Returns:
    ```json
    {
      "property_id": str,
      "overall_score": 0-100,
      "grade": "A+"|"A"|"B"|"C"|"D"|"F",
      "category_scores": {
        "financial_metrics": 0-100,
        "market_fundamentals": 0-100,
        "risk_factors": 0-100,
        "tax_and_financing": 0-100
      },
      "weights": {...},
      "score_breakdown": {...},
      "financial_analysis": {...}
    }
    ```
  - Status: 200 on success, 400 if ID invalid, 404 if not found, 500 on error

**Class: TopMarketsResource**

Methods:
- `GET /api/markets/top` - Get top performing markets ranked by ROI or cap rate
  - Query params: `limit` (1-100, default 10), `metric` ('roi'|'cap_rate')
  - Uses MarketAggregator.top_markets_by_roi() with sort_field
  - Returns: Array of market objects with aggregated metrics
  - Status: 200 on success, 400 on invalid metric, 500 on error

---

### File: `/backend/routes/users.py`

**Purpose:** REST endpoints for user authentication (register, login, logout) with JWT token management.

**Helper Functions:**
- `_validate_username(username)` - Validates username
  - Length: 3-64 characters
  - Chars: alphanumeric, underscores, dots, hyphens only
  - Returns: Error message or None

- `_validate_password(password)` - Validates password strength
  - Length: minimum 8 characters
  - Must contain: uppercase, lowercase, digit
  - Returns: Error message or None

- `_lazy_limit(limit_string)` - Rate limiter decorator that imports limiter at call time
  - Respects RATELIMIT_ENABLED config flag (set to False in tests)
  - Decorator factory for method-level rate limiting

**Class: UserRegistration**

Methods:
- `POST /api/auth/register` - Register new user (3/hour rate limit)
  - Request params: `username`, `password`
  - Validates username and password strength
  - Checks for duplicate username
  - Hashes password with werkzeug.security
  - Inserts user into `users` collection
  - Returns: `{message: 'User registered successfully'}`
  - Status: 201 on success, 400 on validation, 409 if username exists, 500 on error

**Class: UserLogin**

Methods:
- `POST /api/auth/login` - Authenticate user (5/minute rate limit)
  - Request params: `username`, `password`
  - Looks up user in `users` collection
  - Verifies password hash
  - Creates JWT access token (identity = username)
  - Returns: `{access_token: str}`
  - Status: 200 on success, 401 on invalid credentials, 500 on error

**Class: UserLogout**

Methods:
- `POST /api/auth/logout` - Revoke JWT token (requires valid JWT)
  - Extracts `jti` (JWT ID) from token claims
  - Adds to in-memory blocklist via `add_token_to_blocklist()`
  - Returns: `{message: 'User logged out successfully'}`
  - Status: 200 on success

---

## Backend: Analysis Services

### File: `/backend/services/analysis/financial_metrics.py`

**Purpose:** Calculate financial metrics for rental property analysis (income, expenses, returns).

**Class: FinancialMetrics**

**Constructor:**
```python
def __init__(self, property_data, market_data)
```
- `property_data`: Property object with price, sqft, etc.
- `market_data`: Dict with market-level metrics (must be dict, not Market object)

**Key Methods:**

- `estimate_rental_income()` - Monthly rental income estimate
  - Uses price_to_rent_ratio from market (default: 15)
  - Formula: annual_rent = price / ratio; monthly = annual / 12
  - Returns: float (rounded to 2 decimals)

- `estimate_expenses(monthly_rent)` - Monthly operating expenses
  - Components: property tax, insurance, maintenance, vacancy, management, HOA
  - Rates: tax (market %), insurance (0.35%), maintenance (1%), vacancy (market %), management (10%), HOA (market)
  - Returns: Dict with total and component breakdown

- `calculate_mortgage_payment(down_pct, interest_rate, term_years)` - Monthly mortgage payment
  - Guard: Returns 0 if monthly_rate == 0
  - Formula: Standard amortization formula
  - Returns: float (rounded)

- `calculate_cash_flow(monthly_rent, monthly_expenses, mortgage_payment)` - Net monthly income
  - Formula: rent - expenses - mortgage
  - Returns: float

- `calculate_cap_rate(annual_rental_income, annual_expenses)` - Capitalization rate
  - Guard: Returns 0 if price <= 0
  - Formula: (NOI / price) * 100
  - Returns: float (%)

- `calculate_cash_on_cash_return(annual_cf, down_pmt, closing_costs)` - Annual return on cash invested
  - Guard: Returns 0 if total investment <= 0
  - Formula: (annual_cf / (down_pmt + closing)) * 100
  - Returns: float (%)

- `calculate_roi(annual_cf, down_pmt, closing_costs, holding_period, appreciation_rate)` - Total return with appreciation
  - Guard: Returns dict with 0 values if investment <= 0
  - Includes: future_value, total_cash_flow, appreciation_profit, annualized_roi
  - Returns: Dict with roi metrics

- `calculate_break_even_point(monthly_rent, monthly_expenses, mortgage_payment)` - Years to break even
  - Factors: negative cash flow, monthly appreciation
  - Returns: 0 if positive CF; 99 if never breaks even; float years otherwise

- `analyze_property(down_pct, interest_rate, term_years, holding_period, appreciation_rate)` - Complete analysis
  - Runs all calculations with given parameters
  - Returns: Dict with all metrics (rent, expenses, mortgage, cash_flow, ROI, cap_rate, etc.)

---

### File: `/backend/services/analysis/opportunity_scoring.py`

**Purpose:** Calculate composite 0-100 investment opportunity score across 4 weighted categories.

**Class: OpportunityScoring**

**Scoring Categories:**
1. **Financial Metrics (40%)**: cap_rate (35%), cash_flow (30%), cash-on-cash (20%), ROI (15%)
2. **Market Fundamentals (30%)**: appreciation (30%), vacancy (25%), rent_growth (20%), DOM (15%), price-to-rent (10%)
3. **Risk Factors (20%)**: volatility (30%), property_age (25%), location (45%)
4. **Tax & Financing (10%)**: tax_savings (50%), financing_rate (30%), incentives (20%)

**Key Helper Functions:**
- `_clamp(value, low, high)` - Clamp value to range
- `_linear_score(value, poor, excellent)` - Map value linearly to 0-100 score
- `_assign_grade(score)` - Convert score to letter grade (A+, A, B, C, D, F)

**Public Methods:**
- `score_financial_metrics()` - Score financial characteristics (0-100)
- `score_market_fundamentals()` - Score market conditions (0-100)
- `score_risk_factors()` - Score risk profile (0-100, higher = lower risk)
- `score_tax_and_financing()` - Score tax/financing advantages (0-100)
- `calculate_score()` - Composite score calculation
  - Returns: Dict with overall_score, grade, category_scores, weights, score_breakdown, financial_analysis

**Benchmarks:**
- Cap rate: 2% (poor) to 10% (excellent)
- Monthly cash flow: -$500 (poor) to $500 (excellent)
- Appreciation rate: 0% (poor) to 6% (excellent)
- Vacancy rate: 15% (poor) to 3% (excellent)
- Days on market: 90 (poor) to 15 (excellent)
- Property age: 60 years (poor) to 5 years (excellent)

---

### File: `/backend/services/analysis/risk_assessment.py`

**Purpose:** Assess investment risk across 4 dimensions with weighted composite 0-10 score (10 = highest risk).

**Class: RiskAssessment**

**Risk Dimensions:**
1. **Market Volatility (30%)**: price history CV, appreciation deviation
2. **Vacancy Risk (25%)**: vacancy rate, days on market, unemployment
3. **Property Condition (20%)**: age, type, price-per-sqft outliers
4. **Financing Risk (25%)**: LTV, interest rate, DSCR estimate

**Risk Weights:**
```python
_WEIGHTS = {
    "market_volatility": 0.30,
    "vacancy_risk": 0.25,
    "property_condition_risk": 0.20,
    "financing_risk": 0.25,
}
```

**Key Methods:**
- `calculate_market_volatility()` - Score 0-10 based on price history and appreciation
- `calculate_vacancy_risk()` - Score 0-10 based on vacancy rate and days on market
- `calculate_property_condition_risk()` - Score 0-10 based on age, type, price-per-sqft
- `calculate_financing_risk()` - Score 0-10 based on LTV, interest rate, DSCR
- `calculate_overall_risk()` - Weighted composite score 0-10
- `assess_risk()` - Complete risk assessment report
  - Returns: Dict with individual_scores, overall_risk, risk_level, risk_factors, recommendations

**Risk Levels:**
- Low: 0-3.5
- Moderate: 3.5-5.5
- High: 5.5-7.5
- Very High: 7.5-10

---

### File: `/backend/services/analysis/tax_benefits.py`

**Purpose:** Calculate tax benefits and deductions for rental property investment.

**Class: TaxBenefits**

**Key Methods:**
- `calculate_depreciation(property_value, land_value, depreciation_period)` - Annual depreciation deduction
  - Residential property: 27.5-year depreciation (80% building value)
  - Returns: Dict with building_value, land_value, annual_depreciation, monthly_depreciation

- `calculate_mortgage_interest_deduction(loan_amount, interest_rate, term_years)` - First-year interest
  - Sums interest payments for first 12 months
  - Returns: float (annual deductible interest)

- `calculate_property_tax_deduction()` - Annual property tax
  - Formula: price * property_tax_rate
  - Returns: float

- `calculate_local_tax_incentives()` - Location-specific incentives
  - Returns: Dict with opportunity_zone, historic_credits, homestead_exemption, renovation_incentives, special_programs

- `analyze_tax_benefits(tax_bracket, down_pct, interest_rate, term_years)` - Complete tax analysis
  - Combines: depreciation + mortgage interest + property tax
  - Applies tax bracket to calculate annual tax savings
  - Returns: Dict with all tax components and estimated savings

---

### File: `/backend/services/analysis/financing_options.py`

**Purpose:** Compare conventional, FHA, and VA financing options for property purchases.

**Class: FinancingOptions**

**Financing Types:**

1. **Conventional Loan** - `get_conventional_loan(down_pct, interest_rate, term_years, credit_score)`
   - Rate adjustments: +0.5% if credit < 700, +0.25% if down < 20%
   - PMI: 0.5% annual if down < 20%
   - Returns: Dict with loan details, monthly payment, total cost

2. **FHA Loan** - `get_fha_loan(down_pct, interest_rate, term_years, credit_score)`
   - Minimum down: 3.5%
   - Upfront MIP: 1.75% of loan amount
   - Monthly MIP: 0.55% annual
   - Returns: Dict with MIP costs, total payment

3. **VA Loan** - `get_va_loan(funding_fee_pct, interest_rate, term_years, first_time)`
   - 0% down payment option (funding fee instead)
   - First-time funding fee: 2.15%
   - Repeat funding fee: 3.15%
   - Returns: Dict with funding fee, financed amount, total payment

**Public Methods:**
- `get_local_financing_programs()` - Returns market-specific financing programs
- `analyze_financing_options(credit_score, veteran, first_time_va)` - Compare all options
  - Returns: Dict with options array, local_programs, recommended option type

---

### File: `/backend/services/geographic/market_aggregator.py`

**Purpose:** Aggregate property data by geographic market (state, city, zip code) using MongoDB pipelines.

**Class: MarketAggregator**

**Constructor:**
```python
def __init__(self, db)  # db = MongoDB database instance
```

**Methods:**
- `aggregate_by_state(state_code)` - Aggregate at state level
  - Matches: properties in state with sqft > 0 and price > 0
  - Groups: count, avg_price, avg_sqft, avg_price_per_sqft, avg_beds, avg_baths, price_range
  - Returns: Dict or None

- `aggregate_by_city(state_code, city)` - Aggregate at city level
  - Same metrics as state-level
  - Matches: state + city
  - Returns: Dict or None

- `aggregate_by_zip_code(zip_code)` - Aggregate at zip code level
  - Same metrics
  - Matches: zip_code
  - Returns: Dict or None

- `top_markets_by_roi(limit, sort_field)` - Top markets ranked by metric
  - Groups: by state+city
  - Filters: only markets with >= 5 properties
  - Sorts: by avg_roi or avg_cap_rate (descending)
  - Returns: Array of top markets

- `compare_markets(markets, metrics)` - Compare multiple markets
  - Input: List of market dicts with state/city/zip_code
  - Returns: Array of aggregated data for comparison

---

## Backend: Data Collection

### File: `/backend/services/data_collection/zillow_scraper.py`

**Purpose:** Async web scraper for Zillow property listings with backoff retry and rate limiting.

**Class: ZillowScraper**

**Constructor:**
```python
def __init__(self)
```
- Sets base_url to "https://www.zillow.com"
- Maintains list of rotating user agents for stealth

**Key Methods:**
- `_get_headers()` - Returns request headers with random user agent
- `_fetch_page(session, url)` - Async page fetch with exponential backoff and sleep
  - Backoff: max 3 retries on ClientError/TimeoutError
  - Rate limit: random sleep 1.5-3.5 seconds per request
  - Timeout: 10 seconds per request
  - Returns: Page HTML or None on failure

- `_get_search_url(city, state, page)` - Constructs Zillow search URL
  - Format: `https://www.zillow.com/homes/{city}-{state}/for_sale/{page}_p/`
  - Returns: URL string

- `_extract_listings_from_page(soup)` - Parse listing links from HTML
  - Selector: `article.list-card`
  - Returns: List of dicts with 'url' key

- `_parse_property_details(property_url)` - Extract property data from listing page
  - Extracts: address, price, beds, baths, sqft, year_built, lot_size
  - Returns: Dict with Property constructor args or None on error

- `async search_properties(city, state, max_pages)` - Main search method
  - Fetches multiple pages in parallel
  - Parses listings and details
  - Returns: List of Property objects

---

### File: `/backend/services/data_collection/data_collection_service.py`

**Purpose:** Service wrapper for data collection from multiple sources (currently Zillow only).

**Class: DataCollectionService**

**Constructor:**
```python
def __init__(self)
```
- Initializes ZillowScraper instance

**Methods:**
- `async collect_properties(search_params)` - Async property collection
  - Input: Dict with 'city', 'state', 'max_pages' (optional)
  - Returns: List of Property objects
  - Raises: DataCollectionError if city/state missing

- `collect_from_all_sources(search_params)` - Sync wrapper (main entry point)
  - Calls `collect_properties()` via `asyncio.run()`
  - Handles RuntimeError if called from within event loop
  - Returns: List of Property objects
  - Raises: DataCollectionError on failure

---

### File: `/backend/services/scheduler.py`

**Purpose:** Scheduled tasks for periodic property and market data updates.

**Functions:**

- `update_property_data()` - Scheduled property data refresh (daily at 01:00)
  - Scans predefined cities: Seattle WA, Portland OR, San Francisco CA
  - Uses ZillowScraper.search_properties() with max_pages=2
  - Saves each property to database
  - Logs progress and errors
  - Returns: True on success, False on error

- `update_market_data()` - Scheduled market data update (weekly)
  - Fetches all markets from database
  - Updates each market's updated_at timestamp
  - Placeholder for external data source integration (Census API, etc.)
  - Logs progress
  - Returns: True on success, False on error

---

## Backend: Utilities

### File: `/backend/utils/database.py`

**Purpose:** MongoDB connection management with auto-reconnect, health checks, and index creation.

**Globals:**
- `_db_client`: MongoClient instance
- `_db`: Database instance
- `_mongodb_uri`: Connection string
- `_db_lock`: Thread lock for safe concurrent access

**Functions:**

- `_parse_db_name(uri)` - Extract database name from MongoDB URI
  - Defaults to 'realestate' if not specified
  - Strips query parameters
  - Returns: Database name string

- `_connect()` - Establish connection with retries and exponential backoff
  - Max retries: 3
  - Timeout: 5 seconds (server selection, connect, socket)
  - Pool config: maxPoolSize=50, minPoolSize=2, retryWrites/Reads=True
  - Creates indexes:
    - properties: listing_url (unique), state, (state, city), zip_code
    - markets: market_type, zip_code, (state, city)
    - users: username (unique)
  - Returns: Database instance or None on failure

- `init_db(app)` - Initialize database on app startup
  - Reads MONGODB_URI from app config
  - Calls _connect()
  - Called from app.py on startup
  - Returns: Database instance or None if not configured

- `get_db()` - Get database instance with auto-reconnect
  - Lazy initialization if not connected
  - Health check via ping() on every call
  - Auto-reconnects if connection lost
  - Thread-safe via _db_lock
  - Raises: ConnectionError if can't connect
  - Returns: Database instance

- `close_db()` - Close connection and cleanup
  - Called from app teardown
  - Clears globals

---

### File: `/backend/utils/auth.py`

**Purpose:** JWT token blocklist management for logout functionality.

**Globals:**
- `_jwt_blocklist`: Set of revoked token JTI (JWT ID) claims

**Functions:**

- `add_token_to_blocklist(jti)` - Add token to revocation list
  - Called on logout
  - Token identity stored as JTI (unique JWT claim)
  - Parameter: jti (string)

- `is_token_revoked(jti)` - Check if token is revoked
  - Called by Flask-JWT-Extended @jwt.token_in_blocklist_loader
  - Parameter: jti (string)
  - Returns: Boolean

**Note:** In-memory implementation suitable for single worker. For multi-worker deployments, use Redis-backed blocklist.

---

### File: `/backend/utils/errors.py`

**Purpose:** Standardized error response formatting.

**Functions:**

- `error_response(message, code, status)` - Format error response
  - Parameters:
    - message: String error message
    - code: Error code (e.g., 'VALIDATION_ERROR', 'NOT_FOUND', 'INTERNAL_ERROR')
    - status: HTTP status code
  - Returns: Tuple of (response_dict, status_code)
  - Response format:
    ```json
    {
      "error": {
        "code": "...",
        "message": "..."
      }
    }
    ```

---

### File: `/backend/utils/validation.py`

**Purpose:** Input validation helpers.

**Functions:**

- `is_valid_objectid(value)` - Validate MongoDB ObjectId format
  - Checks if value is valid 24-character hex ObjectId string
  - Used before querying by ID to return 400 early
  - Parameter: value (any type)
  - Returns: Boolean

---

## Frontend: Application Structure

### File: `/frontend/src/App.js`

**Purpose:** React Router setup, main navigation, and application layout.

**Components:**

- `Login` - Login form component
  - State: username, password, error
  - Submits credentials to /api/auth/login
  - Stores JWT token in localStorage on success
  - Redirects to dashboard

- `NotFound` - 404 page component
  - Displays 404 message with link to dashboard

- `App` - Main router component
  - Wraps app in ErrorBoundary
  - Sets up React Router with Switch/Route
  - Navigation bar with links
  - Routes:
    - `/` → Dashboard (main view)
    - `/property/:id` → PropertyDetail (single property analysis)
    - `/login` → Login page
    - `*` → NotFound (404)

**Middleware:**
- ErrorBoundary wraps entire app for error catching
- CORS credentials enabled via axios config
- Security: Strict-Transport-Security (HSTS) headers

---

### File: `/frontend/src/services/api.js`

**Purpose:** Axios HTTP client with authentication and error handling.

**Configuration:**
- Base URL: `process.env.REACT_APP_API_URL` or `http://localhost:5000/api`
- Timeout: 10 seconds
- Default headers: `Content-Type: application/json`

**Interceptors:**

- **Request Interceptor**: Adds JWT token to Authorization header
  - Reads token from localStorage
  - Format: `Authorization: Bearer <token>`

- **Response Interceptor**: Handles 401 (unauthorized)
  - Clears localStorage token
  - Redirects to login on 401
  - Preserves error details for calling code

**API Methods:**

```javascript
// Properties
getProperties(filters)        // GET /properties with optional filters
getProperty(id)               // GET /properties/:id

// Analysis
getPropertyAnalysis(id)       // GET /analysis/property/:id
customizeAnalysis(id, params) // POST /analysis/property/:id

// Markets
getTopMarkets(params)         // GET /markets/top

// Auth
login(credentials)            // POST /auth/login
register(userData)            // POST /auth/register
logout()                      // POST /auth/logout
```

---

### File: `/frontend/src/components/Dashboard.js`

**Purpose:** Main dashboard view with property listing, filtering, and market analysis.

**State:**
- `properties`: List of properties
- `topProperties`: Top 4 properties by score
- `topMarkets`: Top markets by ROI
- `isLoading`: Loading state
- `error`: Error message
- `filters`: Current filter values

**Key Features:**
- Summary statistics: property count, avg price, avg ROI, avg cap rate
- Property cards: Top investment opportunities (max 4)
- Filter panel: Price, bedrooms, bathrooms, property type, min score
- Property map: Visual representation of property locations
- Investment summary: Aggregate metrics
- Top markets table: Ranked by ROI
- Market metrics chart: Financial analysis visualization

**Filter Parameters:**
- minPrice, maxPrice
- minBedrooms, minBathrooms
- propertyType
- minScore (default: 70)

**Data Flows:**
1. Component mounts → `fetchData()` triggered
2. API call with current filters → properties list returned
3. Sort by score → set topProperties
4. Fetch top markets → display in table
5. User adjusts filters → `handleFilterChange()` updates state
6. State change triggers effect → refetch data

---

### File: `/frontend/src/components/PropertyDetail.js`

**Purpose:** Detailed property analysis view with tabs for different analysis types.

**State:**
- `property`: Property data
- `analysis`: Financial/tax/financing analysis results
- `similarProperties`: Comparison properties (max 3)
- `activeTab`: Current tab (overview|financial|financing|tax|location)
- `isLoading`: Loading state
- `isAnalyzing`: Custom analysis in progress
- `error`: Error message
- `customParams`: User-defined analysis parameters

**Custom Parameters:**
```javascript
{
  down_payment_percentage: 0.20,
  interest_rate: 0.045,
  term_years: 30,
  holding_period: 5,
  appreciation_rate: 0.03,
  tax_bracket: 0.22,
  credit_score: 720,
  veteran: false,
  first_time_va: true
}
```

**Tabs:**
1. **Overview** - Property description, key metrics (cash flow, cap rate, ROI, break-even)
2. **Financial Analysis** - Detailed financial metrics breakdown
3. **Financing Options** - Loan scenarios (conventional, FHA, VA)
4. **Tax Benefits** - Tax deductions and savings
5. **Location** - Map view and market data

**Key Metrics Displayed:**
- Investment score (colored badge)
- Monthly cash flow
- Cap rate (%)
- Cash-on-cash return (%)
- Annualized ROI (%)
- Break-even point (years)
- Property details (type, lot size, price/sqft)
- Market data (tax rate, vacancy, price-to-rent, appreciation)
- Neighborhood stats (schools, crime, walk score, transit)

---

### File: `/frontend/src/components/MapView.js`

**Purpose:** Interactive property map using Leaflet library.

**Props:**
- `properties`: Array of property objects (must have latitude/longitude)
- `center`: Optional map center [lat, lng]
- `zoom`: Map zoom level (default: 10)
- `height`: Container height (default: '400px')
- `clickable`: Enable links to property detail pages

**Features:**
- OpenStreetMap tiles
- Color-coded property markers (score-based)
  - Green (85+), Yellow (55-84), Orange (40-54), Red (<40), Gray (no score)
- Popup on marker click: address, price, beds/baths, sqft, optional detail link
- Auto-fit bounds when properties provided
- Re-center on center prop change
- Marker cleanup on data update

**Score Colors:**
```javascript
>= 85: #22c55e (green)
>= 70: #16a34a (dark green)
>= 55: #ca8a04 (yellow)
>= 40: #ea580c (orange)
<  40: #dc2626 (red)
else:  #6B7280 (gray)
```

---

### File: `/frontend/src/components/FinancingCalculator.js`

**Purpose:** Interactive financing options calculator with custom parameter adjustment.

**Props:**
- `property`: Property object
- `financingOptions`: Financing analysis result
- `onParamChange`: Callback to update custom parameters
- `params`: Current parameter values
- `onAnalyze`: Callback to rerun analysis with new params

**Features:**
- Loan option tabs: Conventional (20%, 10%), FHA, VA (if veteran)
- Option details: loan amount, down payment, interest rate, monthly payment, total interest
- PMI/MIP/funding fee calculations
- Customization sliders:
  - Down payment percentage (0-50%)
  - Interest rate (2-10%)
  - Loan term (15/20/30 years)
  - Credit score selector
  - Veteran status checkbox
- Monthly cost summary:
  - Estimated rent (green)
  - Mortgage payment (red)
  - Operating expenses (red)
  - Tax savings (green)
  - Net monthly cash flow (colored by sign)
- Local financing programs list

---

### File: `/frontend/src/components/ErrorBoundary.js`

**Purpose:** React error boundary to catch component rendering errors.

**Functionality:**
- Catches errors from child component tree
- Displays error UI with page refresh button
- Logs errors to console
- Prevents white-screen-of-death

**Error UI:**
- "Something went wrong" message
- Refresh button

---

## Test Coverage Map

**Location:** `/backend/tests/` (367 tests total)

| Test File | Test Count | Coverage |
|-----------|-----------|----------|
| `test_models.py` | 65 | Property/Market models: CRUD, validation, serialization |
| `test_routes_properties.py` | 72 | Property endpoints: list, create, get, update, delete, filters, pagination |
| `test_routes_analysis.py` | 68 | Analysis endpoints: property analysis, market analysis, scoring |
| `test_routes_users.py` | 44 | Auth endpoints: registration, login, logout, validation, rate limiting |
| `test_services.py` | 65 | Financial, tax, financing, risk, opportunity scoring services |
| `test_geographic.py` | 28 | Market aggregator: state/city/zip aggregations, top markets |
| `test_utilities.py` | 25 | Database, validation, error responses, auth blocklist |

**Test Strategy:**
- All tests fully mocked (no MongoDB required)
- Uses MagicMock for database operations
- 100% isolated from external dependencies
- Pytest framework with fixtures and parametrization
- Tests run in < 5 seconds

**Critical Coverage:**
- Validation rules (required fields, numeric ranges, enums)
- Error handling (404s, 400s, 500s)
- JWT authentication and rate limiting
- Financial calculations (guards for division-by-zero)
- Response format (paginated envelope, error structure)
- ObjectId validation and handling

---

## Key Data Flows

### Flow 1: User Searches Properties

```
Frontend (Dashboard)
  ├─ User adjusts filters (minPrice, propertyType, etc.)
  └─ state.filters updated → useEffect triggered

  │
  V

api.getProperties(filters)
  └─ GET /api/properties?minPrice=300000&propertyType=single_family

  │
  V

Backend (PropertyListResource.get)
  ├─ Parse query params into MongoDB filters
  ├─ Validate numeric params (catch ValueError)
  ├─ Pagination bounds: page >= 1, 1 <= limit <= 100
  ├─ Query: db.properties.find(filters).sort(sort_by, sort_order).skip().limit()
  └─ Count total matching documents

  │
  V

Response: {data: [...], total: N, page: 1, limit: 50, pages: M}
  └─ Convert ObjectIds to strings

  │
  V

Frontend (Dashboard)
  ├─ Set properties state
  ├─ Sort by score → topProperties
  ├─ Display summary stats
  └─ Render property cards and map
```

---

### Flow 2: User Analyzes Property

```
Frontend (Dashboard/PropertyDetail)
  ├─ User clicks property card or navigates to /property/:id
  └─ PropertyDetail component mounts

  │
  V

  api.getProperty(id)
  api.getPropertyAnalysis(id)
  (parallel requests)

  │
  V

Backend (PropertyResource.get)
  ├─ Validate ObjectId format → return 400 if invalid
  ├─ Query: db.properties.find_one({_id: ObjectId(id)})
  ├─ Deserialize to Property object
  └─ Return property.to_dict()

  │
  V

Backend (PropertyAnalysisResource.get)
  ├─ Validate ObjectId format
  ├─ Get property via Property.find_by_id()
  ├─ Look up market data (zip → city → state → default)
  │
  ├─ FinancialMetrics(property, market_data).analyze_property()
  │   ├─ estimate_rental_income()
  │   ├─ estimate_expenses()
  │   ├─ calculate_mortgage_payment()
  │   ├─ calculate_cap_rate()
  │   ├─ calculate_roi()
  │   └─ calculate_break_even_point()
  │
  ├─ TaxBenefits(property, market_data).analyze_tax_benefits()
  │   ├─ calculate_depreciation()
  │   ├─ calculate_mortgage_interest_deduction()
  │   └─ calculate_property_tax_deduction()
  │
  └─ FinancingOptions(property, market_data).analyze_financing_options()
      ├─ get_conventional_loan()
      ├─ get_fha_loan()
      ├─ get_va_loan()
      └─ Recommend best option

  │
  V

Response: {
  property_id,
  financial_analysis: {...},
  tax_benefits: {...},
  financing_options: {...},
  market_data: {...}
}

  │
  V

Frontend (PropertyDetail)
  ├─ Set property state (from getProperty)
  ├─ Set analysis state (from getPropertyAnalysis)
  ├─ Display tabs:
  │   ├─ Overview: key metrics
  │   ├─ Financial: detailed breakdown
  │   ├─ Financing: loan options comparison
  │   ├─ Tax: deductions and savings
  │   └─ Location: map and market data
  └─ Allow custom parameter adjustment → re-run analysis
```

---

### Flow 3: User Registers and Logs In

```
Frontend (Login page)
  ├─ User enters username and password
  └─ Form submit

  │
  V

api.register(credentials)
  └─ POST /api/auth/register

  │
  V

Backend (UserRegistration.post)
  ├─ Parse username, password from request
  ├─ Validate username:
  │   ├─ Length 3-64 chars
  │   └─ Alphanumeric + underscore/dot/hyphen only
  ├─ Validate password:
  │   ├─ Length >= 8
  │   ├─ Must have uppercase, lowercase, digit
  │   └─ Guard: Return 400 if invalid
  ├─ Check duplicate: db.users.find_one({username})
  │   └─ Guard: Return 409 if exists
  ├─ Hash password: werkzeug.security.generate_password_hash()
  ├─ Insert: db.users.insert_one({username, password_hash})
  └─ Return {message: 'User registered successfully'} 201

  │
  V

Frontend (Login page)
  ├─ Show success message
  └─ Redirect to login

  │
  V

api.login(credentials)
  └─ POST /api/auth/login

  │
  V

Backend (UserLogin.post)
  ├─ Parse username, password
  ├─ Lookup user: db.users.find_one({username})
  ├─ Verify password: werkzeug.security.check_password_hash()
  ├─ Guard: Return 401 if user not found or password invalid
  ├─ Create JWT: flask_jwt_extended.create_access_token(identity=username)
  │   └─ Token includes: identity, jti, exp, iat
  └─ Return {access_token} 200

  │
  V

Frontend (Login page)
  ├─ Store token: localStorage.setItem('token', access_token)
  ├─ axios interceptor adds: Authorization: Bearer <token>
  └─ Redirect to dashboard

  │
  V

Subsequent Requests
  ├─ axios request interceptor adds token to headers
  └─ Backend routes decorated @jwt_required()
    ├─ Validates token signature
    ├─ Checks token_in_blocklist (after logout)
    └─ Guard: Return 401 if invalid/revoked

  │
  V

Logout Flow
  ├─ User clicks logout
  └─ api.logout()
    └─ POST /api/auth/logout (requires valid JWT)

  │
  V

Backend (UserLogout.post)
  ├─ Get JWT claims: flask_jwt_extended.get_jwt()
  ├─ Extract jti (unique token ID)
  ├─ Add to blocklist: auth.add_token_to_blocklist(jti)
  └─ Return {message: 'User logged out successfully'} 200

  │
  V

Frontend
  ├─ axios response interceptor catches 401
  ├─ Clears localStorage token
  └─ Redirects to login
```

---

### Flow 4: Market Data Aggregation

```
Scheduled Task (Daily/Weekly)
  └─ scheduler.py: update_property_data() or update_market_data()

  │
  V

update_property_data()
  ├─ Define cities: Seattle WA, Portland OR, San Francisco CA
  ├─ Initialize ZillowScraper
  ├─ For each city:
  │   ├─ scraper.search_properties(city, state, max_pages=2)
  │   ├─ Async fetch search results + listing pages
  │   ├─ Parse property data with BeautifulSoup
  │   └─ For each property:
  │       ├─ property.save()
  │       │   ├─ Check for duplicate by listing_url
  │       │   ├─ Insert or update in db.properties
  │       │   └─ Set _id
  │       └─ Log result
  └─ Return True on success

  │
  V

update_market_data()
  ├─ Get all markets: Market.find_all()
  ├─ For each market:
  │   ├─ Update updated_at = now()
  │   ├─ Save to database
  │   └─ (Placeholder for external data fetch)
  └─ Return True on success

  │
  V

Aggregation Queries
  ├─ MarketAggregator.aggregate_by_state(state)
  │   └─ MongoDB aggregation pipeline
  │       ├─ $match: {state, sqft > 0, price > 0}
  │       ├─ $group: count, avg_price, avg_sqft, avg_beds, etc.
  │       └─ Returns: Single market aggregation
  │
  ├─ MarketAggregator.aggregate_by_city(state, city)
  │   └─ Same pipeline, grouped by state+city
  │
  └─ MarketAggregator.top_markets_by_roi(limit, sort_field)
      ├─ $match: properties with metrics.cap_rate
      ├─ $group: by state+city, calc avg_roi
      ├─ $match: only markets with >= 5 properties
      ├─ $sort: by avg_roi desc
      └─ Returns: Array of top markets
```

---

## Configuration Reference

### Environment Variables

**Backend (.env or system environment):**

| Variable | Default | Purpose |
|----------|---------|---------|
| `JWT_SECRET` | random 32-byte hex | JWT token signing key |
| `JWT_EXPIRY_SECONDS` | 3600 | Token expiry (1 hour) |
| `DATABASE_URL` | (required if DB used) | MongoDB connection string |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |

**Frontend (.env.local):**

| Variable | Default | Purpose |
|----------|---------|---------|
| `REACT_APP_API_URL` | `http://localhost:5000/api` | Backend API base URL |

**Example .env:**
```bash
JWT_SECRET=your_generated_secret_key_here
JWT_EXPIRY_SECONDS=3600
DATABASE_URL=mongodb://localhost:27017/realestate
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
FLASK_DEBUG=false
```

### Flask Configuration

**Security:**
- `MAX_CONTENT_LENGTH`: 16MB (max request body)
- `JWT_SECRET_KEY`: From JWT_SECRET env var
- Rate limiting: 200 req/day, 50 req/hour (per IP)

**Database:**
- Connection timeout: 5 seconds
- Socket timeout: 10 seconds
- Pool size: 2-50 connections
- Retry on failure: Yes
- Indexes: Created automatically on connect

**CORS:**
- Allow credentials: Yes
- Origins: Configurable
- Methods: Standard (GET, POST, PUT, DELETE, OPTIONS)

### MongoDB

**Collections:**
- `properties`: Store property listings
- `markets`: Store market data and metrics
- `users`: Store user accounts with hashed passwords

**Indexes:**
- `properties.listing_url` (unique)
- `properties.state`
- `properties.(state, city)` (compound)
- `properties.zip_code`
- `markets.market_type`
- `markets.zip_code`
- `markets.(state, city)` (compound)
- `users.username` (unique)

---

## File Organization Summary

```
real-estate-analyzer/
├── backend/
│   ├── app.py (Flask entry point, 212 lines)
│   ├── requirements.txt
│   ├── models/
│   │   ├── property.py (136 lines)
│   │   └── market.py (160 lines)
│   ├── routes/
│   │   ├── properties.py (333 lines)
│   │   ├── analysis.py (273 lines)
│   │   └── users.py (152 lines)
│   ├── services/
│   │   ├── analysis/
│   │   │   ├── financial_metrics.py (206 lines)
│   │   │   ├── opportunity_scoring.py (618 lines)
│   │   │   ├── risk_assessment.py (683 lines)
│   │   │   ├── tax_benefits.py (110 lines)
│   │   │   └── financing_options.py (190 lines)
│   │   ├── geographic/
│   │   │   └── market_aggregator.py (160 lines)
│   │   ├── data_collection/
│   │   │   ├── zillow_scraper.py (121 lines)
│   │   │   └── data_collection_service.py (120 lines)
│   │   └── scheduler.py (85 lines)
│   ├── utils/
│   │   ├── database.py (106 lines)
│   │   ├── auth.py (12 lines)
│   │   ├── validation.py (12 lines)
│   │   └── errors.py (3 lines)
│   └── tests/
│       ├── test_models.py (65 tests)
│       ├── test_routes_properties.py (72 tests)
│       ├── test_routes_analysis.py (68 tests)
│       ├── test_routes_users.py (44 tests)
│       ├── test_services.py (65 tests)
│       ├── test_geographic.py (28 tests)
│       └── test_utilities.py (25 tests)
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── index.js
│   │   ├── index.css (Tailwind)
│   │   ├── App.js (116 lines)
│   │   ├── services/
│   │   │   └── api.js (58 lines)
│   │   └── components/
│   │       ├── Dashboard.js (183 lines)
│   │       ├── PropertyDetail.js (339 lines)
│   │       ├── MapView.js (120 lines)
│   │       ├── FinancingCalculator.js (235 lines)
│   │       ├── ErrorBoundary.js (42 lines)
│   │       ├── PropertyCard.js
│   │       ├── InvestmentSummary.js
│   │       ├── MarketMetricsChart.js
│   │       ├── FilterPanel.js
│   │       ├── PropertyGallery.js
│   │       ├── InvestmentMetrics.js
│   │       ├── TaxBenefits.js
│   │       ├── TopMarketsTable.js
│   │       └── ComparisonTable.js
│   └── package.json
│
├── docker-compose.yml
├── Dockerfile
├── CHANGELOG.md
├── CLAUDE.md
├── ARCHITECTURE.md
├── API.md
├── README.md
└── CODEMAP.md (this file)
```

---

## Quick Reference: Key Decision Points

**When working with Property objects:**
- Always convert to dict before passing to analysis services: `property.to_dict()`
- Preserve ObjectId as ObjectId in from_dict() (don't stringify)
- Use .get() with defaults in from_dict() for defensive parsing

**When writing financial calculations:**
- Add division-by-zero guards: `if price <= 0: return 0.0`
- Use pytest.approx() for float assertions in tests
- Round results to 2 decimals for currency

**When handling API errors:**
- Use error_response(message, code, status) for consistency
- Validate ObjectId format early: `if not is_valid_objectid(id): return 400`
- Always handle 404 by checking find result before using

**When working with the frontend:**
- Use api.js for all backend calls (never fetch directly)
- Axios interceptor handles 401 redirects and token additions
- useState and useEffect for async data loading patterns

**For database queries:**
- Always call get_db() (never use cached connection directly)
- Indexes are created on startup automatically
- Connection auto-reconnects on failure

---

This code map is a living document. Update it when:
- Adding new routes, models, or services
- Changing data flow or architecture
- Adding significant helper functions
- Modifying configuration or deployment strategy
