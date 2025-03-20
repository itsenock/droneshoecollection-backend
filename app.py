from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient, ASCENDING
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime


# Load environment variables
load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

port = int(os.getenv("PORT", 5000))

# MongoDB configuration
client = MongoClient(os.getenv("MONGO_URI"))
db = client["droneshoecollection"]

# Collections
users = db["users"]
items = db["items"]
orders = db["orders"]

# Indexes
users.create_index([("email", ASCENDING)], unique=True)
items.create_index([("sold", ASCENDING)])
orders.create_index([("status", ASCENDING)])

# JWT configuration
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")

# File upload configuration
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Helper function to check if email exists
def email_exists(email):
    return users.find_one({"email": email}) is not None


# Registration route
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    fullname = data.get("fullname")
    email = data.get("email")
    phonenumber = data.get("phonenumber")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    # Validation
    if not fullname or not email or not phonenumber or not password or not confirm_password:
        return jsonify({"message": "All fields are required"}), 400
    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400
    if email_exists(email):
        return jsonify({"message": "Email already registered"}), 400

    # Hash password
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Insert user into database
    users.insert_one({
        "fullname": fullname,
        "email": email,
        "phonenumber": phonenumber,
        "password": hashed_password,
        "role": "user"  # Default role is user
    })

    return jsonify({"message": "User registered successfully"}), 201


# Login route
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    # Find user by email
    user = users.find_one({"email": email})
    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid email or password"}), 401

    # Generate JWT token
    access_token = create_access_token(identity=str(user["_id"]))
    return jsonify({"access_token": access_token}), 200


# Password reset route
@app.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    # Validation
    if not email or not new_password or not confirm_password:
        return jsonify({"message": "All fields are required"}), 400
    if new_password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    # Check if email exists
    user = users.find_one({"email": email})
    if not user:
        return jsonify({"message": "Email not found"}), 404

    # Update password
    hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")
    users.update_one({"_id": user["_id"]}, {"$set": {"password": hashed_password}})
    return jsonify({"message": "Password reset successfully"}), 200


# Profile route (protected)
@app.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Return user details (excluding sensitive information like password)
    return jsonify({
        "fullname": user["fullname"],
        "email": user["email"],
        "phonenumber": user["phonenumber"]
    }), 200


# Admin account creation route (protected)
@app.route("/admin/create-admin", methods=["POST"])
@jwt_required()
def create_admin():
    user_id = get_jwt_identity()
    current_user = users.find_one({"_id": ObjectId(user_id)})
    if current_user["role"] != "admin":
        return jsonify({"message": "Only admins can create new admin accounts"}), 403

    data = request.get_json()
    fullname = data.get("fullname")
    email = data.get("email")
    phonenumber = data.get("phonenumber")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    # Validation
    if not fullname or not email or not phonenumber or not password or not confirm_password:
        return jsonify({"message": "All fields are required"}), 400
    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400
    if email_exists(email):
        return jsonify({"message": "Email already registered"}), 400

    # Hash password
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Insert admin into database
    users.insert_one({
        "fullname": fullname,
        "email": email,
        "phonenumber": phonenumber,
        "password": hashed_password,
        "role": "admin"
    })

    return jsonify({"message": "Admin account created successfully"}), 201


# Admin route to add items (protected)
@app.route("/admin/add-item", methods=["POST"])
@jwt_required()
def add_item():
    user_id = get_jwt_identity()
    user = users.find_one({"_id": ObjectId(user_id)})
    if user["role"] != "admin":
        return jsonify({"message": "Admin access required"}), 403

    # Parse form data
    name = request.form.get("name")
    description = request.form.get("description")
    price = request.form.get("price")
    image = request.files.get("image")

    # Validation
    if not name or not description or not price or not image:
        return jsonify({"message": "All fields are required"}), 400

    # Save image
    filename = secure_filename(image.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    image.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_filename))

    # Insert item into database
    items.insert_one({
        "name": name,
        "description": description,
        "price": float(price),
        "image_url": f"/uploads/{unique_filename}",
        "sold": False  # Initially unsold
    })

    return jsonify({"message": "Item added successfully"}), 201


# Route for users to make orders (protected)
@app.route("/order", methods=["POST"])
@jwt_required()
def make_order():
    user_id = get_jwt_identity()
    data = request.get_json()
    item_id = data.get("item_id")
    quantity = data.get("quantity")
    location = data.get("location")  # Delivery location

    # Validation
    if not item_id or not quantity or not location:
        return jsonify({"message": "Item ID, quantity, and location are required"}), 400

    # Check if item exists and is unsold
    item = items.find_one({"_id": ObjectId(item_id), "sold": False})
    if not item:
        return jsonify({"message": "Item not available for purchase"}), 404

    # Mark item as sold
    items.update_one({"_id": ObjectId(item_id)}, {"$set": {"sold": True}})

    # Create order
    order = {
        "user_id": ObjectId(user_id),
        "item_id": ObjectId(item_id),
        "quantity": quantity,
        "total_price": item["price"] * quantity,
        "location": location,
        "status": "unpaid",  # Initial payment status
        "ordered_at": datetime.utcnow()  # Timestamp of order placement
    }
    orders.insert_one(order)

    return jsonify({"message": "Order placed successfully"}), 201


