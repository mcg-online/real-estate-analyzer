# ADR 003: API Versioning Strategy

**Status**: Accepted (v1.5.0+)

**Date**: 2024-09-01

**Deciders**: Development Team

## Context

The Real Estate Analyzer API has evolved through multiple versions (v1.0-v1.5) with:
- New features (property ownership, API versioning, Redis integration)
- Bug fixes (JWT handling, XSS prevention, datetime serialization)
- Backward compatibility requirements

API consumers include:
- Web frontend (React SPA)
- Mobile apps (potential)
- Third-party integrations (external systems)
- Legacy deployments (still running v1.0)

Challenges:
- **Breaking Changes**: How to introduce incompatible changes without breaking consumers?
- **Deprecation**: How to signal that endpoints will be removed?
- **Migration**: How to help users transition to new versions?
- **Support**: How long to support old API versions?

## Decision

We chose **dual-path versioning** with `/api/v1/*` and `/api/*` routes for backward compatibility.

### 1. Dual-Path Route Registration

Every API endpoint available at both paths:

```python
# app.py - Each resource registered twice
api.add_resource(PropertyListResource, '/api/v1/properties', '/api/properties')
api.add_resource(PropertyResource, '/api/v1/properties/<property_id>', '/api/properties/<property_id>')
api.add_resource(PropertyAnalysisResource, '/api/v1/analysis/property/<property_id>', '/api/analysis/property/<property_id>')
api.add_resource(MarketAnalysisResource, '/api/v1/analysis/market/<market_id>', '/api/analysis/market/<market_id>')
api.add_resource(TopMarketsResource, '/api/v1/markets/top', '/api/markets/top')
api.add_resource(OpportunityScoringResource, '/api/v1/analysis/score/<property_id>', '/api/analysis/score/<property_id>')
api.add_resource(UserRegistration, '/api/v1/auth/register', '/api/auth/register')
api.add_resource(UserLogin, '/api/v1/auth/login', '/api/auth/login')
api.add_resource(UserLogout, '/api/v1/auth/logout', '/api/auth/logout')
```

Benefits:
- **Backward Compatibility**: Old code calling `/api/*` still works
- **Forward Direction**: New code can use `/api/v1/*`
- **No Duplication**: Same resource class handles both paths
- **Simple Transition**: Gradual migration from `/api/*` to `/api/v1/*`

### 2. Versioned Paths for Future Versions

When creating v2 API:

