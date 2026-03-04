# Deployment Guide

This guide covers deploying Real Estate Analyzer in production environments. See [SECURITY.md](SECURITY.md) for security best practices.

## Quick Start: Docker Compose

The fastest way to deploy locally or in test environments:

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

This launches:
- **Backend** (Flask): http://localhost:5000
- **Frontend** (React): http://localhost:3000
- **MongoDB**: localhost:27017
- **Redis**: localhost:6379

## Production Deployment

### Environment Variables Reference

Configure these variables for your deployment:

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `DATABASE_URL` | MongoDB connection URI | `mongodb://localhost:27017/realestate` | Yes |
| `JWT_SECRET` | Secret key for JWT tokens (min 32 chars) | None | Yes |
| `JWT_EXPIRY_SECONDS` | Token expiration time in seconds | `3600` | No |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` | No |
| `REDIS_URL` | Redis connection URI for caching/limiter | None | No |
| `FLASK_ENV` | Flask environment (development/production) | `production` | No |
| `FLASK_DEBUG` | Enable Flask debug mode | `false` | No |

### Setting Environment Variables

#### Docker Environment File

Create a `.env` file in the project root:

```env
DATABASE_URL=mongodb+srv://user:password@cluster.mongodb.net/realestate?retryWrites=true&w=majority
JWT_SECRET=your_very_long_secret_key_at_least_32_characters
JWT_EXPIRY_SECONDS=3600
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
REDIS_URL=redis://user:password@redis-host:6379/0
FLASK_ENV=production
FLASK_DEBUG=false
```

Then load with:

```bash
docker-compose up -d
```

#### Kubernetes/Container Orchestration

Set environment variables via your orchestration platform:

```yaml
# Kubernetes example
apiVersion: v1
kind: ConfigMap
metadata:
  name: realestate-config
data:
  DATABASE_URL: "mongodb+srv://user:password@cluster.mongodb.net/realestate"
  JWT_SECRET: "your_very_long_secret_key_at_least_32_characters"
  CORS_ORIGINS: "https://yourdomain.com"
  FLASK_ENV: "production"
---
apiVersion: v1
kind: Secret
metadata:
  name: realestate-secrets
type: Opaque
stringData:
  JWT_SECRET: "your_very_long_secret_key_at_least_32_characters"
  DATABASE_URL: "mongodb+srv://user:password@cluster.mongodb.net/realestate"
```

#### Traditional Server

Export environment variables before starting:

```bash
export DATABASE_URL="mongodb://mongo-server:27017/realestate"
export JWT_SECRET="your_very_long_secret_key_at_least_32_characters"
export CORS_ORIGINS="https://yourdomain.com"
export FLASK_ENV="production"

python app.py  # or run with gunicorn
```

## Docker Compose Services

### Backend Service

The Flask application runs behind Gunicorn WSGI server.

**Configuration** (docker-compose.yml):

```yaml
backend:
  build: ./backend
  ports:
    - "5000:5000"
  environment:
    - DATABASE_URL=mongodb://mongo:27017/realestate
    - JWT_SECRET=${JWT_SECRET}
    - REDIS_URL=redis://redis:6379/0
  depends_on:
    mongo:
      condition: service_healthy
    redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Gunicorn Configuration** (in Dockerfile):

```dockerfile
# Production server configuration
CMD ["gunicorn", \
     "--workers=4", \
     "--threads=4", \
     "--worker-class=gthread", \
     "--bind=0.0.0.0:5000", \
     "--access-logfile=-", \
     "--error-logfile=-", \
     "app:app"]
```

**Scaling Workers**:
- `--workers`: Number of worker processes (default: 4)
  - Formula: `(2 × CPU_CORES) + 1`
- `--threads`: Threads per worker (default: 4)
- `--worker-class=gthread`: Threaded worker for I/O-bound tasks

Example for 8-core system:

```bash
gunicorn --workers=17 --threads=4 --worker-class=gthread app:app
```

### MongoDB Service

Provides the primary database for property, user, and market data.

**Configuration**:

