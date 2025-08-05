import os
import bcrypt
import jwt  # <-- This is PyJWT, NOT google.auth.jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGODB_CLIENT")]
collection = db[os.getenv("MONGODB_COLLECTION")]

class User:


    def __init__(self, user_id: str, username: str, plain_password: str,already_hashed:bool):
        self.user_id = user_id
        self.username = username
        self.password = plain_password if already_hashed else self.hash_password(plain_password)

        self.chroma_name = username



    def hash_password(self, plain_text: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain_text.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, input_password: str) -> bool:
        return bcrypt.checkpw(input_password.encode('utf-8'), self.password.encode('utf-8'))

    def generate_jwt(self) -> str:
        payload = {
            "sub": self.user_id,
            "username": self.username,
            "exp": datetime.utcnow() + timedelta(hours=12)
        }
        return jwt.encode(payload, os.getenv("APP_SECRET_KEY"), algorithm="HS256")

    @staticmethod
    def get_user(username):
        user = collection.find_one({"username": username})
        if user:
            return User(
                user_id=user.get("user_id"),
                username=user.get("username"),
                plain_password=user.get("password"),  # still called plain_password for compatibility
                already_hashed=True
            )
        return None

    def set_user(self):
        user_json = {
            "user_id": self.user_id,
            "username": self.username,
            "password": self.password
        }

        collection.insert_one(user_json)
        return "Finished Pushing To DB"



#
# man = User("1224","jack","mazhar")
# print(man.password)
# print(man.set_user())
# person = User(username="saqibx").get_user()
# print(person.user_id)

