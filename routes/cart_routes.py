# blueprints/cart.py
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, jwt

cart_bp = Blueprint('cart_bp', __name__)
client = MongoClient(os.getenv('MONGO_URI', 'mongodb+srv://droneshoecollection:38633351$@cluster0.1ayy7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
db = client['user_database']
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key')

def decode_token(token):
    try:
        token = token.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except Exception as e:
        print("Token decoding error in cart:", e)
        return None

@cart_bp.route('/user/cart', methods=['GET'])
def get_user_cart():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token!'}), 401
    cart_items = list(db.cart.find({'user_id': ObjectId(payload['user_id'])}))
    for item in cart_items:
        product = db.items.find_one({'_id': ObjectId(item['product_id'])})
        if product:
            item['available'] = product.get('available', True)
            item['price'] = product.get('price')
            item['name'] = product.get('name')
            item['images'] = product.get('images')
        else:
            item['available'] = False
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
        item['product_id'] = str(item['product_id'])
    return jsonify(cart_items), 200

@cart_bp.route('/user/cart', methods=['POST'])
def add_to_cart():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token!'}), 401
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided.'}), 400
    existing = db.cart.find_one({
        'user_id': ObjectId(payload['user_id']),
        'product_id': ObjectId(data['product_id'])
    })
    if existing:
        return jsonify({'error': 'Item already in cart.'}), 400
    cart_item = {
        'user_id': ObjectId(payload['user_id']),
        'product_id': ObjectId(data['product_id']),
        'quantity': data.get('quantity', 1)
    }
    result = db.cart.insert_one(cart_item)
    cart_item['_id'] = str(result.inserted_id)
    cart_item['user_id'] = str(cart_item['user_id'])
    cart_item['product_id'] = str(cart_item['product_id'])
    return jsonify(cart_item), 201

@cart_bp.route('/user/cart/<item_id>', methods=['PUT'])
def update_cart_item(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token!'}), 401
    data = request.get_json()
    new_quantity = data.get('quantity')
    if not new_quantity or new_quantity <= 0:
        return jsonify({'error': 'Invalid quantity.'}), 400
    result = db.cart.update_one(
        {'_id': ObjectId(item_id), 'user_id': ObjectId(payload['user_id'])},
        {'$set': {'quantity': new_quantity}}
    )
    if result.matched_count == 0:
        return jsonify({'error': 'Cart item not found.'}), 404
    return jsonify({'message': 'Cart updated.'}), 200

@cart_bp.route('/user/cart/<item_id>', methods=['DELETE'])
def remove_from_cart(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token!'}), 401
    result = db.cart.delete_one({
        '_id': ObjectId(item_id),
        'user_id': ObjectId(payload['user_id'])
    })
    if result.deleted_count == 0:
        return jsonify({'error': 'Cart item not found.'}), 404
    return jsonify({'message': 'Item removed from cart.'}), 200

@cart_bp.route('/user/cart', methods=['DELETE'])
def clear_cart():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token!'}), 401
    db.cart.delete_many({'user_id': ObjectId(payload['user_id'])})
    return jsonify({'message': 'Cart cleared.'}), 200

@cart_bp.route('/user/wishlist', methods=['GET'])
def get_wishlist():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token!'}), 401
    wishlist_items = list(db.wishlist.find({'user_id': ObjectId(payload['user_id'])}))
    for item in wishlist_items:
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
        item['product_id'] = str(item['product_id'])
    return jsonify(wishlist_items), 200

@cart_bp.route('/user/wishlist', methods=['POST'])
def add_to_wishlist():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token!'}), 401
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided.'}), 400
    existing = db.wishlist.find_one({
        'user_id': ObjectId(payload['user_id']),
        'product_id': ObjectId(data['product_id'])
    })
    if existing:
        return jsonify({'error': 'Item already in wishlist.'}), 400
    wishlist_item = {
        'user_id': ObjectId(payload['user_id']),
        'product_id': ObjectId(data['product_id'])
    }
    result = db.wishlist.insert_one(wishlist_item)
    wishlist_item['_id'] = str(result.inserted_id)
    wishlist_item['user_id'] = str(wishlist_item['user_id'])
    wishlist_item['product_id'] = str(wishlist_item['product_id'])
    return jsonify(wishlist_item), 201

@cart_bp.route('/user/wishlist/<item_id>', methods=['DELETE'])
def remove_from_wishlist(item_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing!'}), 401
    payload = decode_token(token)
    if not payload:
        return jsonify({'error': 'Invalid token!'}), 401
    result = db.wishlist.delete_one({
        '_id': ObjectId(item_id),
        'user_id': ObjectId(payload['user_id'])
    })
    if result.deleted_count == 0:
        return jsonify({'error': 'Wishlist item not found.'}), 404
    return jsonify({'message': 'Item removed from wishlist.'}), 200
