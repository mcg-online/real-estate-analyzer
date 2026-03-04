# Troubleshooting Guide

Common issues and solutions for developing and deploying Real Estate Analyzer.

## Table of Contents

- [Database Issues](#database-issues)
- [Authentication Issues](#authentication-issues)
- [Frontend Issues](#frontend-issues)
- [Deployment Issues](#deployment-issues)
- [Performance Issues](#performance-issues)

## Database Issues

### MongoDB Connection Errors

#### Symptom: "MongoServerSelectionError: connect ECONNREFUSED"

**Cause**: MongoDB is not running or not accessible.

**Solutions**:

1. **Check if MongoDB is running**:
   ```bash
   # macOS
   brew services list | grep mongodb

   # Linux
   systemctl status mongod

   # Docker
   docker ps | grep mongo
   ```

2. **Start MongoDB**:
   ```bash
   # macOS
   brew services start mongodb-community

   # Linux
   sudo systemctl start mongod

   # Docker
   docker run -d -p 27017:27017 --name mongodb mongo:6
   ```

3. **Verify connection**:
   ```bash
   mongosh "mongodb://localhost:27017/realestate"
   # Should show: realestate>
   ```

4. **Check DATABASE_URL in .env**:
   ```env
   DATABASE_URL=mongodb://localhost:27017/realestate
   ```

Note: The app starts gracefully without MongoDB. Check logs to confirm MongoDB availability.

#### Symptom: "Authentication failed"

**Cause**: Wrong credentials in MongoDB Atlas connection string.

**Solutions**:

1. Verify username and password in connection string
2. Check that special characters are URL-encoded
3. Ensure IP whitelist includes your machine (or 0.0.0.0/0)

**Example - Correct Format**:
```env
DATABASE_URL=mongodb+srv://username:password@cluster0.abc123.mongodb.net/realestate?retryWrites=true&w=majority
```

#### Symptom: "Indexes not created" in logs

**Cause**: App started without MongoDB, then MongoDB came online.

**Solutions**:

1. Verify `DATABASE_URL` is set before starting app
2. Check app logs for index creation confirmation:
   ```bash
   docker-compose logs backend | grep "Creating.*index"
   ```

### Database Write Failures

#### Symptom: Property saves fail silently

**Cause**: ObjectId type mismatch during serialization.

**Solutions**:

1. Ensure `from_dict()` preserves ObjectId:
   ```python
   # Correct
   obj_id = ObjectId(id_string) if isinstance(id_string, str) else id_string

   # Incorrect - causes silent failures
   obj_id = str(id_string)  # Converts ObjectId to string
   ```

2. Use `.to_dict()` before passing to analysis services:
   ```python
   # Correct
   market_dict = market.to_dict()  # Convert to dict
   result = financial_metrics.analyze(market_dict)

   # Incorrect
   result = financial_metrics.analyze(market)  # Market object not supported
   ```

3. Ensure datetime serialization uses `.isoformat()`:
   ```python
   def to_dict(self):
       return {
           'created_at': self.created_at.isoformat(),  # Correct
           'updated_at': self.updated_at.isoformat(),  # Correct
       }
   ```

## Authentication Issues

### JWT Token Errors

#### Symptom: "Missing Authorization Header" on protected routes

**Cause**: JWT token not sent with request.

**Solutions**:

1. Verify frontend includes Authorization header:
   ```javascript
   // Correct - apiClient handles this
   const response = await apiClient.get('/api/v1/properties');

   // Incorrect - raw axios without JWT
   const response = await axios.get('/api/v1/properties');
   ```

2. Check that token is stored after login:
   ```javascript
   // In apiClient.js - verify setAuthToken is called
   setAuthToken(token); // Stores in localStorage and axios headers
   ```

3. Verify login endpoint returns token:
   ```bash
   curl -X POST http://localhost:5000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"user","password":"pass"}'
   # Should return: {"access_token":"eyJ..."}
   ```

#### Symptom: "Token has expired"

**Cause**: JWT token exceeds expiration time (default 1 hour).

**Solutions**:

1. Clear localStorage and login again:
   ```javascript
   localStorage.removeItem('token');
   // User will be redirected to login page
   ```

2. Increase token expiration (optional, not recommended):
   ```env
   # Default: 3600 seconds (1 hour)
   JWT_EXPIRY_SECONDS=7200  # 2 hours
   ```

#### Symptom: "Invalid token" or signature errors

**Cause**: JWT_SECRET changed between server restarts.

**Solutions**:

1. Verify JWT_SECRET consistency:
   ```bash
   # Check .env file
   grep JWT_SECRET backend/.env

   # Verify in deployed environment
   echo $JWT_SECRET
   ```

2. Ensure JWT_SECRET is strong (32+ characters):
   ```env
   # Weak - will be rejected
   JWT_SECRET=secret

   # Good - 32+ characters
   JWT_SECRET=your_very_long_secret_key_at_least_32_characters
   ```

3. If secret changed, users must login again (old tokens become invalid)

### User Registration/Login Failures

#### Symptom: "User already exists"

**Cause**: Username is already registered.

**Solution**: Use a different username or reset the database:
```bash
mongosh realestate
> db.users.deleteMany({})
```

#### Symptom: "Invalid username format"

**Cause**: Username doesn't match validation rules.

**Solutions**:

1. Username must be 3-64 characters
2. Only alphanumeric, hyphens, underscores, and dots allowed
3. Valid: `john_doe`, `user-123`, `test.user`
4. Invalid: `ab` (too short), `john doe` (space), `user!` (special char)

#### Symptom: "Password does not meet requirements"

**Cause**: Password doesn't meet strength requirements.

**Solutions**:

Password must have:
- Minimum 8 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one digit (0-9)

Valid examples: `MyPassword1`, `Test@User99`, `SecurePass123`

## Frontend Issues

### Node.js v24 Compatibility

#### Symptom: "ajv-keywords MODULE_NOT_FOUND" during build

**Cause**: Node.js v24 incompatible with react-scripts 5.x.

**Solutions**:

1. Use react-scripts 4.0.3 (configured in package.json):
   ```json
   {
     "devDependencies": {
       "react-scripts": "4.0.3"
     }
   }
   ```

2. Set NODE_OPTIONS when building:
   ```bash
   export NODE_OPTIONS=--openssl-legacy-provider
   npm run build
   ```

3. If error persists, reinstall with legacy peer deps:
   ```bash
   rm -rf node_modules package-lock.json
   npm install --legacy-peer-deps
   ```

#### Symptom: npm install fails with peer dependency errors

**Cause**: Package version conflicts.

**Solution**: Use the `--legacy-peer-deps` flag:
```bash
npm install --legacy-peer-deps
```

This flag is already configured in the frontend setup guides.

### Frontend Build Failures

#### Symptom: "out of memory" during build

**Cause**: Node.js default memory limit too low.

**Solutions**:

```bash
# Increase Node.js memory limit
export NODE_OPTIONS=--max-old-space-size=4096
npm run build
```

#### Symptom: CSS/styling not loading

**Cause**: Tailwind CSS build not running or missing.

**Solutions**:

1. Verify Tailwind CSS configuration (should be auto-configured):
   ```bash
   # Check src/index.css includes Tailwind directives
   grep -i "tailwind" frontend/src/index.css
   ```

2. Clear build cache and rebuild:
   ```bash
   cd frontend
   rm -rf node_modules/.cache
   npm run build
   ```

### Map Not Displaying

#### Symptom: Leaflet map shows gray tiles, not map content

**Cause**: Map initialization issues or missing Leaflet library.

**Solutions**:

1. Verify Leaflet is installed:
   ```bash
   npm ls leaflet
   ```

2. Check map component useEffect hooks:
   - One hook for initialization (empty dependencies)
   - One hook for markers (depends on markers)

3. Verify mapContainer ref exists and is mounted:
   ```javascript
   // In MapView.js - should have ref on div
   <div ref={mapContainer} className="map-container" />
   ```

4. Check browser console for JavaScript errors

## Deployment Issues

### Docker Build Failures

#### Symptom: "cannot find module" during Docker build

**Cause**: Dependencies not installed properly.

**Solutions**:

1. Verify requirements.txt and package.json are in correct location
2. Check Dockerfile for correct WORKDIR
3. Rebuild from scratch:
   ```bash
   docker-compose build --no-cache backend
   docker-compose build --no-cache frontend
   ```

#### Symptom: "Permission denied" accessing volumes

**Cause**: Volume mount permissions.

**Solutions**:

1. Check Docker user permissions:
   ```bash
   ls -la backend/
   ```

2. Rebuild containers:
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

### Services Not Starting

#### Symptom: Container exits immediately

**Cause**: Application crash on startup.

**Solutions**:

1. Check logs:
   ```bash
   docker-compose logs backend
   docker-compose logs frontend
   ```

2. Verify environment variables are set:
   ```bash
   docker-compose config | grep -A 5 "environment:"
   ```

3. Test app locally before containerizing:
   ```bash
   cd backend && python app.py
   ```

### Health Check Failures

#### Symptom: "Health check failed" repeatedly

**Cause**: Backend not responding to health checks.

**Solutions**:

1. Verify health endpoints are accessible:
   ```bash
   curl http://localhost:5000/health
   curl http://localhost:5000/health/live
   curl http://localhost:5000/health/ready
   ```

2. Check if MongoDB is required for readiness:
   ```bash
   curl -v http://localhost:5000/health/ready
   # 503 if MongoDB not ready, 200 if ready
   ```

3. Increase health check timeout in docker-compose.yml:
   ```yaml
   healthcheck:
     timeout: 30s  # Increased from 10s
   ```

## Performance Issues

### Slow API Responses

#### Symptom: Requests take 5+ seconds

**Cause**: Inefficient queries or resource constraints.

**Solutions**:

1. Check MongoDB indexes:
   ```bash
   mongosh realestate
   > db.properties.getIndexes()
   > db.markets.getIndexes()
   ```

2. Enable query profiling:
   ```bash
   mongosh realestate
   > db.setProfilingLevel(1, { slowms: 100 })
   > db.system.profile.find().sort({ts:-1}).limit(5).pretty()
   ```

3. Monitor Gunicorn workers:
   ```bash
   ps aux | grep gunicorn
   # Check if all workers are running and not hanging
   ```

4. Check Redis (if enabled):
   ```bash
   redis-cli info stats
   # Look for high number of rejected connections
   ```

5. Increase Gunicorn workers (if using multi-instance):
   ```bash
   # For 8-core server: (2 * 8) + 1 = 17 workers
   gunicorn --workers=17 --threads=4 app:app
   ```

### High Memory Usage

#### Symptom: Container memory exceeds limits

**Cause**: Memory leaks or large result sets.

**Solutions**:

1. Enable pagination on property listing:
   ```bash
   # Correct - paginated
   curl "http://localhost:5000/api/v1/properties?limit=10&page=1"

   # Incorrect - fetches all properties into memory
   curl "http://localhost:5000/api/v1/properties?limit=10000"
   ```

2. Check for frontend memory leaks:
   ```javascript
   // Cleanup useEffect hooks properly
   useEffect(() => {
     const handler = () => { /* ... */ };
     window.addEventListener('resize', handler);

     return () => {
       window.removeEventListener('resize', handler);  // Cleanup
     };
   }, []);
   ```

3. Monitor Leaflet map memory:
   - Ensure map instance is removed in cleanup
   - Check for duplicate map initializations

4. Set memory limits in docker-compose.yml:
   ```yaml
   backend:
     mem_limit: 2g
   frontend:
     mem_limit: 1g
   ```

### Rate Limiting Too Strict

#### Symptom: Getting 429 "Too Many Requests" errors

**Cause**: Default rate limits (200/day, 50/hour) too restrictive.

**Solutions**:

1. Check current rate limit in logs:
   ```bash
   docker-compose logs backend | grep "rate limit"
   ```

2. Adjust limits in app.py:
   ```python
   limiter = Limiter(
       get_remote_address,
       app=app,
       storage_uri=redis_url,
       default_limits=[
           "500 per day",   # Increased from 200
           "100 per hour",  # Increased from 50
       ],
   )
   ```

3. Or disable rate limiting in development:
   ```bash
   # Don't do this in production
   FLASK_ENV=development  # Skips rate limiting
   ```

### CORS Issues

#### Symptom: "Access-Control-Allow-Origin" error in browser

**Cause**: Frontend origin not allowed by backend CORS policy.

**Solutions**:

1. Check CORS_ORIGINS environment variable:
   ```bash
   echo $CORS_ORIGINS
   # Should match frontend origin: http://localhost:3000
   ```

2. Update CORS_ORIGINS if deploying to different domain:
   ```env
   CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

3. Restart backend after changing CORS_ORIGINS:
   ```bash
   docker-compose restart backend
   ```

4. For development with multiple hosts:
   ```env
   CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000
   ```

## Getting Help

If you can't find a solution here:

1. Check [README.md](README.md) for overview
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. Look at [API.md](API.md) for endpoint documentation
4. Check application logs for error details
5. File an issue on GitHub with:
   - Error message (full stack trace if available)
   - Steps to reproduce
   - Your environment (OS, Python/Node versions, MongoDB version)
   - Configuration (obfuscate sensitive values)

## References

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment configuration
- [SECURITY.md](SECURITY.md) - Security setup and best practices
- [API.md](API.md) - API reference
