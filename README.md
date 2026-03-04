# Real Estate Investment Analysis Tool

A comprehensive full-stack web application for analyzing residential real estate investment opportunities. This tool helps investors identify profitable properties through detailed financial analysis, tax benefit calculations, financing comparisons, market aggregation, and geographic insights.

**Quick Links**: [Features](#features) | [Architecture](#architecture) | [API Reference](#api-reference) | [Getting Started](#getting-started) | [Testing](#testing) | [Security](#security)

## Features

### Property Analysis & Scoring
- **Financial Metrics**: Calculate ROI, cap rate, cash-on-cash return, break-even analysis, and monthly cash flow
- **Investment Scoring**: Automated 0-100 composite score based on:
  - Financial metrics (40% weight)
  - Market conditions (30% weight)
  - Risk factors (20% weight)
  - Tax benefits (10% weight)
- **Risk Assessment**: Comprehensive evaluation across market volatility, vacancy rates, property condition, and financing risk
- **Tax Benefits**: Estimate depreciation deductions, mortgage interest deductions, and property tax benefits
- **Financing Options**: Compare conventional, FHA, and VA loan options with detailed amortization and payment calculations

### Market Analysis
- **Market Aggregation**: Analyze investment potential across states, cities, and zip codes using MongoDB aggregation pipelines
- **Top Markets**: Identify top-performing markets ranked by ROI, cap rate, or other metrics
- **Market-Specific Insights**: View tax incentives and financing programs available by region

### Data Collection
- **Zillow Web Scraper**: Async scraper with user-agent rotation, automatic retry with exponential backoff
- **Scheduled Updates**: Automated daily property updates and weekly market analysis refresh
- **Background Jobs**: APScheduler integration for reliable background task execution

### User Interface
- **Interactive Maps**: Leaflet-powered geographic visualization with location-based property browsing
- **Advanced Filtering**: Filter by price, bedrooms, bathrooms, property type, location, and opportunity score
- **Dynamic Charts**: Chart.js powered investment metrics comparison and visualization
- **Tabbed Analysis Views**: Organized property details with separate tabs for analysis, market, tax, and financing info
- **Property Gallery**: Visual property browsing with key metrics at a glance

### Authentication & Security
- **JWT Authentication**: Secure token-based authentication with Flask-JWT-Extended
- **User Registration/Login**: Bcrypt password hashing for secure credential storage
- **Rate Limiting**: Flask-Limiter prevents abuse with configurable rate limits
- **Request Logging**: Comprehensive logging of API requests for debugging and monitoring

## Tech Stack

### Backend
- **Framework**: Python 3.9+, Flask 2.x, Flask-RESTful
- **Authentication**: Flask-JWT-Extended with bcrypt password hashing
- **Database**: MongoDB (PyMongo 4.x) with connection pooling and auto-reconnect
- **Caching**: Flask-Caching for response optimization
- **Rate Limiting**: Flask-Limiter to prevent API abuse
- **CORS**: Flask-CORS for cross-origin requests
- **Async Data Collection**: aiohttp with backoff retry strategy
- **Background Jobs**: APScheduler for scheduled data updates
- **Server**: Gunicorn WSGI server (4 workers, production-ready)
- **Testing**: pytest with 405 tests, 100% pass rate
- **Input Validation**: Parameter bounds, username validation, null body handling
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options

### Frontend
- **Framework**: React 17 with React Router v5
- **Styling**: Tailwind CSS with responsive design
- **Visualization**: Chart.js (via react-chartjs-2) and Leaflet (via react-leaflet)
- **HTTP Client**: apiClient service with JWT auth and error handling
- **Build**: Create React App with webpack bundling
- **Error Handling**: ErrorBoundary component for render error recovery
- **Components**: 404 route for unknown paths, Leaflet map memory leak fixes

### Deployment
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose for local development and production
- **Database**: MongoDB container with health checks
- **Health Checks**: Shallow and deep health endpoints for load balancer integration

## Architecture

```
real-estate-analyzer/
├── backend/
│   ├── app.py                              # Flask entry point with configuration
│   │                                       # - JWT setup, rate limiting, caching
│   │                                       # - Health endpoints, request logging
│   │                                       # - APScheduler initialization
│   │
│   ├── models/
│   │   ├── property.py                     # Property model (MongoDB CRUD)
│   │   │                                   # - Defensive deserialization
│   │   │                                   # - Index definitions
│   │   └── market.py                       # Market model (location-based queries)
│   │
│   ├── routes/
│   │   ├── properties.py                   # PropertyListResource (GET/POST)
│   │   │                                   # PropertyResource (GET/PUT/DELETE)
│   │   │                                   # Pagination, filtering, sorting
│   │   │
│   │   ├── analysis.py                     # PropertyAnalysisResource
│   │   │                                   # MarketAnalysisResource
│   │   │                                   # TopMarketsResource
│   │   │
│   │   └── users.py                        # UserRegistration, UserLogin
│   │                                       # Username 3-64 chars validation
│   │                                       # UserLogout with bcrypt hashing
│   │
│   ├── services/
│   │   ├── analysis/
│   │   │   ├── financial_metrics.py        # ROI, cap rate, cash-on-cash
│   │   │   │                               # Break-even, mortgage payment calc
│   │   │   │
│   │   │   ├── opportunity_scoring.py      # Composite 0-100 investment score
│   │   │   │                               # Weighted metric calculation
│   │   │   │
│   │   │   ├── risk_assessment.py          # Market volatility, vacancy
│   │   │   │                               # Property condition, financing risk
│   │   │   │
│   │   │   ├── tax_benefits.py             # Depreciation, mortgage interest
│   │   │   │                               # Property tax deductions
│   │   │   │
│   │   │   └── financing_options.py        # Conventional, FHA, VA loan
│   │   │                                   # comparison and calculations
│   │   │
│   │   ├── geographic/
│   │   │   └── market_aggregator.py        # MongoDB aggregation pipelines
│   │   │                                   # State/city/zip queries
│   │   │
│   │   ├── data_collection/
│   │   │   ├── zillow_scraper.py           # Async scraper, user-agent rotation
│   │   │   │                               # Automatic retry with backoff
│   │   │   │
│   │   │   └── data_collection_service.py  # Orchestration and coordination
│   │   │
│   │   ├── scheduler.py                    # APScheduler initialization
│   │   │                                   # Daily property + weekly market updates
│   │   │
│   │   └── geocoding.py (optional)         # Address to coordinates conversion
│   │
│   ├── utils/
│   │   ├── database.py                     # MongoDB connection manager
│   │   │                                   # Thread-safe, auto-reconnect
│   │   │                                   # Exponential backoff, URI parsing
│   │   │
│   │   └── validation.py                   # Shared ObjectId and input validation
│   │
│   ├── tests/
│   │   ├── test_financial_metrics.py       # ROI, cap rate calculations
│   │   ├── test_financing_options.py       # Loan comparison logic
│   │   ├── test_opportunity_scoring.py     # Scoring algorithm
│   │   ├── test_risk_assessment.py         # Risk evaluation
│   │   ├── test_routes.py                  # API endpoint testing
│   │   ├── test_tax_benefits.py            # Tax deduction calculations
│   │   └── conftest.py                     # pytest fixtures and setup
│   │
│   ├── Dockerfile                          # Multi-stage build for backend
│   ├── requirements.txt                    # Python dependencies
│   └── .env.example                        # Example environment variables
│
├── frontend/
│   ├── public/
│   │   └── index.html                      # HTML entry point
│   │
│   ├── src/
│   │   ├── App.js                          # React Router configuration
│   │   │                                   # Routes: /, /property/:id, /login
│   │   │
│   │   ├── components/
│   │   │   ├── Dashboard.js                # Property listing with filters
│   │   │   ├── PropertyDetail.js           # Tabbed analysis view
│   │   │   ├── PropertyCard.js             # Individual property display
│   │   │   ├── FilterPanel.js              # Advanced filter controls
│   │   │   ├── MapView.js                  # Leaflet map integration
│   │   │   │                               # Memory leak fixes, proper cleanup
│   │   │   ├── PropertyGallery.js          # Photo gallery view
│   │   │   ├── InvestmentSummary.js        # Key metrics overview
│   │   │   ├── InvestmentMetrics.js        # Detailed metrics table
│   │   │   ├── MarketMetricsChart.js       # Chart.js visualizations
│   │   │   ├── TopMarketsTable.js          # Ranked markets display
│   │   │   ├── ComparisonTable.js          # Multi-property comparison
│   │   │   ├── TaxBenefits.js              # Tax benefit breakdown
│   │   │   ├── FinancingCalculator.js      # Loan option calculator
│   │   │   ├── ErrorBoundary.js            # Render error recovery
│   │   │   ├── Login.js                    # Authentication view
│   │   │   └── NotFound.js                 # 404 route handler
│   │   │
│   │   ├── services/
│   │   │   └── api.js                      # apiClient for all API calls
│   │   │                                   # JWT auth, error handling, interceptors
│   │   │
│   │   ├── App.css                         # Global styles
│   │   └── index.js                        # React DOM render
│   │
│   ├── Dockerfile                          # Multi-stage build for frontend
│   ├── package.json                        # JavaScript dependencies
│   ├── tailwind.config.js                  # Tailwind CSS configuration
│   └── .env.example                        # Example env variables
│
├── docker-compose.yml                      # MongoDB, backend, frontend services
│                                           # Health checks, volume mounts
│
├── .env.example                            # Example environment variables
├── README.md                               # This file
└── LICENSE                                 # MIT License
```

## API Reference

### Properties Endpoints

| Method | Endpoint | Description | Auth | Query Params |
|--------|----------|-------------|------|--------------|
| GET | `/api/properties` | List properties with filtering & pagination | No | `minPrice`, `maxPrice`, `minBedrooms`, `minBathrooms`, `propertyType`, `city`, `state`, `zipCode`, `minScore`, `limit`, `page`, `sortBy`, `sortOrder` |
| POST | `/api/properties` | Create new property | Yes | — |
| GET | `/api/properties/<id>` | Get property by ID | No | — |
| PUT | `/api/properties/<id>` | Update property | Yes | — |
| DELETE | `/api/properties/<id>` | Delete property | Yes | — |

**GET /api/properties Example**:
```bash
curl "http://localhost:5000/api/properties?minPrice=100000&maxPrice=500000&minScore=70&city=Austin&state=TX&limit=20&page=1&sortBy=opportunity_score&sortOrder=desc"
```

**POST /api/properties Request Body**:
```json
{
  "address": "123 Main St",
  "city": "Austin",
  "state": "TX",
  "zipCode": "78701",
  "price": 350000,
  "bedrooms": 3,
  "bathrooms": 2,
  "sqft": 1800,
  "propertyType": "single_family",
  "yearBuilt": 2010,
  "estimatedMonthlyRent": 2200
}
```

### Analysis Endpoints

| Method | Endpoint | Description | Auth | Purpose |
|--------|----------|-------------|------|---------|
| GET | `/api/analysis/property/<id>` | Full property analysis | No | Financial + tax + financing metrics with defaults |
| POST | `/api/analysis/property/<id>` | Custom property analysis | No | Custom params: `down_payment_percentage`, `interest_rate`, `term_years`, `holding_period`, `appreciation_rate`, `tax_bracket`, `credit_score`, `veteran`, `first_time_va` |
| GET | `/api/analysis/market/<id>` | Market aggregation by location | No | Market-level statistics and trends |
| POST | `/api/analysis/market/<id>` | Custom market analysis | No | Custom parameters for market-level calculations |
| GET | `/api/markets/top` | Top markets by metric | No | Query: `metric` (roi, cap_rate, etc.), `limit` (default 10) |

**GET /api/analysis/property/:id Response**:
```json
{
  "property_id": "507f1f77bcf86cd799439011",
  "financial_metrics": {
    "roi": 12.5,
    "cap_rate": 8.2,
    "cash_on_cash": 15.3,
    "monthly_cash_flow": 450,
    "break_even_months": 24,
    "annual_cash_flow": 5400
  },
  "risk_assessment": {
    "market_risk": 35,
    "vacancy_risk": 25,
    "property_condition_risk": 20,
    "financing_risk": 30,
    "overall_risk_score": 28
  },
  "tax_benefits": {
    "annual_depreciation": 12000,
    "mortgage_interest_deduction": 18500,
    "property_tax_deduction": 4200,
    "total_annual_tax_benefits": 34700
  },
  "financing_options": [
    {
      "loan_type": "conventional",
      "monthly_payment": 1650,
      "total_interest": 193000,
      "apr": 6.5
    },
    {
      "loan_type": "fha",
      "monthly_payment": 1580,
      "total_interest": 185000,
      "apr": 6.2
    }
  ],
  "opportunity_score": 78,
  "investment_strength": "strong"
}
```

**POST /api/analysis/property/:id Request Body**:
```json
{
  "down_payment_percentage": 20,
  "interest_rate": 6.5,
  "term_years": 30,
  "holding_period": 10,
  "appreciation_rate": 3.5,
  "tax_bracket": 0.32,
  "credit_score": 750,
  "veteran": false,
  "first_time_va": false
}
```

### Authentication Endpoints

| Method | Endpoint | Description | Auth | Body |
|--------|----------|-------------|------|------|
| POST | `/api/auth/register` | Register new user | No | `username`, `password` |
| POST | `/api/auth/login` | Login & get JWT token | No | `username`, `password` |
| POST | `/api/auth/logout` | Logout (invalidate token) | Yes | — |

**POST /api/auth/login Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

### Health Check Endpoints

| Method | Endpoint | Description | Use Case |
|--------|----------|-------------|----------|
| GET | `/health` | Shallow health check (fast) | Load balancer probes |
| GET | `/health/ready` | Deep health check | Readiness probe (checks MongoDB) |
| GET | `/health/live` | Liveness probe | Keep-alive checks |

**GET /health Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-03T14:23:45Z"
}
```

## Getting Started

### Prerequisites

- **Docker & Docker Compose** (recommended) OR:
  - Python 3.9+
  - Node.js 14+ and npm
  - MongoDB 4.4+ (if not using Docker)

### Option 1: Docker (Recommended)

The fastest way to get the application running locally.

```bash
# Clone the repository
git clone https://github.com/yourusername/real-estate-analyzer.git
cd real-estate-analyzer

