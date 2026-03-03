from flask_restful import Resource, reqparse
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from utils.database import get_db
import logging

logger = logging.getLogger(__name__)

user_parser = reqparse.RequestParser()
user_parser.add_argument('username', type=str, required=True, help="Username cannot be blank")
user_parser.add_argument('password', type=str, required=True, help="Password cannot be blank")


class UserRegistration(Resource):
    def post(self):
        """Register a new user.

        Parses username and password from the request, checks for duplicate
        usernames, hashes the password, and persists the user document to the
        'users' MongoDB collection.

        Returns:
            tuple: A dict with a success message and HTTP 201 on success, or a
            dict with an error message and the appropriate HTTP status code on
            failure.
        """
        data = user_parser.parse_args()
        username = data['username']
        password = data['password']

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
        """Log out the current user.

        Requires a valid JWT. The token claims are retrieved via ``get_jwt()``
        to support future blocklist integration. Returns a success message.

        Returns:
            tuple: A dict with a logout confirmation message and HTTP 200.
        """
        claims = get_jwt()
        logger.info("User logged out, jti=%s", claims.get('jti'))
        return {'message': 'User logged out successfully'}, 200
