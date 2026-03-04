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

from routes.properties import PropertyResource, PropertyListResource
from routes.analysis import PropertyAnalysisResource, MarketAnalysisResource, TopMarketsResource, OpportunityScoringResource
from routes.users import UserRegistration, UserLogin, UserLogout
from utils.database import init_db, close_db
from utils.auth import is_token_revoked
from services.scheduler import update_property_data, update_market_data

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# JWT configuration - Flask-JWT-Extended uses JWT_SECRET_KEY, not SECRET_KEY
jwt_secret = os.getenv('JWT_SECRET')
if not jwt_secret or jwt_secret in ('your_secret_key', 'changeme', 'secret'):
    logger.warning("JWT_SECRET is missing or set to a placeholder. Using a random secret.")
    jwt_secret = os.urandom(32).hex()
app.config['JWT_SECRET_KEY'] = jwt_secret
app.config['SECRET_KEY'] = jwt_secret
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_EXPIRY_SECONDS', 3600))  # 1 hour default
app.config['MONGODB_URI'] = os.getenv('DATABASE_URL')

# Initialize extensions
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, origins=cors_origins, supports_credentials=True)
api = Api(app)
jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return is_token_revoked(jwt_payload['jti'])


redis_url = os.getenv('REDIS_URL')
if redis_url:
    cache_config = {'CACHE_TYPE': 'RedisCache', 'CACHE_REDIS_URL': redis_url}
    logger.info("Cache using Redis at %s", redis_url)
else:
    cache_config = {'CACHE_TYPE': 'SimpleCache'}
    logger.info("Cache using SimpleCache (no REDIS_URL configured)")
cache = Cache(app, config=cache_config)

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

# Initialize database
init_db(app)

# Register routes - each resource is available at both the versioned (/api/v1/*)
# and legacy (/api/*) paths to maintain full backward compatibility.
api.add_resource(PropertyListResource, '/api/v1/properties', '/api/properties')
api.add_resource(PropertyResource, '/api/v1/properties/<property_id>', '/api/properties/<property_id>')
api.add_resource(PropertyAnalysisResource, '/api/v1/analysis/property/<property_id>', '/api/analysis/property/<property_id>')
api.add_resource(MarketAnalysisResource, '/api/v1/analysis/market/<market_id>', '/api/analysis/market/<market_id>')
api.add_resource(TopMarketsResource, '/api/v1/markets/top', '/api/markets/top')
api.add_resource(OpportunityScoringResource, '/api/v1/analysis/score/<property_id>', '/api/analysis/score/<property_id>')
api.add_resource(UserRegistration, '/api/v1/auth/register', '/api/auth/register')
api.add_resource(UserLogin, '/api/v1/auth/login', '/api/auth/login')
api.add_resource(UserLogout, '/api/v1/auth/logout', '/api/auth/logout')


# Request logging middleware
@app.before_request
def before_request():
    request.start_time = time.time()
    request.request_id = str(uuid.uuid4())[:8]


@app.after_request
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
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.route('/')
def home():
    return jsonify({
        'message': 'Real Estate Investment Analysis API',
        'version': __version__,
        'api_versions': ['v1'],
        'current_api': '/api/v1'
    })


@app.route('/health')
def health_check():
    """Shallow health check for load balancers"""
    return jsonify({'status': 'ok'}), 200


@app.route('/health/ready')
def readiness_check():
    """Deep readiness check - verifies dependencies"""
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


@app.route('/health/live')
def liveness_check():
    """Liveness probe - is the process responsive"""
    return jsonify({'status': 'alive', 'pid': os.getpid()}), 200


_scheduler_thread = None
_scheduler_last_heartbeat = None
_scheduler_lock = threading.Lock()


def run_scheduled_tasks():
    """Run scheduled tasks in background thread."""
    global _scheduler_thread

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


@app.teardown_appcontext
def shutdown_db(exception=None):
    close_db()


# Start scheduler for both direct execution and WSGI servers (e.g., gunicorn)
run_scheduled_tasks()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=5000)
