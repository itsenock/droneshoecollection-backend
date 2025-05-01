from flask import Blueprint, request, jsonify
import os, jwt
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from models.user import User
from pymongo import MongoClient

auth_bp = Blueprint('auth_bp', __name__)
client = MongoClient(os.getenv('MONGO_URI', 'mongodb+srv://droneshoecollection:38633351$@cluster0.1ayy7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
db = client['user_database']

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key')

# Helper function to generate JWT token
def generate_token(user):
    payload = {'user_id': str(user['_id']), 'role': user['role']}
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
    return token

# Helper function to decode JWT token
def decode_token(token):
    try:
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except Exception as e:
        print("Token decoding error:", e)
        return None

# Registration Endpoint
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required_fields = ['fullname', 'email', 'phone_number', 'password', 'confirmPassword']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'All fields are required.'}), 400
    if data['password'] != data['confirmPassword']:
        return jsonify({'error': 'Passwords do not match.'}), 400

    if db.users.find_one({'email': data['email']}):
        return jsonify({'error': 'User with this email already exists.'}), 400

    hashed_password = generate_password_hash(data['password'])
    user = User(data['fullname'], data['email'], data['phone_number'], hashed_password, role='normal')
    result = user.save()
    if not result.inserted_id:
        return jsonify({'error': 'Registration failed.'}), 500

    new_user = db.users.find_one({'_id': result.inserted_id})
    token = generate_token(new_user)
    return jsonify({
        'message': 'Registration successful.',
        'token': token,
        'role': new_user['role'],  # Include the user role in the response
    }), 201

# Login Endpoint
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = db.users.find_one({'email': email})
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid credentials.'}), 401

    token = generate_token(user)
    return jsonify({
        'message': 'Login successful.',
        'token': token,
        'role': user.get('role'),  # Include the user role in the response
    }), 200

# Get Current User Endpoint
@auth_bp.route('/me', methods=['GET'])
def get_me():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(auth_header)
    if not payload:
        return jsonify({'error': 'Invalid token!'}), 401
    user = db.users.find_one({'_id': ObjectId(payload['user_id'])})
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    user['_id'] = str(user['_id'])
    user.pop('password', None)  # Remove sensitive information
    return jsonify(user), 200

# Get All Users Endpoint (Admin-Protected)
@auth_bp.route('/users', methods=['GET'])
def get_all_users():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(auth_header)
    if not payload or payload.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    users = list(db.users.find())
    for user in users:
        user['_id'] = str(user['_id'])
        user.pop('password', None)  # Remove sensitive information
    return jsonify(users), 200