# Route to update payment status (protected)
@app.route("/order/<order_id>/pay", methods=["POST"])
@jwt_required()
def pay_order(order_id):
    user_id = get_jwt_identity()

    # Find the order by ID and ensure it belongs to the user
    order = orders.find_one({"_id": ObjectId(order_id), "user_id": ObjectId(user_id)})
    if not order:
        return jsonify({"message": "Order not found or unauthorized"}), 404

    # Update payment status to "paid"
    orders.update_one({"_id": ObjectId(order_id)}, {"$set": {"status": "paid"}})
    return jsonify({"message": "Payment confirmed successfully"}), 200


# User route to view order history (protected)
@app.route("/orders", methods=["GET"])
@jwt_required()
def user_orders():
    user_id = get_jwt_identity()

    # Fetch all orders for the user
    user_orders = list(orders.aggregate([
        {
            "$match": {"user_id": ObjectId(user_id)}
        },
        {
            "$lookup": {
                "from": "items",
                "localField": "item_id",
                "foreignField": "_id",
                "as": "item_details"
            }
        },
        {
            "$project": {
                "item_name": {"$arrayElemAt": ["$item_details.name", 0]},
                "quantity": 1,
                "total_price": 1,
                "location": 1,
                "status": 1,
                "ordered_at": 1
            }
        }
    ]))

    return jsonify({"orders": user_orders}), 200


# Admin route to view all orders (protected)
@app.route("/admin/orders", methods=["GET"])
@jwt_required()
def admin_view_orders():
    user_id = get_jwt_identity()
    user = users.find_one({"_id": ObjectId(user_id)})
    if user["role"] != "admin":
        return jsonify({"message": "Admin access required"}), 403

    # Fetch all orders with user and item details
    all_orders = list(orders.aggregate([
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_details"
            }
        },
        {
            "$lookup": {
                "from": "items",
                "localField": "item_id",
                "foreignField": "_id",
                "as": "item_details"
            }
        },
        {
            "$project": {
                "user_fullname": {"$arrayElemAt": ["$user_details.fullname", 0]},
                "user_email": {"$arrayElemAt": ["$user_details.email", 0]},
                "item_name": {"$arrayElemAt": ["$item_details.name", 0]},
                "quantity": 1,
                "total_price": 1,
                "location": 1,
                "status": 1,
                "ordered_at": 1
            }
        }
    ]))

    return jsonify({"orders": all_orders}), 200


# Admin route to filter orders by payment status (protected)
@app.route("/admin/orders/<status>", methods=["GET"])
@jwt_required()
def admin_filter_orders(status):
    user_id = get_jwt_identity()
    user = users.find_one({"_id": ObjectId(user_id)})
    if user["role"] != "admin":
        return jsonify({"message": "Admin access required"}), 403

    if status not in ["paid", "unpaid"]:
        return jsonify({"message": "Invalid status"}), 400

    # Fetch filtered orders
    filtered_orders = list(orders.aggregate([
        {
            "$match": {"status": status}
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_details"
            }
        },
        {
            "$lookup": {
                "from": "items",
                "localField": "item_id",
                "foreignField": "_id",
                "as": "item_details"
            }
        },
        {
            "$project": {
                "user_fullname": {"$arrayElemAt": ["$user_details.fullname", 0]},
                "user_email": {"$arrayElemAt": ["$user_details.email", 0]},
                "item_name": {"$arrayElemAt": ["$item_details.name", 0]},
                "quantity": 1,
                "total_price": 1,
                "location": 1,
                "status": 1,
                "ordered_at": 1
            }
        }
    ]))

    return jsonify({"orders": filtered_orders}), 200


# Admin route to view sold/unsold items (protected)
@app.route("/admin/items/<status>", methods=["GET"])
@jwt_required()
def admin_view_items(status):
    user_id = get_jwt_identity()
    user = users.find_one({"_id": ObjectId(user_id)})
    if user["role"] != "admin":
        return jsonify({"message": "Admin access required"}), 403

    if status not in ["sold", "unsold"]:
        return jsonify({"message": "Invalid status"}), 400

    # Fetch items based on sold status
    sold_status = True if status == "sold" else False
    items_list = list(items.find({"sold": sold_status}))

    return jsonify({"items": items_list}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=port, debug=True)