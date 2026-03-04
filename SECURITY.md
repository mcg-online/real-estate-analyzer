# Security Policy

Real Estate Analyzer v1.4.0 - Security documentation and responsible disclosure guidelines.

## Supported Versions

| Version | Status | Support Until |
|---------|--------|---------------|
| 1.4.0   | Supported | Current |
| 1.3.0   | Supported | 6 months |
| 1.2.0   | Security fixes only | 3 months |
| < 1.2.0 | Unsupported | Upgrade required |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly:

**Email**: security@realestate-analyzer.local (or create a private security advisory on GitHub)

**Expected Response Time**: We will acknowledge your report within 48 hours and provide an estimated timeline for a fix.

**What to Include**:
- Detailed description of the vulnerability
- Steps to reproduce the issue
- Affected versions
- Suggested fix (if you have one)
- Your contact information (optional, for follow-up)

**Confidentiality**: Please do not publicly disclose the vulnerability until a fix is released. We will work with you to coordinate responsible disclosure.

## Security Features (v1.4.0)

### Authentication & Authorization

- **JWT Authentication** - Uses Flask-JWT-Extended for token-based authentication on protected endpoints
- **Bcrypt Password Hashing** - Passwords hashed with werkzeug.security for secure storage
- **Configurable Token Expiration** - JWT tokens expire after 1 hour (configurable via `JWT_EXPIRY_SECONDS` environment variable)
- **Token Blocklist for Logout** - Logout support via token revocation (in-memory blocklist in v1.4.0, Redis in v1.5.0+)
- **Startup Secret Validation** - Rejects weak JWT secrets on startup:
  - Rejects placeholder values: `your_secret_key`, `changeme`, `secret`
  - Requires minimum 32 characters for production deployments
  - Logs warning in development mode if weak secret detected

### Input Validation

- **ObjectId Format Validation** - All ID-based routes validate MongoDB ObjectId format, return 400 on invalid IDs
- **Username Validation** - 3-64 characters, alphanumeric with hyphens, underscores, and dots only (`[a-zA-Z0-9_.-]`)
- **Password Requirements** - Enforced at registration:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one digit
- **Analysis Parameter Bounds** - Enforced bounds on financial analysis inputs:
  - `term_years`: 1-40
  - `interest_rate`: 0.001-0.30
  - `down_payment_percent`: 0-100
  - `annual_rent`: >= 0
  - `holding_years`: 1-50
- **Query Parameter Type Validation** - GET /api/properties validates:
  - `sort_by`: whitelist validation (price, created_at, score)
  - `sort_order`: must be 'asc' or 'desc'
  - `limit`, `page`: positive integers within bounds
  - `state`, `city`, `zip_code`: string format validation
- **Pagination Bounds** - Enforced limits:
  - `limit`: 1-100 (default: 10)
  - `page`: >= 1 (default: 1)
- **Null Body Handling** - POST and PUT endpoints return 400 Bad Request on missing or invalid JSON

### XSS Prevention

- **HTML Escaping in Leaflet Popups** - Map popups escape HTML via `escapeHtml()` helper to prevent DOM-based XSS
- **URL Scheme Validation** - Listing URLs validated to only allow `http://` and `https://` schemes
- **Content-Security-Policy Header** - Restricts resource loading:
  - `default-src 'self'` - Only load resources from same origin
  - `frame-ancestors 'none'` - Prevent clickjacking via frame embedding

### Mass Assignment Prevention

- **PUT /api/properties Whitelist** - Only updatable fields allowed in request body:
  - `address`, `city`, `state`, `zip_code`
  - `purchase_price`, `rental_income`, `expenses`
  - `listing_url`, `notes`
- **Protected Fields** - These fields cannot be modified via API:
  - `_id` - MongoDB object ID
  - `created_at` - Creation timestamp
  - `updated_at` - Last modification timestamp
  - `metrics` - Calculated metrics
  - `score` - Opportunity score

### Security Headers

Applied to all HTTP responses by Flask middleware:

```
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains (production only)
```

### Rate Limiting

- **200 requests per day** per IP address
- **50 requests per hour** per IP address
- Enforced via Flask-Limiter
- Configurable via environment variables (`RATELIMIT_STORAGE_URL`, etc.)
- In-process implementation in v1.4.0 (use Redis backend for multi-worker deployments)

### CORS

- **Origin Whitelist** - Restricted to configured origins via `CORS_ORIGINS` environment variable
- **Credentials Support** - `supports_credentials=True` for cookie-based authentication
- **Allowed Methods** - GET, POST, PUT, DELETE, OPTIONS
- **Allowed Headers** - Content-Type, Authorization, Accept

