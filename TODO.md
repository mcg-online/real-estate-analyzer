# TODO - Real Estate Analyzer

This document tracks known issues, feature gaps, and improvement opportunities for the Real Estate Analyzer project.

## Completed in v1.6.0

- **Frontend tests** - 132 Jest/React Testing Library tests across 14 suites covering all components.
- **Integration/E2E tests** - 64 cross-endpoint API flow tests covering user lifecycle, CRUD, ownership, search, analysis, error cascades, versioning parity, and rate limiting.
- **Contract tests** - 50 frontend-backend API contract tests verifying response shapes across all endpoints.
- **Chart.js consolidation** - Duplicate `ChartJS.register()` calls consolidated into single `chartSetup.js` module.
- **Circuit breaker for Zillow scraper** - Circuit breaker pattern (CLOSED/OPEN/HALF_OPEN) with failure threshold and recovery timeout.
- **Mixed async/sync in ZillowScraper** - Refactored with `_run_maybe_coroutine()` helper for consistent async/sync handling.
- **Cursor-based pagination** - Opt-in cursor pagination via `?cursor=<objectid>` alongside existing offset/limit (36 tests).
- **Load/performance tests** - Locust load tests with 3 user profiles (browsing, authenticated, heavy analysis).
- **Documentation** - CONTRIBUTING.md, DEPLOYMENT.md, TROUBLESHOOTING.md, and 4 Architecture Decision Records (ADRs).
- **Frontend dependency security** - Babel version conflicts resolved via npm overrides; build verified.
- **Request validation middleware** - Centralized `require_json_body`, `validate_objectid`, `require_entity` decorators (33 tests).
- **Flask application factory pattern** - `create_app(config)` factory with BaseConfig/TestingConfig/ProductionConfig classes.

## Completed in v1.5.0

- **Ownership verification on PUT/DELETE property endpoints** - Property ownership model implemented with user_id linking.
- **Rate limiter and cache Redis backing** - Redis integration for distributed rate limiting and caching.
- **JWT token blocklist persistence** - Redis-backed blocklist with in-memory fallback.
- **Outdated frontend dependencies** - React 18, react-router v6, axios 1.x.
- **Dead dependency: react-leaflet** - Removed from package.json.
- **FilterPanel accessibility issues** - ARIA labels, htmlFor associations, and role attributes.
- **FinancingCalculator slider debounce** - useDebounce hook (300ms) for optimized recalculation.
- **Unit tests for ZillowScraper, DataCollectionService, database.py** - Full coverage (512 tests total).
- **Scheduler tests** - 18 tests for watchdog thread, heartbeat tracking, and auto-restart.
- **API versioning** - Dual-path routes (/api/v1/* and /api/*) for forward compatibility.

## Feature Roadmap

- Advanced market analysis with ML predictions
- Property image processing and analysis (computer vision)
- REITs and crowdfunding integration
- Mobile app (React Native)
- Advanced portfolio management with rebalancing suggestions
- Automated property matching alerts and notifications
- Integration with real estate APIs (MLS, Redfin, Zillow)
- Neighborhood analysis and crime data integration
- School district ratings integration
- Export reports (PDF, Excel, CSV)
- WebSocket support for real-time property updates
- Saved search filters and favorites
- Price history charts and trend analysis
- Comparable sales (comps) analysis
- Investment portfolio tracking across multiple properties

---

**Last updated**: 2026-03-04
**Contributors**: Development Team
**Current version**: v1.6.0 (800+ tests, factory pattern, validation middleware, full test coverage)