# Copy example environment file and customize
cp .env.example .env

# Edit .env with your settings (especially JWT_SECRET - see Security section)
nano .env

# Start all services (MongoDB, backend, frontend)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Access the application at**: http://localhost:3000

**Access backend API at**: http://localhost:5000/api

The docker-compose configuration includes:
- **MongoDB**: Running on port 27017 with health checks
- **Backend**: Python Flask on port 5000 with Gunicorn (4 workers)
- **Frontend**: React development server on port 3000
- **Volumes**: MongoDB data persisted to `mongodb_data/`

### Option 2: Manual Installation

For development with hot-reload and local debugging.

#### Backend Setup

```bash
# Clone and navigate to project
git clone https://github.com/yourusername/real-estate-analyzer.git
cd real-estate-analyzer/backend

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r ../requirements.txt

# Ensure MongoDB is running
# If installed locally: mongod
# Or use Docker: docker run -d -p 27017:27017 mongo:latest

# Configure environment variables (from project root)
cd ..
cp .env.example .env
nano .env

# Start Flask development server
cd backend
python app.py
```

The backend will start at http://localhost:5000

#### Frontend Setup

```bash
# In a new terminal, from project root
cd frontend

# Install Node dependencies
npm install

# Start development server
npm start
```

The frontend will open at http://localhost:3000

