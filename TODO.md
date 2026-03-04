# TODO - Real Estate Analyzer

This document tracks known issues, feature gaps, and improvement opportunities for the Real Estate Analyzer project.

## Completed in v1.5.0

These items have been successfully implemented and should not be revisited:

- **Ownership verification on PUT/DELETE property endpoints** - Property ownership model implemented with user_id linking. All PUT/DELETE endpoints enforce 403 Forbidden for non-owners.
- **Rate limiter and cache Redis backing** - Redis integration added for distributed rate limiting and caching across gunicorn workers.
- **JWT token blocklist persistence** - Redis-backed blocklist with in-memory fallback for distributed deployments.
- **Outdated frontend dependencies** - React upgraded to 18, react-router to v6, axios to 1.x.
- **Dead dependency: react-leaflet** - Removed from package.json.
- **FilterPanel accessibility issues** - ARIA labels, htmlFor associations, and role attributes added.
- **FinancingCalculator slider debounce** - useDebounce hook (300ms) implemented for optimized recalculation.
- **Unit tests for ZillowScraper, DataCollectionService, database.py** - Full coverage added (512 tests total).
- **Scheduler tests** - 18 tests added for watchdog thread, heartbeat tracking, and auto-restart logic.
- **API versioning** - Dual-path routes (/api/v1/* and /api/*) implemented for forward compatibility.

## Known Issues (Low Priority)

- **No circuit breaker for Zillow scraper service** - Scraper can fail repeatedly without backoff, hammering the Zillow API. Add circuit breaker pattern with exponential backoff.
- **Mixed async/sync in ZillowScraper** - Uses aiohttp for async HTTP but not fully async throughout. Refactor to pure async or pure sync.

## Frontend Issues

- **No frontend tests** - All 512 tests are backend only. Add Jest/React Testing Library tests for components.
- **Duplicate Chart.js register() calls** - Multiple components register the same Chart.js plugins. Consolidate to single location.

## Architecture Improvements

- **Add pagination cursor-based option** - Implement cursor-based pagination alongside offset/limit for large datasets.
- **Add request validation middleware** - Centralize input validation instead of duplicating validation logic in each route handler.
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

## Documentation

- **CONTRIBUTING.md** - Add PR guidelines, commit message format, branch naming conventions.
- **Deployment guide** - Add deployment instructions for AWS, GCP, Azure, DigitalOcean.
- **Architecture Decision Records (ADRs)** - Document key architectural decisions with rationale and alternatives.
- **Security hardening guide** - Document security best practices for deployment (SSL/TLS, secrets management, etc.).
- **Performance tuning guide** - Document MongoDB indexing, query optimization, and caching strategies.
- **Troubleshooting guide** - Add common issues and solutions (MongoDB connection issues, JWT errors, CORS problems).

---

**Last updated**: 2026-03-04
**Contributors**: Development Team
**Current version**: v1.5.0 (512 tests, Redis integration, ownership enforcement, modernized frontend)