```yaml
mongo:
  image: mongo:6
  ports:
    - "27017:27017"
  volumes:
    - mongo_data:/data/db
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Production Notes**:
- Use managed MongoDB (MongoDB Atlas, AWS DocumentDB, Azure Cosmos)
- Enable authentication with username/password
- Configure backups and point-in-time recovery
- Use connection pooling with `maxPoolSize=50`
- Enable encryption in transit (TLS/SSL)

### Redis Service

Provides caching, rate limiting, and JWT token blocklist.

**Configuration**:

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
```

**Production Notes**:
- Use managed Redis (AWS ElastiCache, Azure Cache, Heroku Redis)
- Enable authentication with requirepass
- Configure persistence (RDB snapshots or AOF)
- Set appropriate memory limits and eviction policy
- Enable encryption in transit

### Frontend Service

React SPA served during development via Node development server.

**Production Setup**:

For production, build the React app and serve with a static file server:

```bash
cd frontend
npm install --legacy-peer-deps
NODE_OPTIONS=--openssl-legacy-provider npm run build
```

Serve the `build/` directory with nginx, Apache, or a CDN.

## Production Checklist

Before deploying to production, verify:

### Security

- [ ] **JWT_SECRET**: Set to strong value (32+ characters), not placeholder
- [ ] **CORS_ORIGINS**: Restricted to your domain(s), not `*`
- [ ] **FLASK_ENV**: Set to `production`
- [ ] **HTTPS**: All traffic encrypted (TLS 1.2+)
- [ ] **Database Authentication**: MongoDB requires username/password
- [ ] **Redis Authentication**: Redis requirepass configured if exposed to network
- [ ] **Rate Limiting**: Default limits (200/day, 50/hour) appropriate for your usage
- [ ] **Input Validation**: All inputs validated (enabled by default)
- [ ] **Security Headers**: CSP, HSTS, X-Frame-Options enabled (enabled by default)
- [ ] **Password Hashing**: Bcrypt with proper salt (enabled by default)

See [SECURITY.md](SECURITY.md) for complete security feature details.

### Performance & Reliability

- [ ] **Health Checks**: `/health`, `/health/live`, `/health/ready` responding
- [ ] **Database Indexes**: Created on startup (verified in logs)
- [ ] **Connection Pooling**: MongoDB maxPoolSize=50 configured
- [ ] **Caching**: Redis enabled for performance (optional)
- [ ] **Rate Limiter**: Redis backend for distributed rate limiting (optional)
- [ ] **Logging**: Structured JSON logs with request_id correlation
- [ ] **Monitoring**: Application metrics and error tracking configured
- [ ] **Backup Strategy**: Database backups scheduled daily minimum
- [ ] **Load Balancing**: Traffic distributed across multiple backend instances

### Data Integrity

- [ ] **Backups**: Automated daily backups with retention policy
- [ ] **Point-in-Time Recovery**: Available for disaster recovery
- [ ] **Database Validation**: Test restore procedures
- [ ] **Migration Scripts**: Version-controlled and tested

### Deployment Process

- [ ] **Version Tagging**: Release version tagged in git
- [ ] **Changelog Updated**: Changes documented in CHANGELOG.md
- [ ] **Testing**: All tests passing (`pytest tests/ -v`)
- [ ] **Code Review**: Changes reviewed and approved
- [ ] **Staging Test**: Deployed to staging environment first
- [ ] **Smoke Tests**: Basic functionality verified in staging
- [ ] **Rollback Plan**: Previous version ready to deploy if issues arise

## Monitoring & Logging

### Health Check Endpoints

Three health check endpoints for monitoring:

```bash
# Basic health check (always returns 200)
curl http://localhost:5000/health

# Liveness probe (pod alive check for K8s)
curl http://localhost:5000/health/live

# Readiness probe (ready to serve traffic)
curl http://localhost:5000/health/ready
```

### Structured Logging

The application logs in structured JSON format:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "request_id": "a1b2c3d4",
  "message": "GET /api/v1/properties completed",
  "method": "GET",
  "path": "/api/v1/properties",
  "status": 200,
  "duration_ms": 145,
  "user_id": "user123"
}
```

**Log Aggregation**: Send logs to:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- Datadog
- CloudWatch
- Stackdriver

### Request Correlation

All API requests include a `request_id` header for tracing:

```
X-Request-ID: a1b2c3d4
```

Use this to correlate logs across services.

## Scaling Strategies

### Horizontal Scaling (Multiple Backend Instances)

Deploy multiple Flask/Gunicorn instances behind a load balancer:

```
Load Balancer (nginx, HAProxy, AWS ALB)
  ├── Backend Instance 1
  ├── Backend Instance 2
  ├── Backend Instance 3
  └── Backend Instance 4
  ↓