### Request Logging & Monitoring

- **Request ID Tracking** - Each request assigned UUID prefix for correlation across logs
- **Latency Measurement** - Automatic latency tracking on all requests
- **Structured Logging Format** - JSON-formatted logs with request context:
  - `timestamp`, `level`, `message`
  - `request_id`, `method`, `path`, `status_code`
  - `latency_ms`, `user_id` (if authenticated)

## Known Limitations

These are security gaps that should be addressed in future versions:

- **JWT Blocklist is In-Memory** - Not shared across gunicorn worker processes or persisted across restarts. Tokens revoked via logout are only blocked in that specific worker. Upgrade to Redis-backed blocklist for production.
- **Rate Limiter is In-Process** - Limits are tracked per gunicorn worker, not globally across all workers. Multiple workers can bypass rate limits. Use Redis backend for distributed rate limiting.
- **No Ownership Verification on Property CRUD** - Any authenticated user can read, modify, or delete any property. Properties should be linked to users with ownership checks on PUT/DELETE.
- **No CSRF Protection** - Relies on JWT Bearer tokens (not vulnerable to traditional CSRF). If adding cookie-based sessions, implement CSRF tokens.
- **No API Key Rotation Mechanism** - If deploying with API keys, implement key rotation and versioning.
- **Cache is In-Process SimpleCache** - Not shared across workers or persisted. Use Redis for shared caching across gunicorn workers.
- **No Two-Factor Authentication** - Implement 2FA for sensitive operations (admin functions, account recovery).
- **No Audit Logging** - Add comprehensive audit trail for sensitive operations (property modifications, user account changes).

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-at-least-32-chars
JWT_EXPIRY_SECONDS=3600

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://example.com

# Database
MONGO_URI=mongodb://localhost:27017/real_estate

# Flask Environment
FLASK_ENV=production
FLASK_DEBUG=false

# Rate Limiting
RATELIMIT_STORAGE_URL=memory://
RATELIMIT_DEFAULT=200/day;50/hour

# Server
WORKERS=4
THREADS_PER_WORKER=4
```

### Production Deployment Checklist

- [ ] Set `FLASK_ENV=production` and `FLASK_DEBUG=false`
- [ ] Use strong `JWT_SECRET_KEY` (32+ random characters)
- [ ] Configure HTTPS/TLS with valid certificate
- [ ] Set `CORS_ORIGINS` to specific domains (not `*`)
- [ ] Enable `Strict-Transport-Security` header (automatic in production)
- [ ] Configure rate limiting with Redis backend
- [ ] Set up JWT token blocklist with Redis
- [ ] Enable request logging to persistent storage
- [ ] Configure database authentication (username/password)
- [ ] Enable MongoDB authentication and encryption
- [ ] Run security updates on all dependencies
- [ ] Set up monitoring and alerting for security events
- [ ] Implement backup and disaster recovery procedures

## Security Changelog

### v1.4.0 (Current)
- Added XSS prevention with HTML escaping in Leaflet popups
- Added URL scheme validation (only http/https allowed)
- Added username validation (3-64 chars, alphanumeric + hyphens/underscores/dots)
- Added parameter bounds validation for financial analysis inputs
- Added null body handling with 400 response
- Added CSP header `default-src 'self'; frame-ancestors 'none'`
- Added X-Frame-Options, X-Content-Type-Options, X-XSS-Protection headers
- Added Referrer-Policy and HSTS headers (production)

### v1.3.0
- Fixed mass assignment vulnerability on PUT /api/properties
- Added query parameter injection fix with whitelist validation
- Added pagination bounds validation (limit 1-100, page >= 1)
- Added Content-Security-Policy header
- Added JWT token expiration enforcement (default: 1 hour)
- Added startup validation for JWT secret strength

### v1.2.0
- Added ObjectId format validation on all ID-based routes
- Returns 400 Bad Request on invalid ObjectId format

### v1.1.0
- Fixed JWT configuration (uses `JWT_SECRET_KEY` not `SECRET_KEY`)
- Added startup validation rejecting weak secrets
- Migrated to gunicorn for production deployments
- Added environment-based FLASK_DEBUG control

## Vulnerability Disclosure History

No known vulnerabilities have been publicly disclosed for this project. To report a security issue, please follow the guidelines in the "Reporting a Vulnerability" section above.

## References

- [OWASP Top 10 - 2021](https://owasp.org/Top10/)
- [Flask Security Documentation](https://flask.palletsprojects.com/en/2.3.x/security/)
- [MongoDB Security Practices](https://docs.mongodb.com/manual/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8949)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Last updated**: 2026-03-03
**Contact**: For security questions, email security@realestate-analyzer.local