```python
# v1 continues to work
api.add_resource(PropertyListResource_v1, '/api/v1/properties', '/api/properties')

# v2 introduces new format/behavior
api.add_resource(PropertyListResource_v2, '/api/v2/properties')

# Old `/api/*` routes updated to point to latest version
api.add_resource(PropertyListResource_v2, '/api/v2/properties', '/api/properties')
```

### 3. Version Detection via Header (Not Used, But Reserved)

For future advanced use cases, support version via header:

```python
@app.before_request
def detect_version():
    # API-Version header, defaults to latest
    request.api_version = request.headers.get('API-Version', 'v1')
    # Could route to different handlers based on version
```

Current implementation uses URL paths only (simpler, more standard).

### 4. Response Format Consistency

All API responses use consistent structure across versions:

```javascript
// GET /api/v1/properties (paginated endpoint)
{
  "data": [
    {
      "_id": "...",
      "address": "...",
      "price": 500000,
      ...
    }
  ],
  "total": 142,
  "page": 1,
  "limit": 10,
  "pages": 15
}

// GET /api/properties (same response)
{
  "data": [ ... ],
  "total": 142,
  "page": 1,
  "limit": 10,
  "pages": 15
}

// Error format (same across versions)
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field: price"
  }
}
```

### 5. Frontend Uses Versioned Path

The React frontend targets the versioned path:

```javascript
// src/services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api/v1';

// All calls go to /api/v1/*
export const getProperties = (filters) =>
  apiClient.get(`${API_BASE_URL}/properties`, { params: filters });

export const analyzeProperty = (propertyId, params) =>
  apiClient.get(`${API_BASE_URL}/analysis/property/${propertyId}`, { params });
```

This:
- Makes frontend intent clear (using v1 API)
- Easier to identify which version new features target
- Allows frontend to upgrade when v2 is ready

### 6. Deprecation & Migration Path

#### For Backward Incompatible Changes

1. **Announce**: Document breaking change in CHANGELOG
   ```markdown
   ### v2.0.0 (Breaking Changes)
   - [BREAKING] PropertyListResource now returns data in 'properties' field instead of root array
   - [DEPRECATED] /api/* paths replaced by /api/v2/* (v1 paths continue to work)
   ```

2. **Plan**: 6-month support window for v1
   ```markdown
   - v1 API supported until 2024-09-01
   - v2 API becomes default after 2024-09-01
   - /api/* routes redirected to /api/v2/* after 2024-12-01
   ```

3. **Warn**: Add deprecation headers in responses
   ```python
   @app.after_request
   def add_deprecation_headers(response):
       if request.path.startswith('/api/') and not request.path.startswith('/api/v'):
           response.headers['Deprecation'] = 'true'
           response.headers['Sunset'] = 'Sun, 01 Sep 2024 00:00:00 GMT'
           response.headers['Link'] = '</api/v2/...>; rel="successor-version"'
       return response
   ```

4. **Migrate**: Provide migration guide
   ```markdown
   # Migrating from v1 to v2 API

   ## What Changed
   - Response format for property listing...
   - Authentication mechanism...

   ## Migration Steps
   1. Update API endpoints from `/api/` to `/api/v2/`
   2. Update response parsing (new format)
   3. Test in staging environment
   4. Deploy to production
   ```

### 7. Supporting Multiple Versions Long-Term

Version support strategy:

| Version | Release | Support Until | Status |
|---------|---------|---------------|--------|
| v1.5    | Jan 2024 | Sep 2024 | Current |
| v2.0    | Sep 2024 | Sep 2025 | Future |
| v3.0    | Sep 2025 | Sep 2026 | Future |

Each version receives:
- **Bug Fixes**: 12 months
- **Security Patches**: 18 months
- **Feature Development**: Only latest version

## Consequences

### Positive

1. **Backward Compatibility**: Old clients continue to work indefinitely
2. **Smooth Transitions**: Gradual migration from old to new API versions
3. **Clear Intent**: `/api/v1/*` makes version explicit
4. **URL-Based Versioning**: Standard HTTP practice, caching-friendly
5. **Simple Implementation**: No conditional logic needed for versioning

### Negative

1. **Code Duplication**: Same resource classes registered twice
   - **Mitigation**: Use resource base classes (already done)
2. **Multiple Versions to Maintain**: Longer support window increases burden
   - **Mitigation**: Limit support window (12-18 months per version)
3. **Confusion**: Users unclear which version to use
   - **Mitigation**: Clear documentation and deprecation warnings
4. **No Automatic Upgrade**: Clients must change code to use new version
   - **Mitigation**: Provide migration guides

### Alternative Approaches Considered

#### 1. Content Negotiation (Accept Header)
```javascript
// Request specifies version via header
Accept: application/vnd.realestate.v1+json
```

**Pros**: Cleaner URLs, content-negotiation standard
**Cons**: Less visible, harder to cache, not RESTful

#### 2. URL Path with Query String
```
GET /api/properties?version=1
GET /api/properties?version=2
```

**Pros**: Single path, flexible
**Cons**: Versioning in query params is non-standard, hard to proxy/cache

#### 3. URL Path with Sub-domain
```
https://api-v1.realestate.com/properties
https://api-v2.realestate.com/properties
```

**Pros**: Clear separation, easy to scale independently
**Cons**: DNS complexity, certificate management, infrastructure overhead

We chose URL path versioning (`/api/v1/*`) because:
- **Standard**: RESTful API standard practice
- **Explicit**: Version clear in every URL
- **Cache-Friendly**: Different versions cached separately
- **Simple**: No additional HTTP headers or subdomains needed

## Migration Guide for V1 -> V2 (Future)

### Before V2 Release

1. Announce in CHANGELOG and documentation
2. Provide migration guide 6 months before v1 sunset
3. Set API-Version header in test environments to v2

### At V2 Release

1. Deploy v2 and v1 side-by-side
2. Monitor both versions for issues
3. Update frontend to use `/api/v2/*`
4. Continue supporting v1 for 6 more months

### V1 Sunset

1. Remove routes: `/api/v1/*` (keep `/api/*` for compatibility)
2. Redirect old v1 calls to v2 with warnings
3. Deprecate `/api/*` paths after 6 months

## References

- [Semantic Versioning](https://semver.org/)
- [REST API Versioning Best Practices](https://restfulapi.net/versioning/)
- [API Versioning Strategies](https://swagger.io/blog/api-versioning-in-openapi/)
- [IETF RFC 7231: Versioning](https://tools.ietf.org/html/rfc7231)

## Related Decisions

- **ADR 002**: JWT Authentication (same for all API versions)
- **ADR 004**: Redis Integration (available to all versions)
