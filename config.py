import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_flask_secret_key')
    MONGO_URI = os.environ.get('mongodb+srv://droneshoecollection:38633351$@cluster0.1ayy7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')  # MongoDB URI
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your_jwt_secret_key')
