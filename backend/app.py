from flask import Flask, jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os
import logging
from routes.properties import PropertyResource, PropertyListResource
from routes.analysis import AnalysisResource
from routes.users import UserRegistration, UserLogin, UserLogout
from utils.database import init_db, close_db

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET')
app.config['MONGODB_URI'] = os.getenv('DATABASE_URL')

# Initialize extensions
api = Api(app)
jwt = JWTManager(app)

# Initialize database
init_db(app)

# Register routes
api.add_resource(PropertyListResource, '/api/properties')
api.add_resource(PropertyResource, '/api/properties/<property_id>')
api.add_resource(AnalysisResource, '/api/analysis/<property_id>')
api.add_resource(UserRegistration, '/api/auth/register')
api.add_resource(UserLogin, '/api/auth/login')
api.add_resource(UserLogout, '/api/auth/logout')

@app.route('/')
def home():
    return jsonify({
        'message': 'Real Estate Investment Analysis API',
        'version': '1.0.0'
    })

@app.teardown_appcontext
def shutdown_db(exception=None):
    close_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Add to backend/app.py

from flask_caching import Cache
import schedule
import threading
import time

# Initialize cache
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# Setup scheduled tasks
def run_scheduled_tasks():
    """Run scheduled tasks in background thread"""
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    # Schedule data update tasks
    schedule.every().day.at("01:00").do(update_property_data)
    schedule.every().week.do(update_market_data)
    
    # Start scheduler in separate thread
    scheduler_thread = threading.Thread(target=run_schedule)
    scheduler_thread.daemon = True
    scheduler_thread.start()

# Cache API responses
@cache.memoize(timeout=3600)
def get_cached_properties(filters, limit, skip, sort_by, sort_order):
    """Get cached property results"""
    # Implementation


from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Apply rate limits to API endpoints
@limiter.limit("10 per minute")
@app.route('/api/properties')
def get_properties():
    # Implementation