#### Verify Installation

```bash
# Test backend API
curl http://localhost:5000/health

# Test frontend is running
curl http://localhost:3000
```

### Initial Data Population

```bash
# The scheduler automatically fetches data daily, but to populate initially:
cd backend
python -c "from services.data_collection.data_collection_service import DataCollectionService; DataCollectionService().collect_properties()"
```

## Testing

### Run All Tests

```bash
cd backend

# Run all 405 tests with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=services --cov=models --cov=routes

# Run specific test file
pytest tests/test_financial_metrics.py -v

# Run tests matching a pattern
pytest tests/ -k "roi" -v
```

### Test Files

- **test_financial_metrics.py**: ROI, cap rate, cash-on-cash, break-even calculations; includes zero-investment ROI guard test
- **test_financing_options.py**: Conventional, FHA, VA loan comparisons
- **test_opportunity_scoring.py**: 0-100 composite scoring algorithm
- **test_risk_assessment.py**: Risk evaluation across dimensions
- **test_routes.py**: 62 API endpoint tests (24 base + 23 v1.3.0 + 15 v1.4.0)
- **test_tax_benefits.py**: Depreciation and tax deduction calculations
- **test_validation.py**: 7 tests for shared validation utility (ObjectId, parameters, username)
- **conftest.py**: pytest fixtures and MongoDB test setup

