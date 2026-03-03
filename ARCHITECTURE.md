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

### Entry Point: app.py

The Flask application initializes and coordinates all backend services.

**Features:**
- Flask application factory pattern
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
- Fields: address, city, state, zip_code, price, bedrooms, bathrooms, sqft, year_built, property_type, lot_size, listing_url, source, latitude, longitude, images, description, created_at, updated_at, metrics, score
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

**properties.py - Property Management**
- `GET /properties` - List all properties with filtering, pagination, sorting
- `GET /properties/<id>` - Retrieve single property details
- `POST /properties` - Create new property listing
- `PUT /properties/<id>` - Update property information
- `DELETE /properties/<id>` - Remove property from system

**analysis.py - Investment Analysis**
- Composes multiple analysis services
- Converts Market objects to dictionaries for service layer compatibility
- Endpoints:
  - `GET /analysis/financial/<property_id>` - Financial metrics
  - `GET /analysis/risk/<property_id>` - Risk assessment
  - `GET /analysis/tax-benefits/<property_id>` - Tax benefit analysis
  - `GET /analysis/financing/<property_id>` - Financing options
  - `GET /analysis/score/<property_id>` - Opportunity scoring
  - `GET /analysis/comparison/<property_ids>` - Compare multiple properties

**users.py - Authentication**
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication and JWT token generation
- JWT auth with bcrypt password hashing
- Token validation on protected routes

### Services Layer (services/)

Analysis services accept (property_obj, market_dict) pairs and return computed results.

**financial_metrics.py**
- Calculates investment financial metrics
- Metrics:
  - ROI (Return on Investment)
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
- Monthly payment estimation
- Total cost of borrowing analysis

**market_aggregator.py**
- MongoDB aggregation pipeline construction
- State and city level market analysis
- Safety filters (sqft > 0) prevent MongoDB calculation errors
- Performance optimized queries
- Market trend calculations

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
- Runs in separate thread to prevent blocking API requests

### Utils Layer (utils/)

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
- **Framework**: React 17 (React Hooks for state management)
- **Routing**: React Router v5
- **HTTP Client**: Axios with interceptors
- **Styling**: Tailwind CSS
- **Charts**: Chart.js via react-chartjs-2
- **Maps**: Leaflet via react-leaflet

### Routes
- `/` - Dashboard (property overview and search)
- `/property/:id` - Property detail page
- `/login` - Authentication

### Component Architecture (14 Components)

**Page Components:**
- **Dashboard** - Main property browsing interface with search and filtering
- **PropertyDetail** - Comprehensive property analysis view
- **Login** - User authentication form

**Feature Components:**
- **MapView** - Interactive property location map
- **MarketMetricsChart** - Market trends visualization
- **PropertyCard** - Compact property display card
- **FilterPanel** - Advanced property filtering interface
- **InvestmentSummary** - High-level investment metrics
- **InvestmentMetrics** - Detailed financial metrics display
- **PropertyGallery** - Image carousel for property photos
- **TopMarketsTable** - Market comparison table
- **ComparisonTable** - Side-by-side property comparison
- **TaxBenefits** - Tax advantage breakdown
- **FinancingCalculator** - Loan program comparison tool

### API Integration (services/api.js)
- Axios HTTP client with request/response interceptors
- Automatic JWT token injection on authenticated requests
- Centralized error handling
- Base URL configuration for API endpoints
- Methods for all backend API operations

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
  - Token generation on successful login
  - Token validation on protected routes
  - JWT_SECRET_KEY configured and validated at startup
- **Password Security**
  - Bcrypt hashing via werkzeug.security
  - Salted hashes prevent rainbow table attacks
  - No plaintext passwords stored

### Rate Limiting
- 200 requests per day per IP address
- 50 requests per hour per IP address
- Protects against brute force and DoS attacks

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
- Separate containers for Flask API, React frontend, and MongoDB
- Network isolation between services
- Volume mounts for data persistence
- Environment variable configuration
- Health checks for container orchestration

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
- `/health/ready` - Database connectivity
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

## Configuration

### Environment Variables
- `FLASK_ENV` - Development or production
- `JWT_SECRET_KEY` - JWT token signing key (required)
- `MONGODB_URI` - MongoDB connection string
- `REACT_APP_API_URL` - Frontend API endpoint
- Database connection parameters
- Rate limiting thresholds
- CORS allowed origins

### Configuration Files
- Flask app configuration
- React environment files
- Docker Compose configuration
- Database connection parameters
