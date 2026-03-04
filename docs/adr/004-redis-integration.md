# ADR 004: Redis Integration

**Status**: Accepted (v1.5.0+)

**Date**: 2024-09-01

**Deciders**: Development Team

## Context

Real Estate Analyzer needs:
- **Caching**: Response caching for frequently-accessed data (markets, top performers)
- **Rate Limiting**: Prevent API abuse (200/day, 50/hour per IP)
- **JWT Blocklist**: Token revocation for logout (prevent reuse of revoked tokens)
- **Distributed State**: Support horizontal scaling across multiple backend instances

Previous implementation (v1.4.0 and earlier):
- **Rate Limiting**: In-memory (Limiter storage) - works only on single instance
- **JWT Blocklist**: In-memory (Python set) - lost on server restart
- **Caching**: SimpleCache (in-memory) - not shared across instances

Limitations:
- Horizontally scaling (multiple backend instances) causes issues:
  - Rate limits reset on different instances
  - Logout on instance A doesn't affect instance B
  - Cache not shared, leading to redundant database queries
- Server restarts lose all revoked tokens and rate limit data

## Decision

We chose **Redis** for caching, rate limiting, and JWT blocklist with **graceful fallback to in-memory** when Redis is unavailable.

### 1. Redis for Caching

**With Redis**:

```python
# app.py
if redis_url:
    cache_config = {
        'CACHE_TYPE': 'RedisCache',
        'CACHE_REDIS_URL': redis_url
    }
    logger.info("Cache using Redis at %s", redis_url)
else:
    cache_config = {
        'CACHE_TYPE': 'SimpleCache'
    }
    logger.info("Cache using SimpleCache (no REDIS_URL configured)")

cache = Cache(app, config=cache_config)

# Mark endpoints for caching
@app.route('/api/v1/markets/top')
@cache.cached(timeout=3600)  # Cache for 1 hour
def get_top_markets():
    # Expensive aggregation query
    top_markets = db.markets.aggregate(pipeline)
    return jsonify(top_markets)
```

**Benefits**:
- **Reduced Database Load**: Expensive queries cached
- **Faster Responses**: Cache hits return in milliseconds
- **Shared Across Instances**: Multiple backend instances share same cache
- **Configurable TTL**: Different endpoints have different cache durations
- **Atomic Operations**: Redis guarantees consistency

**Cache Candidates** (high-value, low-change):
- Top markets by ROI/cap rate (expensive aggregation, changes daily)
- Market analysis summaries (state-level statistics, changes weekly)
- Property listings with filters (popular queries, refreshed hourly)

### 2. Redis for Rate Limiting

**With Redis Backend** (v1.5.0+):

```python
if redis_url:
    limiter = Limiter(
        get_remote_address,
        app=app,
        storage_uri=redis_url,
        default_limits=["200 per day", "50 per hour"],
    )
    logger.info("Rate limiter using Redis storage")
else:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
    )
    logger.info("Rate limiter using in-memory storage")

# Apply to all routes or specific endpoints
@app.route('/api/v1/properties')
@limiter.limit("10 per minute")
def get_properties():
    ...
```

**Benefits**:
- **Distributed Tracking**: Rate limits enforced across all instances
- **IP-Based**: Track requests per IP address
- **Customizable**: Different limits for different endpoints
- **Automatic Reset**: Time-based window resets (daily, hourly, per minute)
- **Non-Blocking**: Limits checked in Redis, not in-process

**Default Limits** (configurable):
- 200 requests per day (per IP)
- 50 requests per hour (per IP)

**Example - Rate Limited Response**:
```bash
# First request succeeds
curl -i http://localhost:5000/api/v1/properties
# HTTP/1.1 200 OK
# X-RateLimit-Limit: 50
# X-RateLimit-Remaining: 49
# X-RateLimit-Reset: 1726759234

# After limit exceeded
curl -i http://localhost:5000/api/v1/properties
# HTTP/1.1 429 Too Many Requests
# Retry-After: 3599
```

### 3. Redis for JWT Token Blocklist

**Token Revocation** (logout):

```python
# app.py
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return is_token_revoked(jwt_payload['jti'])

# routes/users.py
@app.route('/api/v1/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']  # Unique token ID
    add_token_to_blocklist(jti)  # Add to blocklist
    return jsonify(msg="Successfully logged out"), 200

# utils/auth.py
def add_token_to_blocklist(jti):
    if redis_client:
        # Set key=jti, expire after token lifetime
        expires = app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)
        redis_client.setex(f'token_blocklist:{jti}', expires, 'revoked')
    else:
        # Fallback: in-memory set
        blocklist.add(jti)

def is_token_revoked(jti):
    if redis_client:
        return redis_client.exists(f'token_blocklist:{jti}')
    else:
        return jti in blocklist
```

**Benefits**:
- **Immediate Revocation**: User immediately logged out on all instances
- **Automatic Cleanup**: Keys expire after token lifetime
- **Distributed**: Logout on instance A affects instance B
- **Simple Implementation**: One line to add to blocklist

**Alternative Without Redis** (v1.0-1.4):
```python
# In-memory blocklist - only survives on same instance
blocklist = set()

def logout():
    blocklist.add(jti)  # Lost on server restart
```

Problems:
- Logout not immediate across instances
- Token still valid if it reaches different instance
- Blocklist lost on server restart

### 4. Graceful Fallback Architecture

The application works without Redis (development mode):