### Test Coverage

The project maintains **100% test pass rate** with 405 tests covering:
- Financial calculation accuracy
- API endpoint behavior
- Authentication flows
- Data persistence
- Error handling
- Edge cases

## Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Database Configuration
DATABASE_URL=mongodb://localhost:27017/realestate

# JWT Secret (CRITICAL - see Security section below)
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=your_very_long_random_secret_key_minimum_32_characters

# Frontend Configuration
REACT_APP_API_URL=http://localhost:5000/api

# Backend Configuration
FLASK_DEBUG=true                          # Set to 'false' in production
FLASK_ENV=development                     # Use 'production' in production
WORKERS=4                                 # Gunicorn worker count

# Data Collection (optional for Zillow scraping)
# ZILLOW_API_KEY=your_api_key_here

# Rate Limiting (optional)
RATELIMIT_ENABLED=true
RATELIMIT_REQUESTS=100
RATELIMIT_PERIOD=3600

# Caching (optional)
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300
```

### Example .env File

```bash
# .env
DATABASE_URL=mongodb://mongo:27017/realestate
JWT_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
REACT_APP_API_URL=http://localhost:5000/api
FLASK_DEBUG=true
FLASK_ENV=development
WORKERS=4
```

## Security

### JWT_SECRET Configuration (CRITICAL)

The `JWT_SECRET` environment variable is used to sign and verify JSON Web Tokens. This must be:

1. **Long and random**: At least 32 characters (64+ recommended)
2. **Cryptographically secure**: Use a proper random generator
3. **Unique per environment**: Different secrets for dev, staging, production
4. **Never hardcoded**: Always use environment variables
5. **Kept secret**: Never commit to version control

#### Generate a Secure JWT_SECRET

```bash
# Using Python
python -c "import secrets; print(secrets.token_hex(32))"
# Output example: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# Using OpenSSL
openssl rand -hex 32

