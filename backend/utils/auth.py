# JWT token blocklist.
# Uses Redis when REDIS_URL is set; falls back to an in-process set so the app
# stays functional without Redis.  The module-level singleton is initialised
# lazily on first use so that the import itself never raises.
import logging
import os

logger = logging.getLogger(__name__)

# Sentinel values for the lazy Redis connection:
#   None  -> not yet attempted
#   False -> attempted and failed (use fallback forever)
#   redis.Redis instance -> connected and healthy
_redis_client = None

# In-memory fallback used when Redis is unavailable.
_fallback_blocklist: set = set()

# TTL for blocklisted tokens in Redis (matches default JWT expiry: 1 hour).
_BLOCKLIST_TTL_SECONDS = 3600


def _get_redis():
    """Return a connected Redis client, or None if Redis is unavailable."""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis  # imported lazily so redis is optional at startup

                client = redis.from_url(redis_url, decode_responses=True)
                client.ping()
                _redis_client = client
                logger.info("JWT blocklist using Redis at %s", redis_url)
            except Exception as exc:
                logger.warning(
                    "Redis unavailable for JWT blocklist, using in-memory fallback: %s",
                    exc,
                )
                _redis_client = False  # mark as permanently failed this process
        else:
            # No URL configured — stay None so the branch is cheap to skip on
            # every subsequent call without re-reading the env var.
            _redis_client = False

    # Return the client if it is a real object; None for the False sentinel.
    return _redis_client if _redis_client else None


def add_token_to_blocklist(jti: str) -> None:
    """Blocklist a JWT identified by its *jti* claim."""
    r = _get_redis()
    if r is not None:
        r.setex(f"jwt_blocklist:{jti}", _BLOCKLIST_TTL_SECONDS, "1")
    else:
        _fallback_blocklist.add(jti)


def is_token_revoked(jti: str) -> bool:
    """Return True if the JWT identified by *jti* has been revoked."""
    r = _get_redis()
    if r is not None:
        return r.exists(f"jwt_blocklist:{jti}") > 0
    return jti in _fallback_blocklist
