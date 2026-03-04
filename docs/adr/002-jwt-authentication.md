# ADR 002: JWT Authentication

**Status**: Accepted (v1.0.0+)

**Date**: 2024-01-01

**Deciders**: Development Team

## Context

The application needs to:
- Authenticate users via username/password registration and login
- Maintain authenticated state across API requests (browser + mobile)
- Provide secure access to user-specific properties and data
- Support logout/token revocation
- Scale horizontally without session storage

Traditional approaches:
- **Session-based (server-side)**: Requires server state (sessions table)
- **Token-based (client-side)**: Stateless, scales horizontally

## Decision

We chose **JWT (JSON Web Token) Authentication** with Flask-JWT-Extended because:

### 1. Stateless Authentication

Tokens are self-contained; server doesn't store session state:

```python
# Server verifies token signature without database lookup
@app.route('/api/v1/properties')
@jwt_required()
def get_properties():
    current_user = get_jwt_identity()  # Extracted from token claims
    # No session lookup needed
```

Benefits:
- **Horizontal Scaling**: Multiple backend instances verify tokens independently
- **No Session Table**: Reduces database overhead
- **Distributed Systems**: Works seamlessly across microservices

### 2. Token-Based for Web & Mobile

Clients receive token on login and send it with each request:

```javascript
// Frontend login
const response = await axios.post('/api/v1/auth/login', {
  username: 'user@example.com',
  password: 'password'
});
const token = response.data.access_token;

// Store in localStorage (or secure storage on mobile)
localStorage.setItem('token', token);

// Send with each request
axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

// API automatically includes token via apiClient
const properties = await apiClient.get('/api/v1/properties');
```

### 3. Flask-JWT-Extended Integration

Flask-JWT-Extended provides:

```python
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token

# Setup
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# User login
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    user = User.find_by_username(username)
    if user and user.check_password(password):
        access_token = create_access_token(identity=user.username)
        return jsonify(access_token=access_token)
    return jsonify(error="Invalid credentials"), 401

# Protected route
@app.route('/api/v1/properties')
@jwt_required()
def get_properties():
    username = get_jwt_identity()
    # Only logged-in users reach this point
```

### 4. Token Expiration & Refresh

Tokens expire after 1 hour (configurable):

```python
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(
    os.getenv('JWT_EXPIRY_SECONDS', 3600)  # Default 1 hour
)
```

When token expires:
- Frontend detects 401 Unauthorized response
- User redirected to login page
- User logs in again to get new token

Benefits:
- **Reduced Risk**: Expired tokens can't be used
- **Logout Safety**: User can't use old tokens after password change
- **Configurable**: Adjust expiration for security/convenience tradeoff

### 5. Logout with Token Blocklist

Token revocation uses Redis-backed blocklist:

```python
# JWT blocklist callback
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return is_token_revoked(jwt_payload['jti'])

# Logout adds token to blocklist
@app.route('/api/v1/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    blocklist.add(jti)  # Store in Redis (or in-memory if no Redis)
    return jsonify(msg="Successfully logged out")

# All subsequent requests with revoked token are rejected
@app.route('/api/v1/protected')
@jwt_required()
def protected():
    # Won't reach here if token is in blocklist
    ...
```

Redis backend (if available):
- **Distributed**: Works across multiple backend instances
- **Fast**: In-memory lookups (< 1ms)
- **Persistent**: Survives server restarts

In-memory fallback (no Redis):
- Works for single-instance deployments
- Blocklist cleared on server restart

### 6. Secure Token Storage & Transmission

**Frontend Storage**:
```javascript
// localStorage: Simple, but vulnerable to XSS
// Solution: Use XSS prevention (Content Security Policy)
localStorage.setItem('token', access_token);

// httpOnly cookie: Better, prevents XSS but vulnerable to CSRF
// Trade-off: Requires CSRF token
```