```python
# Check if Redis available
redis_url = os.getenv('REDIS_URL')

if redis_url:
    # Production: Use Redis for all three features
    cache = Cache(app, config={'CACHE_TYPE': 'RedisCache', 'CACHE_REDIS_URL': redis_url})
    limiter = Limiter(get_remote_address, app=app, storage_uri=redis_url)
    jwt_blocklist = RedisBlocklist(redis_client)
else:
    # Development: Use in-memory fallbacks
    cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})
    limiter = Limiter(get_remote_address, app=app)
    jwt_blocklist = InMemoryBlocklist()
```

**Development Mode** (no Redis):
- ✓ Caching works (in-memory)
- ✓ Rate limiting works (per-instance)
- ✓ JWT blocklist works (revoked tokens blocked)
- ✗ Caching not shared across instances
- ✗ Rate limits reset per instance
- ✗ Logout on instance A doesn't affect instance B

**Production Mode** (with Redis):
- ✓ All features work fully
- ✓ Shared cache across instances
- ✓ Distributed rate limiting
- ✓ Distributed JWT blocklist

### 5. Redis Configuration

**Environment Variable**:
```env
REDIS_URL=redis://[username]:[password]@host:port/[database]

# Examples:
REDIS_URL=redis://localhost:6379/0          # Local development
REDIS_URL=redis://user:pass@redis.example.com:6379/0  # Authentication
REDIS_URL=rediss://host:port/0              # TLS encrypted
```

**Docker Compose**:
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 3

backend:
  environment:
    - REDIS_URL=redis://redis:6379/0
  depends_on:
    redis:
      condition: service_healthy
```

**Production Setup** (Managed Redis):
- AWS ElastiCache
- Azure Cache for Redis
- Google Cloud Memorystore
- Heroku Redis
- Self-managed Redis with replication

### 6. Memory Management

**Redis Memory Limits**:
```bash
# Set max memory for Redis
redis-cli config set maxmemory 2gb
redis-cli config set maxmemory-policy allkeys-lru
```

**Eviction Policies**:
- `noeviction`: Reject writes if memory full
- `allkeys-lru`: Remove oldest keys when full
- `volatile-lru`: Remove expiring keys oldest first
- `volatile-ttl`: Remove keys with shortest TTL

**Monitoring**:
```bash
# Check Redis memory usage
redis-cli info memory

# Sample output:
# used_memory: 1048576 bytes
# maxmemory: 2147483648 bytes
# evicted_keys: 0
```

### 7. Data Consistency & Atomicity

**JWT Blocklist Expiration** (automatic cleanup):
```python
# When token is revoked, set TTL = token lifetime
expires_in = app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)  # 1 hour
redis_client.setex(f'blocklist:{jti}', expires_in, 'revoked')

# After 1 hour, key automatically expires
# No manual cleanup needed
```

**Cache Invalidation**:
```python
# Invalidate cache when data changes
@app.route('/api/v1/properties', methods=['POST'])
def create_property():
    property = Property.create(request.get_json())

    # Property data changed, invalidate related caches
    cache.delete('top_markets')
    cache.delete('market_analysis')

    return jsonify(property.to_dict()), 201
```

## Consequences

### Positive

1. **Scalability**: Distributed caching and rate limiting work across instances
2. **Performance**: Frequently-accessed data cached in-memory (Redis)
3. **Availability**: Graceful degradation without Redis (in-memory fallback)
4. **Security**: Logout works immediately across all instances
5. **Flexibility**: Easy to enable/disable via environment variable
6. **Standards**: Redis is industry-standard for caching

### Negative

1. **Additional Dependency**: Requires Redis service (can be eliminated with fallback)
2. **Operational Complexity**: Redis monitoring, backups, failover
3. **Memory Overhead**: Another service to manage and secure
4. **Latency**: Network round-trip to Redis (usually sub-millisecond)
5. **Data Loss Risk**: Redis data lost if not persisted

### Mitigations

1. **Fallback Mode**: Works without Redis (not required)
2. **Managed Services**: Use managed Redis (avoid operations)
3. **Monitoring**: Set memory limits and eviction policies
4. **Persistence**: Configure RDB snapshots or AOF for production

## Alternative Approaches Considered

### 1. Memcached Instead of Redis
- Simpler, lighter-weight
- No blocklist support
- No rate limiting support
- Would need separate solution for JWT blocklist

### 2. Distributed Cache in Database (MongoDB)
```python
# Use MongoDB as cache store
cache_collection = db.cache
cache_collection.insert_one({
    '_id': 'top_markets',
    'data': [...],
    'expires_at': datetime.now() + timedelta(hours=1)
})
```

- Pros: Single database, simpler deployment
- Cons: Slower than Redis, requires TTL index, more complex cleanup

### 3. No Caching
- Simpler deployment
- Slower performance
- Higher database load
- Can't scale to many users

We chose Redis because:
- **All-in-one**: Caching, rate limiting, blocklist
- **Fast**: Sub-millisecond latency
- **Scalable**: Distributed state across instances
- **Optional**: Works without it (graceful fallback)

## References

- [Redis Documentation](https://redis.io/documentation)
- [Flask-Caching with Redis](https://flask-caching.readthedocs.io/)
- [Flask-Limiter with Redis](https://flask-limiter.readthedocs.io/)
- [Redis Best Practices](https://redis.io/topics/protocol)

## Related Decisions

- **ADR 001**: MongoDB (primary database, Redis supplements)
- **ADR 002**: JWT Authentication (Redis stores blocklist)
- **ADR 003**: API Versioning (cached endpoints available across versions)
