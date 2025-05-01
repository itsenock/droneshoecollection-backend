# blueprints/admin.py
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, jwt, os.path
import os

admin_bp = Blueprint('admin_bp', __name__)
client = MongoClient(os.getenv('MONGO_URI', 'mongodb+srv://droneshoecollection:38633351$@cluster0.1ayy7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
db = client['user_database']
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key')
UPLOAD_FOLDER = 'uploads'

def decode_token(token):
    try:
        token = token.split(" ")[1]  # Remove "Bearer " prefix
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except Exception as e:
        print("Token decoding error (admin):", e)
        return None

def verify_admin(request):
    token = request.headers.get('Authorization')
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user = db.users.find_one({'_id': ObjectId(payload['user_id'])})
    if user and user.get('role') == 'admin':
        return user
    return None

@admin_bp.route('/users', methods=['GET'])
def get_all_users():
    admin = verify_admin(request)
    if not admin:
        return jsonify({'error': 'Unauthorized access.'}), 403
    users = list(db.users.find({}))
    for user in users:
        user['_id'] = str(user['_id'])
        user.pop('password', None)
    return jsonify(users), 200

@admin_bp.route('/orders', methods=['GET'])
def get_all_orders():
    admin = verify_admin(request)
    if not admin:
        return jsonify({'error': 'Unauthorized access.'}), 403
    orders = list(db.orders.find({}).sort('created_at', -1))
    for order in orders:
        order['_id'] = str(order['_id'])
        order['buyer_id'] = str(order['buyer_id'])
        order['seller_id'] = str(order['seller_id'])
        order['item_id'] = str(order['item_id'])
    return jsonify(orders), 200

@admin_bp.route('/items/pending', methods=['GET'])
def get_pending_items():
    admin = verify_admin(request)
    if not admin:
        return jsonify({'error': 'Unauthorized access.'}), 403
    items = list(db.items.find({'status': 'pending'}))
    for item in items:
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
    return jsonify(items), 200

@admin_bp.route('/items/approve/<item_id>', methods=['POST'])
def approve_item(item_id):
    admin = verify_admin(request)
    if not admin:
        return jsonify({'error': 'Unauthorized access.'}), 403
    result = db.items.update_one({'_id': ObjectId(item_id)}, {'$set': {'status': 'approved'}})
    if result.modified_count == 0:
        return jsonify({'error': 'Item approval failed.'}), 400
    return jsonify({'message': 'Item approved successfully.'}), 200

@admin_bp.route('/items/reject/<item_id>', methods=['POST'])
def reject_item(item_id):
    admin = verify_admin(request)
    if not admin:
        return jsonify({'error': 'Unauthorized access.'}), 403
    item = db.items.find_one({'_id': ObjectId(item_id)})
    if not item:
        return jsonify({'error': 'Item not found.'}), 404
    if 'images' in item:
        for image_path in item['images']:
            filepath = os.path.join(UPLOAD_FOLDER, os.path.basename(image_path))
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"Error removing image {filepath}: {e}")
    result = db.items.delete_one({'_id': ObjectId(item_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Item removal failed.'}), 400
    return jsonify({'message': 'Item rejected and removed successfully.'}), 200

@admin_bp.route('/item/<item_id>', methods=['DELETE'])
def remove_item(item_id):
    admin = verify_admin(request)
    if not admin:
        return jsonify({'error': 'Unauthorized access.'}), 403
    item = db.items.find_one({'_id': ObjectId(item_id)})
    if not item:
        return jsonify({'error': 'Item not found.'}), 404
    if 'images' in item:
        for image_path in item['images']:
            filepath = os.path.join(UPLOAD_FOLDER, os.path.basename(image_path))
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"Error removing image {filepath}: {e}")
    result = db.items.delete_one({'_id': ObjectId(item_id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Item removal failed.'}), 400
    return jsonify({'message': 'Item removed successfully.'}), 200
