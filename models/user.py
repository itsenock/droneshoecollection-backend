# models/user.py
import os
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

client = MongoClient(os.getenv('MONGO_URI', 'mongodb+srv://droneshoecollection:38633351$@cluster0.1ayy7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
db = client['user_database']

class User:
    def __init__(self, fullname, email, phone_number, password, role='normal'):
        self.fullname = fullname
        self.email = email
        self.phone_number = phone_number
        self.password = password  # Should be hashed
        self.role = role

    def save(self):
        user_data = {
            'fullname': self.fullname,
            'email': self.email,
            'phone_number': self.phone_number,
            'password': self.password,
            'role': self.role
        }
        result = db.users.insert_one(user_data)
        return result

    @staticmethod
    def find_by_email(email):
        return db.users.find_one({'email': email})

    @staticmethod
    def find_by_id(user_id):
        try:
            return db.users.find_one({'_id': ObjectId(user_id)})
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def verify_password(user, password):
        return check_password_hash(user['password'], password)