Shared MongoDB
Shared Redis
```

**Configuration**:
- Share `DATABASE_URL` and `REDIS_URL` across instances
- Rate limiter uses Redis for distributed tracking
- JWT blocklist uses Redis for distributed revocation
- Cache (if enabled) uses Redis for distributed storage

**Load Balancer Config** (nginx example):

```nginx
upstream backend {
    server backend1:5000;
    server backend2:5000;
    server backend3:5000;
    server backend4:5000;
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Request-ID $request_id;
    }
}
```

### Vertical Scaling (Larger Instance)

Increase Gunicorn worker processes for larger servers:

```bash
# 16-core server
gunicorn --workers=33 --threads=4 --worker-class=gthread app:app
```

### Database Scaling

- **MongoDB Atlas**: Sharded cluster for horizontal scaling
- **Read Replicas**: Secondary nodes for read-heavy workloads
- **Connection Pooling**: Reuse connections across instances

### Caching Optimization

- Enable Redis caching (REDIS_URL configuration)
- Cache market analysis and top markets queries
- Set appropriate TTLs for data freshness

## Cloud Deployment Examples

### AWS Elastic Container Service (ECS)

```bash
# Build and push image
docker build -t myrepo/realestate-backend:1.5.0 ./backend
docker push myrepo/realestate-backend:1.5.0

# Deploy via CloudFormation/Terraform with:
# - ALB for load balancing
# - RDS for MongoDB (DocumentDB) or MongoDB Atlas
# - ElastiCache for Redis
# - CloudWatch for logs
# - Auto Scaling Group for backend instances
```

### Google Cloud Run

```bash
# Build and deploy
gcloud run deploy realestate-backend \
  --source=./backend \
  --set-env-vars DATABASE_URL=$MONGODB_URI,JWT_SECRET=$JWT_SECRET
```

### Heroku

```bash
# Deploy via Git push
git push heroku main

# Set environment variables
heroku config:set JWT_SECRET=your_secret
heroku config:set DATABASE_URL=mongodb+srv://...
heroku config:set REDIS_URL=redis://...
```

### Kubernetes

```bash
# Create deployments
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/configmap.yaml

# Scale replicas
kubectl scale deployment realestate-backend --replicas=5

# Monitor
kubectl logs deployment/realestate-backend
```

## Database Setup

### MongoDB Atlas (Cloud)

1. Create cluster at https://www.mongodb.com/cloud/atlas
2. Create database user with strong password
3. Add IP whitelist (or allow 0.0.0.0/0 for development)
4. Get connection string: `mongodb+srv://user:password@cluster.mongodb.net/realestate`
5. Set as `DATABASE_URL` environment variable

### Local MongoDB

```bash
# macOS with Homebrew
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community

# Linux
sudo apt-get install mongodb
sudo systemctl start mongod

# Docker
docker run -d -p 27017:27017 --name mongodb mongo:6
```

### Create Indexes

Indexes are automatically created on startup. Verify:

```bash
mongosh realestate
> db.properties.getIndexes()
> db.markets.getIndexes()
```

## Troubleshooting Deployments

### Services Not Starting

```bash
# Check logs
docker-compose logs backend
docker-compose logs mongo
docker-compose logs redis

# Verify health
curl http://localhost:5000/health/ready
```

### Connection Failures

```bash
# Check MongoDB connection
mongosh --uri "mongodb://mongo:27017/realestate"

# Check Redis connection
redis-cli -u redis://redis:6379/0 ping

# Verify network
docker-compose exec backend curl http://mongo:27017
```

### Performance Issues

```bash
# Monitor MongoDB slow queries
mongosh realestate
> db.setProfilingLevel(1, { slowms: 100 })
> db.system.profile.find().pretty()

# Check Redis memory
redis-cli info memory

# Monitor Gunicorn
ps aux | grep gunicorn
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more help.

## References

- [SECURITY.md](SECURITY.md) - Security configuration and best practices
- [README.md](README.md) - Project overview and features
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [API.md](API.md) - API reference and examples