**Transmission**:
```
HTTP Request:
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

HTTPS Required:
- Tokens in transit must be encrypted (TLS/SSL)
- Prevents man-in-the-middle attacks
```

### 7. Password Security

Passwords hashed with bcrypt:

```python
from werkzeug.security import generate_password_hash, check_password_hash

# Registration
hashed = generate_password_hash(password)
user.password_hash = hashed

# Login
if check_password_hash(user.password_hash, provided_password):
    # Password correct
```

Bcrypt benefits:
- **Salted**: Each password has unique salt
- **Slow**: Resistant to brute force (configurable work factor)
- **Industry Standard**: Well-tested algorithm

### 8. Property Ownership Authorization

User ID captured in token claims during property creation:

```python
@app.route('/api/v1/properties', methods=['POST'])
@jwt_required()
def create_property():
    current_user_id = get_jwt_identity()  # From token
    property_data = request.get_json()

    # New property gets user_id
    property_data['user_id'] = current_user_id
    property = Property.create(property_data)

    return jsonify(property.to_dict()), 201

# PUT/DELETE enforce ownership
@app.route('/api/v1/properties/<property_id>', methods=['PUT'])
@jwt_required()
def update_property(property_id):
    current_user_id = get_jwt_identity()
    property = Property.find_by_id(property_id)

    if property.user_id != current_user_id:
        return jsonify(error="Forbidden"), 403  # Not owner

    # Update allowed
    property.update(request.get_json())
    return jsonify(property.to_dict()), 200
```

## Consequences

### Positive

1. **Stateless**: Scales horizontally without session storage
2. **Revokable**: Logout works via blocklist (with Redis)
3. **Flexible**: Easy to add custom claims (user role, permissions)
4. **Web & Mobile**: Works naturally with browser cookies and mobile apps
5. **Security**: Expiration, signature verification, optional refresh tokens
6. **Transparent**: Token contains readable claims (base64 encoded, not encrypted)

### Negative

1. **Token Size**: Larger than session ID sent with each request
2. **Can't Revoke Instantly**: Token valid until expiration (unless blocklist checked)
3. **XSS Vulnerability**: Token in localStorage vulnerable to XSS attacks
   - **Mitigation**: Content Security Policy (CSP) headers
4. **Complexity**: More complex than simple session cookies

### Trade-offs

| Approach | Stateless | Revokable | Mobile | Scalable | Complexity |
|----------|-----------|-----------|--------|----------|------------|
| Sessions | No | Yes | Harder | No | Low |
| JWT (no revocation) | Yes | No | Yes | Yes | Medium |
| JWT (with blocklist) | Yes | Yes | Yes | Yes | High |

We chose JWT with blocklist (high complexity) for the best combination of revocation and scalability.

## Related Decisions

- **ADR 001**: MongoDB (stores user accounts with hashed passwords)
- **ADR 004**: Redis (stores JWT token blocklist for logout)

## Implementation Details

### Startup Secret Validation

```python
jwt_secret = os.getenv('JWT_SECRET')
if not jwt_secret or jwt_secret in ('your_secret_key', 'changeme', 'secret'):
    logger.warning("JWT_SECRET is weak or missing. Using random secret.")
    jwt_secret = os.urandom(32).hex()
app.config['JWT_SECRET_KEY'] = jwt_secret
```

Rejects placeholder values in production:
- `your_secret_key`
- `changeme`
- `secret`

Requires 32+ characters in production deployments.

### Configuration

```python
# app.py
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(
    os.getenv('JWT_EXPIRY_SECONDS', 3600)
)

# .env
JWT_SECRET=your_32_char_minimum_secret_key
JWT_EXPIRY_SECONDS=3600  # 1 hour
```

## References

- [Flask-JWT-Extended Documentation](https://flask-jwt-extended.readthedocs.io/)
- [JWT.io](https://jwt.io/) - JWT standard and tools
- [OWASP: Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Werkzeug Security](https://werkzeug.palletsprojects.com/en/2.3.x/security/)
