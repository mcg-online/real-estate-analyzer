# Real Estate Analyzer - Project Instructions

## Project Overview

Full-stack real estate investment analysis tool with three main components:
- **Backend**: Flask REST API with MongoDB for property and market data analysis
- **Frontend**: React SPA with interactive dashboards and property comparison tools
- **Services**: Financial metrics, risk assessment, opportunity scoring, and tax benefit analysis

## Key Commands

### Testing
```bash
cd backend && source venv/bin/activate && pytest tests/ -v
```
Run the comprehensive test suite (405 tests across 8 files).

### Backend Validation
```bash
cd backend && source venv/bin/activate && python -c "from app import app; print('OK')"
```
Quick import check to verify all dependencies are installed and app starts without errors.

### Frontend Build
```bash
cd frontend && NODE_OPTIONS=--openssl-legacy-provider npx react-scripts build
```
Build optimized production bundle. NODE_OPTIONS is required for Node.js v24 compatibility with react-scripts.

### Linting
```bash
cd backend && source venv/bin/activate && ruff check .
```
Check code quality with ruff static analyzer.

### Docker
```bash
docker-compose up -d
```
Start all services: Flask backend, MongoDB, and React frontend (via node).

## Architecture Notes

### Data Conversions
- **Market objects to dicts**: Analysis services require dicts, not Market objects. Always convert with `.to_dict()` before passing to financial_metrics, risk_assessment, or opportunity_scoring services.
- **MongoDB ObjectIds**: Preserve as ObjectId in `from_dict()` methods. String ObjectIds cause silent failures in subsequent `save()` calls. Use `ObjectId(id_string)` for deserialization.
- **Datetime serialization**: All datetime fields (created_at, updated_at) require `.isoformat()` in `to_dict()` for proper JSON serialization.

### Financial Calculations
- **Division-by-zero guards**: Required in all financial methods:
  - `estimate_rental_income()`: guard if sqft <= 0
  - `calculate_cap_rate()`: guard if purchase_price <= 0
  - `calculate_cash_on_cash_return()`: guard if cash_down <= 0
  - `analyze_property()`: guard before any dividend operations
- **Aggregation pipelines**: Add `$match: {sqft: {$gt: 0}, price: {$gt: 0}}` pre-filters to prevent division-by-zero in downstream calculations.

### Model Methods
- **Property.from_dict()**: Returns None on failure; `find_all()` filters out None results. Use defensive `.get()` calls with sensible defaults.
- **Market.from_dict()**: Similar defensive pattern. Skips corrupted documents gracefully.
- **Property.find_all()**: Supports sort_by and sort_order parameters for flexible queries.

### Configuration
- **Flask-JWT-Extended**: Uses `JWT_SECRET_KEY` config key (NOT `SECRET_KEY`). Startup validation rejects placeholder values: 'your_secret_key', 'changeme', 'secret'.
- **Flask-Limiter v3**: Constructor takes `key_func` as first positional argument: `Limiter(get_remote_address, app=app, ...)`.
- **FLASK_DEBUG**: Should be environment-controlled via .env (not hardcoded in app.py).

## Testing Patterns

### Mocking Routes
Patch at the import site, not the definition site:
```python
# Correct
@patch('routes.users.get_db')
def test_login(mock_get_db):
    ...

# Incorrect
@patch('utils.database.get_db')
def test_login(mock_get_db):
    ...
```

### Financial Assertions
Use `pytest.approx()` for floating-point comparisons with rounding tolerance:
```python
assert result == pytest.approx(expected, abs=2.0)
```

### Test Coverage
- All tests run without MongoDB (fully mocked with MagicMock)
- No external dependencies required to run test suite
- 405 tests total across test_*.py files in backend/tests/

## Database

### MongoDB Indexes
Performance indexes created automatically on startup:
- state: for regional filtering
- (state, city): for market analysis
- zip_code: for property lookup
- market_type: for investment type analysis
- username: for user queries

### Connection Resilience
- Auto-reconnect with exponential backoff on connection loss
- Health checks via MongoDB ping on every `get_db()` call
- Connection pool: maxPoolSize=50, retryWrites=true, retryReads=true
- Graceful degradation: app starts even if MongoDB is unavailable

## Health Checks

Three health endpoints for monitoring:
- **GET /health**: Basic health check (always 200)
- **GET /health/live**: Liveness probe (always 200)
- **GET /health/ready**: Readiness probe (200 only if MongoDB connected and scheduler healthy)

## Known Constraints

- **Python**: 3.9.6 on local macOS system
- **Node.js**: v24 requires NODE_OPTIONS=--openssl-legacy-provider for react-scripts
- **MongoDB**: Not required locally; app starts gracefully without it
- **Dependencies**: See requirements.txt and package.json for version constraints

## Project Structure

```
real-estate-analyzer/
├── backend/
│   ├── app.py                  # Flask application entry point
│   ├── requirements.txt         # Python dependencies
│   ├── models/                 # MongoDB models (Property, Market, User)
│   ├── routes/                 # API endpoints
│   ├── services/               # Business logic (financial, risk, opportunity)
│   ├── utils/                  # Database, logging, utilities
│   └── tests/                  # Comprehensive pytest suite (512 tests)
├── frontend/
│   ├── src/
│   │   ├── App.js             # React Router setup
│   │   ├── index.js           # Entry point
│   │   ├── index.css          # Tailwind CSS
│   │   ├── components/        # React components
│   │   └── pages/             # Page components
│   ├── public/index.html       # HTML template
│   └── package.json            # Node dependencies
├── docker-compose.yml          # Service orchestration (Flask, MongoDB, Node)
├── Dockerfile                  # Production Flask server with gunicorn
├── CHANGELOG.md                # Version history
├── CODEMAP.md                  # Complete code map with data flows
├── TODO.md                     # Known issues, roadmap, testing gaps
├── SECURITY.md                 # Security policy and features
└── CLAUDE.md                   # This file
```

## Recent Changes (v1.5.0)

- Property ownership: `user_id` tracked from JWT, PUT/DELETE enforce ownership (403), backward-compatible for legacy properties
- API versioning: dual-path routes at `/api/v1/*` and `/api/*`
- Redis integration: JWT blocklist, rate limiter, cache use Redis when available, fallback to in-memory
- React 18 + react-router v6 + axios 1.x migration
- Frontend apiClient targets `/api/v1`
- FilterPanel ARIA accessibility, FinancingCalculator slider debounce (300ms)
- 107 new backend tests across 4 new files (512 total, all passing)

### v1.4.0

- apiClient JWT auth fix, XSS prevention, parameter validation, null body handling
- 405 tests

### v1.3.0

- Fixed mass assignment vulnerability, query param validation, pagination bounds
- Added CSP header, JWT token expiration, ErrorBoundary, 404 route
- Fixed datetime deprecation, zero-interest-rate division-by-zero
- Fixed frontend paginated response handling, MapView memory leak
- 390 tests

### v1.2.0

- Removed numpy dependency (replaced with pure Python clamping)
- Added ObjectId format validation on all ID-based routes (400 on invalid IDs)
- Fixed `datetime.utcnow()` deprecation across models (now timezone-aware)
- Added scheduler thread watchdog with heartbeat and auto-restart
- 367 tests all passing

### v1.1.0

- Security hardening (JWT, production server, validation)
- Critical bug fixes (Market object/dict mismatch, ObjectId stringification, datetime serialization)
- Resilience improvements (auto-reconnect, health checks, MongoDB indexes)
- 4 new health check endpoint tests

See CHANGELOG.md for complete details.
