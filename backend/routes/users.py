from flask_restful import Resource, reqparse
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
import logging

logger = logging.getLogger(__name__)

user_parser = reqparse.RequestParser()
user_parser.add_argument('username', type=str, required=True, help="Username cannot be blank")
user_parser.add_argument('password', type=str, required=True, help="Password cannot be blank")

class UserRegistration(Resource):
    def post(self):
        data = user_parser.parse_args()
        # Simplified user registration (no real storage here)
        return {'message': 'User registered successfully'}, 201

class UserLogin(Resource):
    def post(self):
        data = user_parser.parse_args()
        # Simplified login (no real auth check)
        access_token = create_access_token(identity=data['username'])
        return {'access_token': access_token}, 200

class UserLogout(Resource):
    @jwt_required()
    def post(self):
        return {'message': 'User logged out successfully'}, 200