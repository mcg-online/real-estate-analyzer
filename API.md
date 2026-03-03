# Real Estate Analyzer API Reference

Complete documentation for the Real Estate Analyzer API. This API provides comprehensive tools for analyzing real estate properties, accessing market data, and calculating investment metrics.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Health Checks](#health-checks)
- [Properties](#properties)
- [Analysis](#analysis)
- [Markets](#markets)
- [Authentication Endpoints](#authentication-endpoints)
- [Error Handling](#error-handling)

## Getting Started

### Base URL

- **Development**: `http://localhost:5000`
- **Production**: Set via `REACT_APP_API_URL` environment variable

### Example Request

```bash
curl -X GET http://localhost:5000/api/properties \
  -H "Authorization: Bearer your_access_token"
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. All endpoints except health checks and authentication endpoints require a valid JWT token.

### Including JWT in Requests

Include the JWT token in the `Authorization` header with the `Bearer` scheme:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Format

JWT tokens are issued by the login endpoint and are required for all protected endpoints. Tokens are signed using the `JWT_SECRET` environment variable.

## Rate Limiting

API requests are rate limited per IP address to ensure fair usage and service stability.

**Rate Limits:**
- **Daily limit**: 200 requests per day
- **Hourly limit**: 50 requests per hour

When rate limit is exceeded, the API returns a 429 (Too Many Requests) status code.

## Health Checks

Health check endpoints are available for monitoring and load balancer integration. These endpoints do not require authentication.

### GET /health

Shallow health check for load balancers. Useful for basic liveness probes.

**Response (200 OK):**
```json
{
  "status": "ok"
}
```

---

### GET /health/ready

Deep readiness check that verifies critical dependencies. This checks MongoDB connectivity and overall service readiness.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "checks": {
    "mongodb": {
      "status": "ok"
    },
    "scheduler": {
      "status": "ok"
    }
  },
  "version": "1.2.0"
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "degraded",
  "checks": {
    "mongodb": {
      "status": "error",
      "detail": "Unable to connect to MongoDB: connection timeout"
    },
    "scheduler": {
      "status": "warning",
      "detail": "No heartbeat for 720s"
    }
  },
  "version": "1.2.0"
}
```

---

### GET /health/live

Liveness probe to check if the process is responsive. Used by Kubernetes and other orchestration platforms.

**Response (200 OK):**
```json
{
  "status": "alive",
  "pid": 12345
}
```

---

## Properties

Property endpoints allow you to list, create, retrieve, update, and delete real estate properties in the system.

### GET /api/properties

List properties with support for filtering, pagination, and sorting.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `minPrice` | integer | - | Minimum property price (inclusive) |
| `maxPrice` | integer | - | Maximum property price (inclusive) |
| `minBedrooms` | float | - | Minimum number of bedrooms |
| `minBathrooms` | float | - | Minimum number of bathrooms |
| `propertyType` | string | - | Filter by property type (e.g., "single_family", "condo", "townhouse") |
| `city` | string | - | Filter by city name |
| `state` | string | - | Filter by state abbreviation (e.g., "CA", "NY") |
| `zipCode` | string | - | Filter by zip code |
| `minScore` | float | - | Minimum investment opportunity score (0-100) |
| `limit` | integer | 50 | Number of results per page (max 100) |
| `page` | integer | 1 | Page number for pagination |
| `sortBy` | string | "price" | Field to sort by (e.g., "price", "bedrooms", "score") |
| `sortOrder` | string | "asc" | Sort direction: "asc" for ascending, "desc" for descending |

**Example Request:**

```bash
curl -X GET "http://localhost:5000/api/properties?minPrice=200000&maxPrice=500000&state=CA&limit=20&page=1" \
  -H "Authorization: Bearer your_access_token"
```

**Response (200 OK):**
```json
{
  "data": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "address": "123 Oak Street",
      "city": "San Francisco",
      "state": "CA",
      "zip_code": "94102",
      "price": 350000,
      "bedrooms": 3,
      "bathrooms": 2,
      "sqft": 1850,
      "year_built": 1995,
      "property_type": "single_family",
      "score": 78.5,
      "created_at": "2024-01-15T10:30:00+00:00",
      "updated_at": "2024-01-20T14:22:00+00:00"
    }
  ],
  "total": 142,
  "page": 1,
  "limit": 50,
  "pages": 3
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": {
    "code": "INVALID_ID",
    "message": "Invalid property ID format"
  }
}
```

---

### POST /api/properties

Create a new property in the system.

**Request Body (application/json):**

```json
{
  "address": "789 Pine Street",
  "city": "Berkeley",
  "state": "CA",
  "zip_code": "94704",
  "price": 550000,
  "bedrooms": 3,
  "bathrooms": 2.5,
  "sqft": 1950,
  "year_built": 1998,
  "property_type": "single_family",
  "lot_size": 5500,
  "listing_url": "https://example.com/property/789",
  "source": "mls",
  "latitude": 37.8716,
  "longitude": -122.2727,
  "description": "Charming Victorian-style home with updated utilities",
  "images": [
    "https://example.com/images/789-1.jpg"
  ]
}
```

**Required Fields:**
- `address`: string - Full property address
- `price`: number - Property price in dollars
- `bedrooms`: number - Number of bedrooms
- `bathrooms`: number - Number of bathrooms
- `sqft`: number - Square footage of living space
- `year_built`: integer - Year property was constructed
- `property_type`: string - Type of property
- `lot_size`: number - Lot size in square feet
- `listing_url`: string - URL to original listing
- `source`: string - Data source (e.g., "mls", "zillow", "redfin")

**Optional Fields:**
- `city`: string - City name
- `state`: string - State abbreviation
- `zip_code`: string - Zip/postal code
- `latitude`: number - Geographic latitude
- `longitude`: number - Geographic longitude
- `images`: array of strings - URLs to property images
- `description`: string - Property description

**Response (201 Created):**
```json
{
  "_id": "507f1f77bcf86cd799439013",
  "address": "789 Pine Street",
  "city": "Berkeley",
  "state": "CA",
  "zip_code": "94704",
  "price": 550000,
  "bedrooms": 3,
  "bathrooms": 2.5,
  "sqft": 1950,
  "year_built": 1998,
  "property_type": "single_family",
  "lot_size": 5500,
  "listing_url": "https://example.com/property/789",
  "source": "mls",
  "latitude": 37.8716,
  "longitude": -122.2727,
  "description": "Charming Victorian-style home with updated utilities",
  "images": ["https://example.com/images/789-1.jpg"],
  "score": 0,
  "created_at": "2024-01-21T11:30:00Z",
  "updated_at": "2024-01-21T11:30:00Z"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": {
    "code": "MISSING_FIELD",
    "message": "Missing required field: property_type"
  }
}
```

---

### GET /api/properties/<property_id>

Retrieve a single property by its ID.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `property_id` | string | MongoDB ObjectId of the property |

**Example Request:**

```bash
curl -X GET "http://localhost:5000/api/properties/507f1f77bcf86cd799439011" \
  -H "Authorization: Bearer your_access_token"
```

**Response (200 OK):**
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "address": "123 Oak Street",
  "city": "San Francisco",
  "state": "CA",
  "zip_code": "94102",
  "price": 350000,
  "bedrooms": 3,
  "bathrooms": 2,
  "sqft": 1850,
  "year_built": 1995,
  "property_type": "single_family",
  "lot_size": 5000,
  "listing_url": "https://example.com/property/123",
  "source": "zillow",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "description": "Beautiful single family home in desirable neighborhood",
  "images": ["https://example.com/images/123-1.jpg"],
  "score": 78.5,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:22:00Z"
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "Property not found"
}
```

---

### PUT /api/properties/<property_id>

Update a property. Send only the fields you want to modify.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `property_id` | string | MongoDB ObjectId of the property |

**Request Body (application/json):**

```json
{
  "price": 360000,
  "description": "Price reduced! Beautiful home with updated kitchen"
}
```

**Example Request:**

```bash
curl -X PUT "http://localhost:5000/api/properties/507f1f77bcf86cd799439011" \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{"price": 360000, "description": "Price reduced!"}'
```

**Response (200 OK):**
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "address": "123 Oak Street",
  "city": "San Francisco",
  "state": "CA",
  "zip_code": "94102",
  "price": 360000,
  "bedrooms": 3,
  "bathrooms": 2,
  "sqft": 1850,
  "year_built": 1995,
  "property_type": "single_family",
  "lot_size": 5000,
  "listing_url": "https://example.com/property/123",
  "source": "zillow",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "description": "Price reduced!",
  "images": ["https://example.com/images/123-1.jpg"],
  "score": 78.5,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-21T12:00:00Z"
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "Property not found"
}
```

---

### DELETE /api/properties/<property_id>

Delete a property from the system.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `property_id` | string | MongoDB ObjectId of the property |

**Example Request:**

```bash
curl -X DELETE "http://localhost:5000/api/properties/507f1f77bcf86cd799439011" \
  -H "Authorization: Bearer your_access_token"
```

**Response (200 OK):**
```json
{
  "message": "Property deleted successfully"
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "Property not found"
}
```

---

## Analysis

Analysis endpoints provide comprehensive investment analysis for properties and markets. These include financial metrics, tax benefits analysis, and financing options.

### GET /api/analysis/property/<property_id>

Get comprehensive investment analysis for a property with default parameters. The API automatically looks up market data by property location (zip code > city > state > defaults).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `property_id` | string | MongoDB ObjectId of the property |

**Example Request:**

```bash
curl -X GET "http://localhost:5000/api/analysis/property/507f1f77bcf86cd799439011" \
  -H "Authorization: Bearer your_access_token"
```

**Response (200 OK):**
```json
{
  "property_id": "507f1f77bcf86cd799439011",
  "financial_analysis": {
    "monthly_rent": 1666.67,
    "monthly_expenses": {
      "total": 625.0,
      "property_tax": 250.0,
      "insurance": 87.5,
      "maintenance": 150.0,
      "utilities": 137.5
    },
    "mortgage_payment": 1216.04,
    "monthly_cash_flow": -174.37,
    "annual_cash_flow": -2092.44,
    "cap_rate": 4.17,
    "cash_on_cash_return": -2.87,
    "roi": {
      "total_roi": 42.0,
      "annualized_roi": 7.25,
      "payback_period_years": 13.8
    },
    "break_even_point": 5.2,
    "price_to_rent_ratio": 15.0,
    "gross_yield": 6.67,
    "total_investment": 69000.0,
    "down_payment_percentage": 0.20,
    "interest_rate": 0.045,
    "term_years": 30,
    "holding_period": 5,
    "appreciation_rate": 0.03
  },
  "tax_benefits": {
    "depreciation": {
      "building_value": 240000.0,
      "annual_depreciation": 8727.27,
      "useful_life_years": 27.5
    },
    "mortgage_interest_deduction": 10750.23,
    "property_tax_deduction": 3000.0,
    "total_deductions": 22477.5,
    "estimated_tax_savings": 4945.05,
    "monthly_tax_savings": 412.09,
    "tax_bracket": 0.22
  },
  "financing_options": {
    "options": [
      {
        "name": "Conventional",
        "down_payment_min": 0.03,
        "interest_rate_avg": 0.045,
        "max_term_years": 30,
        "credit_score_min": 580,
        "fees": "1% - 2%",
        "available": true
      },
      {
        "name": "FHA",
        "down_payment_min": 0.035,
        "interest_rate_avg": 0.048,
        "max_term_years": 30,
        "credit_score_min": 500,
        "mortgage_insurance": "Required",
        "available": true
      }
    ],
    "local_programs": [],
    "recommended": "Conventional"
  },
  "market_data": {
    "property_tax_rate": 0.01,
    "price_to_rent_ratio": 15,
    "vacancy_rate": 0.08,
    "appreciation_rate": 0.03,
    "avg_hoa_fee": 0,
    "tax_benefits": {},
    "financing_programs": []
  }
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "Property not found"
}
```

---

### POST /api/analysis/property/<property_id>

Run custom investment analysis with user-defined parameters.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `property_id` | string | MongoDB ObjectId of the property |

**Request Body (application/json):**

All parameters are optional. Defaults are shown below:

```json
{
  "down_payment_percentage": 0.25,
  "interest_rate": 0.05,
  "term_years": 25,
  "holding_period": 7,
  "appreciation_rate": 0.04,
  "tax_bracket": 0.24,
  "credit_score": 750,
  "veteran": false,
  "first_time_va": true
}
```

**Parameter Descriptions:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `down_payment_percentage` | float | 0.20 | Down payment as percentage (0.0-1.0) |
| `interest_rate` | float | 0.045 | Mortgage interest rate (0.0-0.15) |
| `term_years` | integer | 30 | Loan term in years (5-40) |
| `holding_period` | integer | 5 | Years to hold property (1-50) |
| `appreciation_rate` | float | 0.03 | Annual property appreciation rate (0.0-0.10) |
| `tax_bracket` | float | 0.22 | Federal income tax bracket (0.10-0.37) |
| `credit_score` | integer | 720 | Credit score (300-850) |
| `veteran` | boolean | false | Is the buyer a veteran? |
| `first_time_va` | boolean | true | Is this first time using VA benefits? |

**Example Request:**

```bash
curl -X POST "http://localhost:5000/api/analysis/property/507f1f77bcf86cd799439011" \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "down_payment_percentage": 0.25,
    "interest_rate": 0.05,
    "term_years": 25,
    "tax_bracket": 0.24
  }'
```

**Response (200 OK):**

Same structure as GET endpoint, with the addition of a `parameters` field showing the custom inputs used:

```json
{
  "property_id": "507f1f77bcf86cd799439011",
  "parameters": {
    "down_payment_percentage": 0.25,
    "interest_rate": 0.05,
    "term_years": 25,
    "holding_period": 5,
    "appreciation_rate": 0.03,
    "tax_bracket": 0.24,
    "credit_score": 720,
    "veteran": false,
    "first_time_va": true
  },
  "financial_analysis": {
    "monthly_rent": 1666.67,
    "monthly_expenses": {...},
    "mortgage_payment": 1241.80,
    "monthly_cash_flow": -183.46,
    "annual_cash_flow": -2201.52,
    "cap_rate": 4.17,
    "cash_on_cash_return": -2.53,
    "roi": {...},
    "break_even_point": 5.8,
    "price_to_rent_ratio": 15.0,
    "gross_yield": 6.67,
    "total_investment": 87500.0,
    "down_payment_percentage": 0.25,
    "interest_rate": 0.05,
    "term_years": 25,
    "holding_period": 5,
    "appreciation_rate": 0.03
  },
  "tax_benefits": {...},
  "financing_options": {...},
  "market_data": {...}
}
```

---

## Markets

Market endpoints provide aggregated analysis across properties in specific geographic areas.

### GET /api/analysis/market/<market_id>

Get market analysis for a specific market area with aggregated property data.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `market_id` | string | MongoDB ObjectId of the market |

**Example Request:**

```bash
curl -X GET "http://localhost:5000/api/analysis/market/507f1f77bcf86cd799439014" \
  -H "Authorization: Bearer your_access_token"
```

**Response (200 OK):**
```json
{
  "market_id": "507f1f77bcf86cd799439014",
  "market_name": "San Francisco, CA",
  "market_type": "city",
  "aggregate_data": {
    "count": 150,
    "avg_price": 550000,
    "median_price": 525000,
    "min_price": 250000,
    "max_price": 1200000,
    "avg_sqft": 1800,
    "avg_price_per_sqft": 305.56,
    "avg_bedrooms": 3.2,
    "avg_bathrooms": 2.1,
    "avg_year_built": 1985,
    "avg_roi": 0.062,
    "avg_cap_rate": 0.038,
    "avg_cash_on_cash_return": 0.045,
    "avg_price_to_rent_ratio": 16.2,
    "vacancy_rate": 0.06,
    "appreciation_rate": 0.035
  },
  "market_metrics": {
    "market_strength": "strong",
    "investment_opportunity": "moderate",
    "growth_trend": "positive",
    "days_on_market_avg": 28
  }
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "Market not found"
}
```

---

### POST /api/analysis/market/<market_id>

Run custom market analysis with user-defined parameters.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `market_id` | string | MongoDB ObjectId of the market |

**Request Body (application/json):**

```json
{
  "metric_filters": {
    "min_price": 300000,
    "max_price": 700000,
    "min_roi": 0.05
  }
}
```

**Example Request:**

```bash
curl -X POST "http://localhost:5000/api/analysis/market/507f1f77bcf86cd799439014" \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "metric_filters": {
      "min_price": 300000,
      "max_price": 700000
    }
  }'
```

**Response (200 OK):**

Same structure as GET endpoint, with the addition of a `parameters` field:

```json
{
  "market_id": "507f1f77bcf86cd799439014",
  "market_name": "San Francisco, CA",
  "market_type": "city",
  "parameters": {
    "metric_filters": {
      "min_price": 300000,
      "max_price": 700000,
      "min_roi": 0.05
    }
  },
  "aggregate_data": {...},
  "market_metrics": {...}
}
```

---

### GET /api/markets/top

Get top performing markets ranked by investment metrics. Useful for identifying markets with the best investment opportunities.

**Query Parameters:**

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `metric` | string | "roi" | - | Ranking metric: "roi" or "cap_rate" |
| `limit` | integer | 10 | 100 | Number of top markets to return |

**Example Requests:**

```bash
# Get top 10 markets by ROI
curl -X GET "http://localhost:5000/api/markets/top?metric=roi&limit=10" \
  -H "Authorization: Bearer your_access_token"

# Get top 20 markets by cap rate
curl -X GET "http://localhost:5000/api/markets/top?metric=cap_rate&limit=20" \
  -H "Authorization: Bearer your_access_token"
```

**Response (200 OK):**
```json
[
  {
    "rank": 1,
    "market_id": "507f1f77bcf86cd799439015",
    "market_name": "Phoenix, AZ",
    "market_type": "city",
    "metric_value": 0.082,
    "metric_name": "roi",
    "property_count": 245,
    "avg_price": 425000,
    "avg_cap_rate": 0.065,
    "avg_cash_flow": 1850
  },
  {
    "rank": 2,
    "market_id": "507f1f77bcf86cd799439016",
    "market_name": "Austin, TX",
    "market_type": "city",
    "metric_value": 0.078,
    "metric_name": "roi",
    "property_count": 312,
    "avg_price": 485000,
    "avg_cap_rate": 0.062,
    "avg_cash_flow": 1920
  },
  {
    "rank": 3,
    "market_id": "507f1f77bcf86cd799439017",
    "market_name": "Denver, CO",
    "market_type": "city",
    "metric_value": 0.075,
    "metric_name": "roi",
    "property_count": 198,
    "avg_price": 515000,
    "avg_cap_rate": 0.058,
    "avg_cash_flow": 1780
  }
]
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Invalid metric"
}
```

---

## Authentication Endpoints

Authentication endpoints manage user registration, login, and logout. These endpoints do not require JWT authentication.

### POST /api/auth/register

Register a new user account.

**Request Body (application/json):**

```json
{
  "username": "john_investor",
  "password": "SecurePassword123!"
}
```

**Required Fields:**
- `username`: string (required, must be unique)
- `password`: string (required, minimum 8 characters recommended)

**Example Request:**

```bash
curl -X POST "http://localhost:5000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_investor",
    "password": "SecurePassword123!"
  }'
```

**Response (201 Created):**
```json
{
  "message": "User registered successfully"
}
```

**Error Response (409 Conflict):**
```json
{
  "message": "Username already exists"
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "Username cannot be blank"
}
```

---

### POST /api/auth/login

Authenticate a user and receive a JWT access token.

**Request Body (application/json):**

```json
{
  "username": "john_investor",
  "password": "SecurePassword123!"
}
```

**Required Fields:**
- `username`: string
- `password`: string

**Example Request:**

```bash
curl -X POST "http://localhost:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_investor",
    "password": "SecurePassword123!"
  }'
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2ludmVzdG9yIiwiaWF0IjoxNjM5NzU5NDMyLCJleHAiOjE2Mzk3NjMwMzJ9.sxLq-1yKz7qJK9K_qJ7q5yK_qJq5yK9K_qJ7q5yKz7q"
}
```

**Error Response (401 Unauthorized):**
```json
{
  "message": "Invalid username or password"
}
```

---

### POST /api/auth/logout

Logout the current user. Requires a valid JWT token.

**Headers:**
```
Authorization: Bearer your_access_token
```

**Example Request:**

```bash
curl -X POST "http://localhost:5000/api/auth/logout" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "message": "User logged out successfully"
}
```

**Error Response (401 Unauthorized):**
```json
{
  "error": "Missing or invalid JWT token"
}
```

---

## Error Handling

All API endpoints return appropriate HTTP status codes and error responses. Errors are returned as JSON objects with an `error` field containing a description.

### Standard Error Codes

| Status Code | Description | Example Scenario |
|-------------|-------------|-----------------|
| 400 | Bad Request | Missing required field, invalid parameter format |
| 401 | Unauthorized | Missing JWT token, invalid token, user not logged in |
| 404 | Not Found | Property/market ID doesn't exist |
| 409 | Conflict | Username already exists during registration |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Database or critical service unavailable |

### Error Response Format

Structured errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Descriptive error message"
  }
}
```

For example, validation errors:

```json
{
  "error": {
    "code": "MISSING_FIELD",
    "message": "Missing required field: property_type"
  }
}
```

Invalid ObjectId format:

```json
{
  "error": {
    "code": "INVALID_ID",
    "message": "Invalid property ID format"
  }
}
```

### Handling Errors in Client Code

Example error handling in JavaScript:

```javascript
async function fetchProperty(propertyId, token) {
  try {
    const response = await fetch(
      `http://localhost:5000/api/properties/${propertyId}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );

    if (!response.ok) {
      const error = await response.json();
      if (response.status === 404) {
        console.error('Property not found:', error.error);
      } else if (response.status === 401) {
        console.error('Unauthorized - please login');
      } else {
        console.error('Error:', error.error);
      }
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error('Network error:', error);
  }
}
```

---

## Best Practices

### Authentication
- Store JWT tokens securely (use httpOnly cookies in browser)
- Refresh tokens periodically
- Never expose JWT tokens in logs or error messages
- Use HTTPS in production to prevent token interception

### Rate Limiting
- Implement exponential backoff for retries
- Cache results to minimize API calls
- Monitor your request rate to avoid hitting limits
- Contact support if you need higher limits

### Pagination
- Always paginate large result sets
- Use appropriate `limit` values (50-100 recommended)
- Check response length to detect end of results
- Implement cursor-based pagination for large datasets

### Performance
- Cache property and market data when possible
- Use specific filters to reduce result sets
- Consider using batch operations for multiple properties
- Leverage the analysis endpoints for pre-computed metrics

### Error Recovery
- Implement retry logic with exponential backoff
- Log errors for debugging and monitoring
- Provide user-friendly error messages
- Handle network timeouts gracefully

---

## Common Workflows

### Searching for Investment Properties

```bash
# 1. Search for properties in your price range
curl "http://localhost:5000/api/properties?minPrice=250000&maxPrice=500000&state=CA&limit=50"

# 2. Get detailed analysis for a property
curl "http://localhost:5000/api/analysis/property/PROPERTY_ID"

# 3. Compare with market analysis
curl "http://localhost:5000/api/analysis/market/MARKET_ID"
```

### Custom Investment Analysis

```bash
# Run analysis with custom financing terms
curl -X POST "http://localhost:5000/api/analysis/property/PROPERTY_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "down_payment_percentage": 0.25,
    "interest_rate": 0.045,
    "term_years": 25,
    "tax_bracket": 0.24
  }'
```

### Finding Top Markets

```bash
# Get top 15 markets by ROI
curl "http://localhost:5000/api/markets/top?metric=roi&limit=15"

# Get top 10 markets by cap rate
curl "http://localhost:5000/api/markets/top?metric=cap_rate&limit=10"
```

---

## Support & Questions

For API issues, questions, or feature requests:
- Check the error message for specific details
- Review this documentation for endpoint usage
- Check the `/health/ready` endpoint to verify service status
- Enable detailed logging to debug integration issues

---

**API Version:** 1.2.0
**Last Updated:** 2026-03-03
**Documentation Status:** Current