# Using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

Add to your `.env`:
```bash
JWT_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

### Security Best Practices

1. **Bcrypt Passwords**: All user passwords are hashed with bcrypt (12 rounds)
2. **JWT Tokens**: Tokens expire after configurable period (default: 1 hour)
3. **Rate Limiting**: API endpoints protected with configurable rate limits (default: 100 req/hour)
4. **CORS Configuration**: Restricted to configured frontend origins
5. **Content-Security-Policy**: CSP headers on all responses preventing XSS attacks
6. **HTML Escaping**: Map popups use `escapeHtml()` helper to prevent DOM-based XSS
7. **Input Validation**:
   - ObjectId format validation on all ID-based endpoints (400 on invalid)
   - Username: 3-64 chars, alphanumeric + `_.-` only
   - Analysis parameters with bounds: term_years [1,40], holding_period [1,30], interest_rate [0.001,0.30]
   - Listing URL validation: only `http://` and `https://` schemes allowed
   - Pagination bounds: limit [1,100], page >= 1
   - Query parameter injection prevention on numeric filters
8. **Null Body Handling**: POST/PUT endpoints return 400 on missing or invalid JSON body
9. **Mass Assignment Prevention**: PUT properties whitelists updatable fields only
10. **Database Connection**: Secure MongoDB connection with authentication support
11. **Security Headers**:
    - Content-Security-Policy (CSP) prevents inline script execution
    - X-Content-Type-Options: nosniff prevents MIME sniffing
    - X-Frame-Options: DENY prevents clickjacking
    - X-XSS-Protection: 1; mode=block for legacy browser support
    - Referrer-Policy: strict-origin-when-cross-origin controls referrer leaking
    - HSTS: Enforces HTTPS in production
