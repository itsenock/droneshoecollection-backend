from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import os

# MongoDB Connection
client = MongoClient(os.getenv('MONGO_URI', 'mongodb+srv://droneshoecollection:38633351$@cluster0.1ayy7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
db = client['user_database']

# Admin User Details
admin_user = {
    "fullname": "Admin User",
    "email": "mutetienock43@gmail.com",
    "phone_number": "112587164",
    "password": generate_password_hash("2467"),  # Replace with your secure password
    "role": "admin"
}

# Insert Admin User
result = db.users.insert_one(admin_user)

if result.inserted_id:
    print(f"Admin user successfully added with ID: {result.inserted_id}")
else:
    print("Failed to add admin user.")
