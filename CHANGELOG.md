# Changelog

All notable changes to the Real Estate Analyzer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-03-03

### Security Fixes
- Fixed JWT configuration: Flask-JWT-Extended requires `JWT_SECRET_KEY`, was incorrectly using `SECRET_KEY`
- Added startup validation rejecting placeholder JWT secrets ('your_secret_key', 'changeme', 'secret')
- Changed Dockerfile from `python app.py` (debug mode) to `gunicorn` with 4 workers for production
- Made `FLASK_DEBUG` environment-controlled instead of hardcoded `debug=True`

### Bug Fixes
- Fixed Market object vs dict mismatch: analysis services crashed when real market data existed in DB because Market objects don't have `.get()` method. Now converts Market objects to dicts before passing to services.
- Fixed Market._id stringification: `from_dict()` was converting ObjectId to string, causing all subsequent `save()` calls to silently fail (string _id doesn't match ObjectId in MongoDB)
- Fixed Market.to_dict() datetime serialization: `created_at`/`updated_at` datetime objects caused JSON serialization errors
- Added division-by-zero guards in FinancialMetrics: `estimate_rental_income`, `calculate_cap_rate`, `calculate_cash_on_cash_return`, `analyze_property`
- Fixed MongoDB URI parsing: replaced naive `split('/')[-1]` with `urlparse()` to handle query parameters

### Resilience Improvements
- Added auto-reconnect to database.py: thread-safe reconnection with exponential backoff on connection loss
- Added connection health checks via MongoDB ping on every `get_db()` call
- Added connection pool configuration (maxPoolSize=50, retryWrites, retryReads)
- Added MongoDB indexes for performance: state, (state,city), zip_code, market_type, username
- Added sqft>0 and price>0 pre-filters in aggregation pipelines to prevent division-by-zero
- Made Property.from_dict() and Market.from_dict() defensive: uses `.get()` with defaults, skips corrupted documents
- Added request logging middleware with request IDs and latency tracking

### New Features
- Added health check endpoints: GET /health, GET /health/ready (checks MongoDB), GET /health/live
- Added Docker health checks for mongo and backend services in docker-compose.yml

### Infrastructure
- Updated docker-compose.yml: health checks, removed unused environment variables, service dependency conditions
- Updated Dockerfile: gunicorn production server
- Fixed ruff lint warning in scheduler.py

### Testing
- Added 4 new health check endpoint tests (362 → 366 total)
- All 366 tests passing

## [1.0.0] - 2026-03-03

### Phase 1: Critical Backend Bug Fixes
- Fixed app.py: removed duplicate code (lines 62-180 had duplicate imports, functions, routes)
- Fixed financial_metrics.py: indentation bug putting methods outside their class
- Fixed zillow_scraper.py: merged 3 separate class definitions into one
- Fixed routes/properties.py: added missing get_db import
- Fixed utils/database.py: added missing time import
- Fixed models/property.py: added sort_by/sort_order parameters to find_all()
- Fixed .env: removed pip install commands that were mixed in with env vars
- Fixed docker-compose.yml: added missing MongoDB service definition
- Fixed Flask-Limiter v3 API change (constructor argument order)
- Fixed complex number bug in ROI annualization (negative ROI edge case)
- Fixed VA loan missing total_monthly_payment key
- Fixed Property.to_dict() datetime serialization
- Added flask-cors to requirements.txt

### Phase 2: Completed Backend Services
- Implemented opportunity_scoring.py: 0-100 composite score across financial, market, risk, and tax dimensions
- Completed risk_assessment.py: market volatility, vacancy risk, property condition, financing risk with weighted composite
- Fixed data_collection_service.py: removed references to non-existent connectors
- Implemented users.py: MongoDB-backed registration/login with bcrypt password hashing

### Phase 3: Fixed and Completed Frontend
- Created App.js with React Router (/, /property/:id, /login)
- Created index.js entry point
- Fixed MapView.js: extracted MarketMetricsChart to separate file
- Fixed TaxBenefits.js: replaced duplicate PropertyDetail content with actual tax component
- Fixed Dashboard.js: wrapped bare text in proper JSX elements
- Fixed PropertyDetail.js: fixed orphaned JSX
- Created 7 missing components: PropertyCard, FilterPanel, InvestmentSummary, InvestmentMetrics, PropertyGallery, TopMarketsTable, ComparisonTable
- Created index.css with Tailwind setup
- Created public/index.html (required by react-scripts)
- Fixed FinancingCalculator.js malformed JSX

### Phase 4: Tests
- Created comprehensive pytest suite: 362 tests across 7 files
  - test_financial_metrics.py: 71 tests
  - test_financing_options.py: 72 tests
  - test_opportunity_scoring.py: 58 tests
  - test_risk_assessment.py: 84 tests
  - test_routes.py: 24 tests (with mocked MongoDB)
  - test_tax_benefits.py: 53 tests
- Created conftest.py with shared fixtures

### Phase 5: Documentation & Cleanup
- Created .gitignore
- Auto-fixed 16 unused imports with ruff
