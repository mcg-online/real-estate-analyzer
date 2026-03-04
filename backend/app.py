from flask import Flask, jsonify, request
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_cors import CORS
import threading
import time
import logging
import schedule
import uuid
from dotenv import load_dotenv
import os

__version__ = '1.5.0'

# Load environment variables from .env (no-op when not present)
load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scheduler state — module-level so the watchdog and health endpoint can
# reference the thread regardless of how many times create_app() is called.
# ---------------------------------------------------------------------------
_scheduler_thread = None
_scheduler_last_heartbeat = None
_scheduler_lock = threading.Lock()


def run_scheduled_tasks():
    """Start the background scheduler thread.

    Registers the daily/weekly jobs and launches a daemon thread.  Idempotent:
    if a live thread already exists this function returns it unchanged.
    """
    global _scheduler_thread

    # Avoid spawning duplicate threads (e.g. if create_app is called twice).
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return _scheduler_thread

    from services.scheduler import update_property_data, update_market_data

    def run_schedule():
        global _scheduler_last_heartbeat
        while True:
            try:
                schedule.run_pending()
                with _scheduler_lock:
                    _scheduler_last_heartbeat = time.time()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(300)

    schedule.every().day.at("01:00").do(update_property_data)
    schedule.every().week.do(update_market_data)

    _scheduler_thread = threading.Thread(target=run_schedule, name="scheduler")
    _scheduler_thread.daemon = True
    _scheduler_thread.start()
    return _scheduler_thread


