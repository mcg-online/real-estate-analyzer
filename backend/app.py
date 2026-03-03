from flask import Flask, jsonify
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
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET')
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


@app.route('/')
def home():
    return jsonify({
        'message': 'Real Estate Investment Analysis API',
        'version': '1.0.0'
    })


def run_scheduled_tasks():
    """Run scheduled tasks in background thread"""
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

    scheduler_thread = threading.Thread(target=run_schedule)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    return scheduler_thread


@app.teardown_appcontext
def shutdown_db(exception=None):
    close_db()


if __name__ == '__main__':
    run_scheduled_tasks()
    app.run(debug=True, host='0.0.0.0', port=5000)
