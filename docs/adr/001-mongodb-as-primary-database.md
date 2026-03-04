# ADR 001: MongoDB as Primary Database

**Status**: Accepted (v1.0.0+)

**Date**: 2024-01-01

**Deciders**: Development Team

## Context

Real Estate Analyzer needs to store:
- Property data with varying attributes (bedrooms, bathrooms, square footage, location, etc.)
- Market analysis data aggregated by state, city, and zip code
- User account information and preferences
- Investment analysis results with complex nested calculations

The application requires:
- Fast querying for property filtering and geographic searches
- Flexible schema to handle properties with different attributes
- Aggregation capabilities for market analysis
- Easy horizontal scaling for future growth
- Seamless integration with JavaScript/JSON APIs

## Decision

We chose **MongoDB** as the primary database because:

### 1. Flexible Schema

Property data varies significantly across listings. MongoDB's document model accommodates varying fields without schema migrations:

```python
# Property with all fields
{
  "_id": ObjectId("..."),
  "address": "123 Main St",
  "price": 500000,
  "bedrooms": 3,
  "bathrooms": 2,
  "sqft": 1800,
  "parking": 2,
  "pool": true,
  "lot_size": 0.25
}

# Property with minimal fields
{
  "_id": ObjectId("..."),
  "address": "456 Oak Ave",
  "price": 300000
}
```

Both documents coexist without schema conflicts.

### 2. Native JSON Support

MongoDB stores documents as JSON (BSON format), which aligns perfectly with REST APIs that send/receive JSON:

```python
# Python object directly serializes to JSON for API response
property_dict = property_obj.to_dict()
return jsonify(property_dict)  # Direct JSON serialization
```

No impedance mismatch between application objects and database format.

### 3. Aggregation Pipeline

Complex market analysis queries use MongoDB's aggregation framework:

```python
# Group properties by state, calculate average metrics
pipeline = [
    {"$match": {"state": "CA"}},
    {"$group": {
        "_id": "$state",
        "avg_price": {"$avg": "$price"},
        "avg_roi": {"$avg": "$roi"},
        "count": {"$sum": 1}
    }},
    {"$sort": {"avg_roi": -1}}
]
top_markets = db.properties.aggregate(pipeline)
```

Aggregations run on the database server, reducing data transfer and processing latency.

### 4. PyMongo Integration

Python integration is straightforward with PyMongo 4.x:

```python
from pymongo import MongoClient

client = MongoClient(os.getenv('DATABASE_URL'))
db = client['realestate']
properties = db['properties']

# CRUD operations are intuitive
property_doc = properties.insert_one({...})
properties.update_one({'_id': id}, {'$set': {...}})
properties.delete_one({'_id': id})
```

### 5. Indexing & Performance

Indexes improve query performance for common access patterns:

```python
# Created on startup
db.properties.create_index('state')
db.properties.create_index([('state', 1), ('city', 1)])
db.properties.create_index('zip_code')
db.markets.create_index('market_type')
db.users.create_index('username', unique=True)
```

### 6. Connection Resilience

Built-in connection pooling and auto-reconnect capabilities:

```python
# App starts even without MongoDB (graceful degradation)
try:
    client = MongoClient(
        mongodb_uri,
        serverSelectionTimeoutMS=2000,
        retryWrites=True,
        retryReads=True,
        maxPoolSize=50
    )
except Exception as e:
    logger.warning("MongoDB unavailable: %s", e)
    # App continues; endpoints return 503 until DB is available
```

## Consequences

### Positive

1. **Flexibility**: Easy schema evolution as business requirements change
2. **Performance**: Aggregation pipeline reduces application-level processing
3. **Scalability**: Horizontal scaling through sharding (MongoDB Atlas)
4. **Developer Experience**: JSON documents align with application code
5. **Rapid Development**: No schema migrations needed for new property types

### Negative

1. **Data Duplication**: Denormalization may lead to data consistency challenges
2. **No ACID Across Collections**: Complex transactions spanning multiple collections are limited
3. **Storage Overhead**: BSON format uses more space than relational schemas
4. **Learning Curve**: Different paradigm than traditional SQL databases

### Mitigations

- **Data Consistency**: Use document validation rules where needed
- **Transactions**: MongoDB 4.0+ supports multi-document transactions (limited use)
- **Storage**: Compression and selective field indexing reduce overhead
- **Testing**: Comprehensive test suite validates data consistency

## Related Decisions

- **ADR 002**: JWT Authentication (stateless, works well with MongoDB user documents)
- **ADR 004**: Redis Integration (complements MongoDB for caching and rate limiting)

## References

- [MongoDB Documentation](https://docs.mongodb.com/)
- [PyMongo 4.x Guide](https://pymongo.readthedocs.io/)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) - Managed MongoDB service
- [Aggregation Pipeline](https://docs.mongodb.com/manual/core/aggregation-pipeline/)