12. **Request Logging**: All API requests logged for auditing
13. **Environment Separation**: Dev, staging, and production have separate configs
14. **HTTPS in Production**: Always use HTTPS for JWT token transmission

### Deployment Security Checklist

Before deploying to production:

- [ ] Generate strong, random `JWT_SECRET` (64+ hex characters)
- [ ] Set `FLASK_DEBUG=false` and `FLASK_ENV=production`
- [ ] Enable HTTPS/TLS on all endpoints
- [ ] Configure MongoDB authentication with strong passwords
- [ ] Set strong `DATABASE_URL` credentials
- [ ] Enable rate limiting on public endpoints
- [ ] Configure CORS to allowed frontend domains only
- [ ] Set up request logging and monitoring
- [ ] Enable database backups and point-in-time recovery
- [ ] Use environment variables for all secrets (no hardcoding)
- [ ] Review and test all error messages (no sensitive info leak)
- [ ] Set up health check endpoints for monitoring
- [ ] Configure API key rotation policies
- [ ] Enable audit logging for user actions
- [ ] Test authentication and authorization thoroughly

## Development Workflow

### Code Style

- **Backend**: Follow PEP 8 (Python style guide)
- **Frontend**: Follow Airbnb React style guide
- Both use linting (eslint for JavaScript, flake8 for Python)

### Making Changes

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and write tests
3. Run the test suite: `pytest tests/ -v`
4. Commit with descriptive messages
5. Push and create a pull request

### Database Migrations

MongoDB collections are created automatically on first write. To add new fields:

1. Update the data model in `models/property.py`
2. Create a migration script if needed for existing data
3. Update API validators accordingly
4. Add tests for new fields

## Troubleshooting

### MongoDB Connection Issues

```bash
# Check if MongoDB is running
docker ps | grep mongo

# View MongoDB logs
docker-compose logs mongo

# Reset MongoDB (warning: deletes data)
docker-compose down
docker volume rm real-estate-analyzer_mongodb_data
docker-compose up -d
```

### Backend API Not Responding

```bash
# Check if backend container is running
docker ps | grep backend

# View backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Frontend Not Loading

```bash
# Check if frontend container is running
docker ps | grep frontend

# View frontend logs
docker-compose logs frontend

# Clear npm cache and reinstall
cd frontend
npm cache clean --force
npm install
npm start
```

### JWT Authentication Errors

```bash
# Ensure JWT_SECRET is set and non-empty
echo $JWT_SECRET

# Verify token in request header
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5000/api/properties
```

## Performance Optimization

### Database Indexing

The following indexes are automatically created:
- Property: `city`, `state`, `zipCode`, `price`, `opportunity_score`
- Market: Location-based geospatial queries

### API Response Caching

- GET endpoints cached for 5 minutes
- Invalidated on POST/PUT/DELETE operations
- Configurable via `CACHE_DEFAULT_TIMEOUT` env var

### Frontend Optimization

- Code splitting by route
- Lazy loading of heavy components
- Debouncing on filter changes
- Image optimization in property galleries

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request with description

See CONTRIBUTING.md for detailed guidelines.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or feature requests:

1. Check existing GitHub issues
2. Create a new issue with detailed description
3. Include steps to reproduce for bugs
4. Provide environment details (OS, Python version, etc.)

## Roadmap

Planned features for future releases:

- [ ] Advanced market analysis with ML predictions
- [ ] Property image processing and analysis
- [ ] REITs and crowdfunding integration
- [ ] Mobile app (React Native)
- [ ] Advanced portfolio management
- [ ] Automated property matching alerts
- [ ] Integration with real estate APIs (MLS, etc.)
- [ ] Neighborhood analysis and crime data
- [ ] School district ratings integration
- [ ] Export reports (PDF, Excel)

## Acknowledgments

Built with:
- Flask and Flask-RESTful for the backend API
- React for the frontend
- MongoDB for data persistence
- Chart.js and Leaflet for visualizations
- Docker for containerization
