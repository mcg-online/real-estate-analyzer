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

from routes.properties import PropertyResource, PropertyListResource
from routes.analysis import PropertyAnalysisResource, MarketAnalysisResource, TopMarketsResource
from routes.users import UserRegistration, UserLogin, UserLogout
from utils.database import init_db, close_db
from services.scheduler import update_property_data, update_market_data

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)

# JWT configuration - Flask-JWT-Extended uses JWT_SECRET_KEY, not SECRET_KEY
jwt_secret = os.getenv('JWT_SECRET')
if not jwt_secret or jwt_secret in ('your_secret_key', 'changeme', 'secret'):
    logger.warning("JWT_SECRET is missing or set to a placeholder. Using a random secret.")
    jwt_secret = os.urandom(32).hex()
app.config['JWT_SECRET_KEY'] = jwt_secret
app.config['SECRET_KEY'] = jwt_secret
app.config['MONGODB_URI'] = os.getenv('DATABASE_URL')

# Initialize extensions
CORS(app)
api = Api(app)
jwt = JWTManager(app)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

# Initialize database
init_db(app)

# Register routes
api.add_resource(PropertyListResource, '/api/properties')
api.add_resource(PropertyResource, '/api/properties/<property_id>')
api.add_resource(PropertyAnalysisResource, '/api/analysis/property/<property_id>')
api.add_resource(MarketAnalysisResource, '/api/analysis/market/<market_id>')
api.add_resource(TopMarketsResource, '/api/markets/top')
api.add_resource(UserRegistration, '/api/auth/register')
api.add_resource(UserLogin, '/api/auth/login')
api.add_resource(UserLogout, '/api/auth/logout')


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
    return response


@app.route('/')
def home():
    return jsonify({
        'message': 'Real Estate Investment Analysis API',
        'version': '1.0.0'
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

    status_code = 200 if overall_healthy else 503
    return jsonify({
        'status': 'healthy' if overall_healthy else 'degraded',
        'checks': checks,
        'version': '1.0.0'
    }), status_code


@app.route('/health/live')
def liveness_check():
    """Liveness probe - is the process responsive"""
    return jsonify({'status': 'alive', 'pid': os.getpid()}), 200


_scheduler_thread = None


def run_scheduled_tasks():
    """Run scheduled tasks in background thread"""
    global _scheduler_thread

    def run_schedule():
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(300)

    schedule.every().day.at("01:00").do(update_property_data)
    schedule.every().week.do(update_market_data)

    _scheduler_thread = threading.Thread(target=run_schedule)
    _scheduler_thread.daemon = True
    _scheduler_thread.start()
    return _scheduler_thread


@app.teardown_appcontext
def shutdown_db(exception=None):
    close_db()


if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    run_scheduled_tasks()
    app.run(debug=debug, host='0.0.0.0', port=5000)