def _ensure_scheduler_running():
    """Restart the scheduler thread if it has died."""
    global _scheduler_thread
    if _scheduler_thread is not None and not _scheduler_thread.is_alive():
        logger.warning("Scheduler thread died, restarting...")
        run_scheduled_tasks()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(config=None):
    """Create and return a configured Flask application instance.

    Parameters
    ----------
    config:
        Any of the following:
        - ``None``  — uses :class:`config.BaseConfig` (reads from env vars)
        - A :class:`config.BaseConfig` subclass (not an instance)
        - A plain ``dict`` of config overrides applied on top of BaseConfig

    Scheduler startup
    -----------------
    The background scheduler starts automatically unless ``TESTING=True`` is
    present in the resolved configuration.  This keeps tests fast and prevents
    spurious background threads during the test session.

    Backward compatibility
    ----------------------
    ``from app import app`` and ``from app import limiter`` continue to work
    because both names are re-exported at module level below.
    """
    from config import BaseConfig

    application = Flask(__name__)

    # ----------------------------------------------------------------- Config
    # Start with BaseConfig defaults, then layer on any caller-supplied values.
    application.config.from_object(BaseConfig)

    if config is not None:
        if isinstance(config, dict):
            application.config.update(config)
        else:
            # Treat it as a config class (not instantiated)
            application.config.from_object(config)

    # Cache config must be applied separately because BaseConfig uses a
    # classmethod (_cache_config) rather than simple class attributes so that
    # environment variables are read lazily.
    if "CACHE_TYPE" not in application.config:
        application.config.update(BaseConfig._cache_config())

    # Force correct MAX_CONTENT_LENGTH if not already set by caller
    application.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)

    # ------------------------------------------------------------ Extensions
    cors_origins = application.config.get("CORS_ORIGINS", ["http://localhost:3000"])
    CORS(application, origins=cors_origins, supports_credentials=True)

    api = Api(application)

    jwt = JWTManager(application)

    from utils.auth import is_token_revoked

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return is_token_revoked(jwt_payload['jti'])

    redis_url = os.getenv('REDIS_URL')
    if redis_url and not application.config.get('TESTING'):
        _cache_cfg = {'CACHE_TYPE': 'RedisCache', 'CACHE_REDIS_URL': redis_url}
        logger.info("Cache using Redis at %s", redis_url)
    else:
        _cache_cfg = {'CACHE_TYPE': application.config.get('CACHE_TYPE', 'SimpleCache')}
        if not redis_url:
            logger.info("Cache using SimpleCache (no REDIS_URL configured)")

    Cache(application, config=_cache_cfg)

    if redis_url and not application.config.get('TESTING'):
        _limiter = Limiter(
            get_remote_address,
            app=application,
            storage_uri=redis_url,
            default_limits=["200 per day", "50 per hour"],
        )
        logger.info("Rate limiter using Redis storage")
    else:
        _limiter = Limiter(
            get_remote_address,
            app=application,
            default_limits=["200 per day", "50 per hour"],
        )

    # Store limiter on app so routes/users.py can import it from the app module.
    # We keep the module-level `limiter` name updated via the post-factory hook.
    application.extensions['limiter'] = _limiter

    # --------------------------------------------------------- Database init
    from utils.database import init_db
    init_db(application)

    # ----------------------------------------------------------- Route setup
    from routes.properties import PropertyResource, PropertyListResource
    from routes.analysis import (
        PropertyAnalysisResource,
        MarketAnalysisResource,
        TopMarketsResource,
        OpportunityScoringResource,
    )
    from routes.users import UserRegistration, UserLogin, UserLogout

    # Each resource is available at both the versioned (/api/v1/*) and legacy
    # (/api/*) paths to maintain full backward compatibility.
    api.add_resource(PropertyListResource, '/api/v1/properties', '/api/properties')
    api.add_resource(PropertyResource, '/api/v1/properties/<property_id>', '/api/properties/<property_id>')
    api.add_resource(PropertyAnalysisResource, '/api/v1/analysis/property/<property_id>', '/api/analysis/property/<property_id>')
    api.add_resource(MarketAnalysisResource, '/api/v1/analysis/market/<market_id>', '/api/analysis/market/<market_id>')
    api.add_resource(TopMarketsResource, '/api/v1/markets/top', '/api/markets/top')
    api.add_resource(OpportunityScoringResource, '/api/v1/analysis/score/<property_id>', '/api/analysis/score/<property_id>')
    api.add_resource(UserRegistration, '/api/v1/auth/register', '/api/auth/register')
    api.add_resource(UserLogin, '/api/v1/auth/login', '/api/auth/login')
    api.add_resource(UserLogout, '/api/v1/auth/logout', '/api/auth/logout')

    # ----------------------------------------------- Request logging middleware
    @application.before_request
    def before_request():
        request.start_time = time.time()
        request.request_id = str(uuid.uuid4())[:8]

    @application.after_request
    def after_request(response):
        latency = (time.time() - getattr(request, 'start_time', time.time())) * 1000
        logger.info(
            "request_id=%s method=%s path=%s status=%d latency_ms=%.1f",
            getattr(request, 'request_id', '-'),
            request.method,
            request.path,
            response.status_code,
            latency,
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; frame-ancestors 'none'"
        if not application.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # ----------------------------------------------------------- Route handlers
    @application.route('/')
    def home():
        return jsonify({
            'message': 'Real Estate Investment Analysis API',
            'version': __version__,
            'api_versions': ['v1'],
            'current_api': '/api/v1'
        })

    @application.route('/health')
    def health_check():
        """Shallow health check for load balancers"""
        return jsonify({'status': 'ok'}), 200

    @application.route('/health/ready')
    def readiness_check():
        """Deep readiness check — verifies dependencies"""
        checks = {}
        overall_healthy = True

        # MongoDB check
        try:
            from utils.database import get_db
            db = get_db()
            db.command('ping')
            checks['mongodb'] = {'status': 'ok'}
        except Exception as e:
            checks['mongodb'] = {'status': 'error', 'detail': str(e)}
            overall_healthy = False

        # Scheduler check
        if _scheduler_thread is not None:
            if _scheduler_thread.is_alive():
                checks['scheduler'] = {'status': 'ok'}
                with _scheduler_lock:
                    if _scheduler_last_heartbeat:
                        elapsed = time.time() - _scheduler_last_heartbeat
                        if elapsed > 600:  # No heartbeat in 10 minutes
                            checks['scheduler'] = {
                                'status': 'warning',
                                'detail': f'No heartbeat for {int(elapsed)}s'
                            }
            else:
                checks['scheduler'] = {'status': 'error', 'detail': 'Scheduler thread died'}
                overall_healthy = False

        _ensure_scheduler_running()

        status_code = 200 if overall_healthy else 503
        return jsonify({
            'status': 'healthy' if overall_healthy else 'degraded',
            'checks': checks,
            'version': __version__
        }), status_code

    @application.route('/health/live')
    def liveness_check():
        """Liveness probe — is the process responsive"""
        return jsonify({'status': 'alive', 'pid': os.getpid()}), 200

    # ---------------------------------------------------------------- Teardown
    from utils.database import close_db

    @application.teardown_appcontext
    def shutdown_db(exception=None):
        close_db()

    # ------------------------------------------- Conditional scheduler startup
    # Skip when TESTING=True so the test suite does not spin up background
    # threads.  The module-level call below handles the production/gunicorn
    # case.
    if not application.config.get('TESTING'):
        run_scheduled_tasks()

    return application, _limiter


# ---------------------------------------------------------------------------
# Module-level singletons — kept here so that:
#   1. ``gunicorn app:app`` works without change.
#   2. ``from app import app`` and ``from app import limiter`` still work.
#   3. Existing test fixtures that do ``import app; app.app`` still work.
# ---------------------------------------------------------------------------

app, limiter = create_app()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=5000)
