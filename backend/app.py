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