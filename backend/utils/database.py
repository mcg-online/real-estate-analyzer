from pymongo import MongoClient
import os
import logging

_db_client = None
_db = None

logger = logging.getLogger(__name__)

def init_db(app):
    global _db_client, _db
    mongodb_uri = app.config.get('MONGODB_URI')
    if not mongodb_uri:
        raise ValueError("MONGODB_URI configuration is missing")
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            _db_client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            _db_client.admin.command('ping')
            db_name = mongodb_uri.split('/')[-1]
            _db = _db_client[db_name]
            
            # Ensure unique index on listing_url to prevent duplicates
            _db['properties'].create_index('listing_url', unique=True)
            logger.info("Successfully connected to MongoDB")
            return _db
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Failed to connect to MongoDB after {max_retries} attempts: {e}")
                raise
            logger.warning(f"MongoDB connection attempt {retry_count} failed. Retrying...")
            time.sleep(2)

def get_db():
    global _db
    if _db is None:
        raise ValueError("Database not initialized. Call init_db first.")
    return _db

def close_db():
    global _db_client, _db
    if _db_client:
        _db_client.close()
        _db_client = None
        _db = None
        logger.info("Database connection closed")