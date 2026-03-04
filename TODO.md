# TODO - Real Estate Analyzer

This document tracks known issues, feature gaps, and improvement opportunities for the Real Estate Analyzer project.

## Known Issues (Low Priority)

- **No ownership verification on PUT/DELETE property endpoints** - Any authenticated user can modify any property. Implement property ownership model linking properties to creator users.
- **No circuit breaker for Zillow scraper service** - Scraper can fail repeatedly without backoff, hammering the Zillow API. Add circuit breaker pattern with exponential backoff.
- **Rate limiter and cache are in-process only** - Not Redis-backed for multi-worker gunicorn deployments. Scale to distributed rate limiting and caching.
- **Mixed async/sync in ZillowScraper** - Uses aiohttp for async HTTP but not fully async throughout. Refactor to pure async or pure sync.
- **JWT token blocklist is in-memory only** - Not persisted across restarts and not shared across workers. Move to Redis for distributed deployments.

## Frontend Issues

- **Outdated dependencies** - axios@0.21 (current is 1.x), React 17 (current is 18+), react-router v5 (current is v6)
- **No frontend tests** - All 405 tests are backend only. Add Jest/React Testing Library tests for components.
- **Dead dependency: react-leaflet** - Listed in package.json but MapView uses raw Leaflet directly instead of react-leaflet wrapper.
- **FilterPanel accessibility issues** - Missing ARIA labels and keyboard navigation support. Add role, aria-label, and keyboard event handlers.
- **Duplicate Chart.js register() calls** - Multiple components register the same Chart.js plugins. Consolidate to single location.
- **FinancingCalculator slider has no debounce** - Recalculates on every pixel of drag. Add debounced onChange handler or use input range with onChangeCapture.

## Architecture Improvements

- **Add Redis** - Implement shared rate limiting, caching, and JWT blocklist across gunicorn workers for production deployments.
- **Add property ownership model** - Link properties to users who created them. Enforce ownership checks on PUT/DELETE endpoints.
- **Add pagination cursor-based option** - Implement cursor-based pagination alongside offset/limit for large datasets.
- **Add request validation middleware** - Centralize input validation instead of duplicating validation logic in each route handler.
- **Add API versioning** - Prefix routes with /api/v1 to support future API changes without breaking clients.
- **Migrate to Flask application factory pattern** - Move app creation to factory function for easier testing and configuration management.

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

## Testing Gaps

- **No frontend tests** - Add Jest and React Testing Library for component testing (target: 70%+ coverage).
- **No integration tests** - Missing end-to-end API flow tests across multiple endpoints.
- **No load/performance tests** - Add stress tests with tools like locust or Apache JMeter.
- **No contract tests** - Add contract tests between frontend and backend API to catch breaking changes.
- **Missing unit tests** - Add coverage for ZillowScraper, DataCollectionService, database.py reconnection logic.
- **Missing scheduler tests** - Add tests for scheduler watchdog thread, heartbeat tracking, and auto-restart logic.

## Documentation

- **CONTRIBUTING.md** - Add PR guidelines, commit message format, branch naming conventions.
- **Deployment guide** - Add deployment instructions for AWS, GCP, Azure, DigitalOcean.
- **Architecture Decision Records (ADRs)** - Document key architectural decisions with rationale and alternatives.
- **Security hardening guide** - Document security best practices for deployment (SSL/TLS, secrets management, etc.).
- **Performance tuning guide** - Document MongoDB indexing, query optimization, and caching strategies.
- **Troubleshooting guide** - Add common issues and solutions (MongoDB connection issues, JWT errors, CORS problems).

---

**Last updated**: 2026-03-03
**Contributors**: Development Team
