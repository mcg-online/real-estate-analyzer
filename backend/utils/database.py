from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from urllib.parse import urlparse
import time
import logging
import threading

_db_client = None
_db = None
_db_lock = threading.Lock()
_mongodb_uri = None

logger = logging.getLogger(__name__)


def _parse_db_name(uri):
    """Parse database name from MongoDB URI, handling query params."""
    parsed = urlparse(uri)
    db_name = parsed.path.lstrip('/')
    if not db_name:
        db_name = 'realestate'
    return db_name


def _connect():
    """Establish MongoDB connection with retries and exponential backoff."""
    global _db_client, _db
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            _db_client = MongoClient(
                _mongodb_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                maxPoolSize=50,
                minPoolSize=2,
                retryWrites=True,
                retryReads=True,
                appname='real-estate-analyzer',
            )
            _db_client.admin.command('ping')
            db_name = _parse_db_name(_mongodb_uri)
            _db = _db_client[db_name]

            # Create indexes
            _db['properties'].create_index('listing_url', unique=True)
            _db['properties'].create_index('state')
            _db['properties'].create_index([('state', 1), ('city', 1)])
            _db['properties'].create_index('zip_code')
            _db['markets'].create_index('market_type')
            _db['markets'].create_index('zip_code')
            _db['markets'].create_index([('state', 1), ('city', 1)])
            _db['users'].create_index('username', unique=True)

            logger.info("Successfully connected to MongoDB")
            return _db
        except Exception as e:
            if attempt >= max_retries:
                logger.error(f"Failed to connect to MongoDB after {max_retries} attempts: {e}")
                return None
            logger.warning(f"MongoDB connection attempt {attempt} failed. Retrying...")
            time.sleep(2 ** attempt)


def init_db(app):
    global _mongodb_uri
    _mongodb_uri = app.config.get('MONGODB_URI')
    if not _mongodb_uri:
        logger.warning("MONGODB_URI not configured. Starting without database.")
        return None
    return _connect()


def get_db():
    global _db, _db_client
    if _db is None:
        with _db_lock:
            if _db is None:
                if _mongodb_uri is None:
                    raise ValueError("Database not initialized. Call init_db first.")
                result = _connect()
                if result is None:
                    raise ConnectionError("Cannot connect to MongoDB")
                return result
    # Verify connection is still alive
    try:
        _db_client.admin.command('ping')
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception):
        logger.warning("Lost MongoDB connection. Attempting reconnect...")
        with _db_lock:
            result = _connect()
            if result is None:
                raise ConnectionError("Cannot reconnect to MongoDB")
            return result
    return _db


def close_db():
    global _db_client, _db
    if _db_client:
        _db_client.close()
        _db_client = None
        _db = None
        logger.info("Database connection closed")
