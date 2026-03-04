import re
from functools import wraps

from flask_restful import Resource, reqparse
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from utils.database import get_db
from utils.auth import add_token_to_blocklist
import logging

logger = logging.getLogger(__name__)

user_parser = reqparse.RequestParser()
user_parser.add_argument('username', type=str, required=True, help="Username cannot be blank")
user_parser.add_argument('password', type=str, required=True, help="Password cannot be blank")


def _validate_username(username):
    username = username.strip()
    if not username or len(username) < 3 or len(username) > 64:
        return "Username must be 3-64 characters"
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', username):
        return "Username may only contain letters, digits, underscores, dots, and hyphens"
    return None


def _validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return "Password must contain at least one digit"
    return None


def _lazy_limit(limit_string):
    """Lazy rate-limit decorator that imports limiter at call time to avoid circular imports.

    Respects RATELIMIT_ENABLED=False in app config (used to disable rate
    limiting during tests).
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import current_app
            from app import limiter
            if not current_app.config.get('RATELIMIT_ENABLED', True):
                return f(*args, **kwargs)
            return limiter.limit(limit_string)(f)(*args, **kwargs)
        return wrapper
    return decorator


class UserRegistration(Resource):
    decorators = [_lazy_limit("3/hour")]

    def post(self):
        """Register a new user.

        Validates password strength, checks for duplicate usernames, hashes
        the password, and persists the user document to MongoDB.

        Returns:
            tuple: A dict with a success message and HTTP 201 on success, or a
            dict with an error message and the appropriate HTTP status code on
            failure.
        """
        data = user_parser.parse_args()
        username = data['username'].strip()
        password = data['password']

        error = _validate_username(username)
        if error:
            return {'message': error}, 400

        error = _validate_password(password)
        if error:
            return {'message': error}, 400

        try:
            db = get_db()
            users = db['users']

            if users.find_one({'username': username}):
                return {'message': 'Username already exists'}, 409

            password_hash = generate_password_hash(password)
            users.insert_one({'username': username, 'password': password_hash})

            logger.info("Registered new user: %s", username)
            return {'message': 'User registered successfully'}, 201

        except Exception as e:
            logger.error("Error during registration for user %s: %s", username, e)
            return {'message': 'Registration failed due to a server error'}, 500


class UserLogin(Resource):
    decorators = [_lazy_limit("5/minute")]

    def post(self):
        """Authenticate a user and return a JWT access token.

        Parses username and password from the request, looks up the user in
        MongoDB, and verifies the password hash. Returns a signed JWT on
        success.

        Returns:
            tuple: A dict containing the ``access_token`` and HTTP 200 on
            success, or a dict with an error message and the appropriate HTTP
            status code on failure.
        """
        data = user_parser.parse_args()
        username = data['username']
        password = data['password']

        try:
            db = get_db()
            user = db['users'].find_one({'username': username})

            if not user or not check_password_hash(user['password'], password):
                return {'message': 'Invalid username or password'}, 401

            access_token = create_access_token(identity=username)
            logger.info("Successful login for user: %s", username)
            return {'access_token': access_token}, 200

        except Exception as e:
            logger.error("Error during login for user %s: %s", username, e)
            return {'message': 'Login failed due to a server error'}, 500


class UserLogout(Resource):
    @jwt_required()
    def post(self):
        """Log out the current user by revoking the JWT token.

        Requires a valid JWT. The token's jti claim is added to the in-memory
        blocklist so subsequent requests with the same token are rejected.

        Returns:
            tuple: A dict with a logout confirmation message and HTTP 200.
        """
        claims = get_jwt()
        jti = claims['jti']
        add_token_to_blocklist(jti)
        logger.info("User logged out, jti=%s", jti)
        return {'message': 'User logged out successfully'}, 200
