from flask import Blueprint, request, jsonify, send_from_directory
from bson.objectid import ObjectId
from pymongo import MongoClient
import os, jwt
from werkzeug.utils import secure_filename

item_bp = Blueprint('item_bp', __name__)
client = MongoClient(os.getenv('MONGO_URI', 'mongodb+srv://droneshoecollection:38633351$@cluster0.1ayy7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
db = client['user_database']

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key')
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def decode_token(token):
    try:
        token = token.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except Exception as e:
        print("Token decoding error in items:", e)
        return None

def verify_admin(token):
    payload = decode_token(token)
    if not payload:
        return None
    user = db.users.find_one({'_id': ObjectId(payload['user_id'])})
    if user and user.get('role') == 'admin':
        return user
    return None

@item_bp.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@item_bp.route('/user/item', methods=['POST'])
def save_item():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    admin = verify_admin(token)
    if not admin:
        return jsonify({'error': 'Unauthorized. Admins only.'}), 403
    data = request.form.to_dict()
    images = request.files.getlist('images')
    image_paths = []
    for image in images:
        filename = secure_filename(image.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        image.save(image_path)
        image_paths.append(f'/uploads/{filename}')
    # Save the item with gender applied properly
    item = {
        'user_id': admin['_id'],
        'name': data.get('name'),
        'brand': data.get('brand'),
        'size': data.get('size'),
        'color': data.get('color'),
        'description': data.get('description'),
        'price': data.get('price'),
        'category': data.get('category'),
        'gender': data.get('gender', 'both'),  # Default to 'both' if gender is not provided
        'images': image_paths,
    }
    result = db.items.insert_one(item)
    item['_id'] = str(result.inserted_id)
    item['user_id'] = str(item['user_id'])
    return jsonify(item), 201

@item_bp.route('/user/items', methods=['GET'])
def get_user_items():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token.'}), 401
    items = list(db.items.find({'user_id': ObjectId(payload['user_id'])}))
    for item in items:
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
    return jsonify(items), 200

@item_bp.route('/products', methods=['GET'])
def get_products():
    # Handle gender filtering if query parameter is provided
    gender_filter = request.args.get('gender')
    query = {'is_sold': {'$ne': True}}
    if gender_filter and gender_filter.lower() in ['male', 'female', 'both']:
        query['gender'] = gender_filter.lower()

    items = list(db.items.find(query))
    for item in items:
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
    return jsonify(items), 200

@item_bp.route('/product/<item_id>', methods=['GET'])
def get_product(item_id):
    try:
        item = db.items.find_one({'_id': ObjectId(item_id)})
        if not item:
            return jsonify({'error': 'Product not found.'}), 404
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
        return jsonify(item), 200
    except Exception as e:
        return jsonify({'error': 'Invalid product ID', 'message': str(e)}), 400
