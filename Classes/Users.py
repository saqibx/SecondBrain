import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGODB_CLIENT")]
collection = db[os.getenv("MONGODB_COLLECTION")]


class User:
    def __init__(self, user_id: str = "", username: str = "", plain_password: str = "", already_hashed: bool = False):
        self.user_id = user_id
        self.username = username

        # Handle password properly
        if plain_password and not already_hashed:
            self.password = self.hash_password(plain_password)
        elif plain_password and already_hashed:
            self.password = plain_password
        else:
            self.password = ""

        self.chroma_name = username

    def hash_password(self, plain_text: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain_text.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, input_password: str) -> bool:
        try:



            if not self.password:
                print("[DEBUG] No password hash stored")
                return False


            result = bcrypt.checkpw(input_password.encode('utf-8'), self.password.encode('utf-8'))
            print(f"[DEBUG] Password verification result: {result}")
            return result

        except Exception as e:
            print(f"[DEBUG] Error in password verification: {e}")
            return False

    def generate_jwt(self) -> str:
        payload = {
            "sub": self.user_id,
            "username": self.username,
            "exp": datetime.utcnow() + timedelta(hours=12)
        }
        return jwt.encode(payload, os.getenv("APP_SECRET_KEY"), algorithm="HS256")

    @staticmethod
    def get_user(username: str):
        try:
            # print(f"[DEBUG] Searching for user: {username}")
            user = collection.find_one({"username": username})

            if not user:
                print(f"[DEBUG] No user found with username: {username}")
                return None

            # print(f"[DEBUG] User found in database: {user['username']}")


            u = User(
                user_id=user.get("user_id", ""),
                username=user["username"],
                plain_password="",  # Empty since we'll set it manually
                already_hashed=True
            )
            u.password = user["password"]  # Set the hashed password

            # print(f"[DEBUG] Created user object: {u.username}")
            return u

        except Exception as e:
            print(f"[DEBUG] Error in get_user: {e}")
            return None

    def set_user(self):
        try:
            user_json = {
                "user_id": self.user_id,
                "username": self.username,
                "password": self.password
            }

            username_available = True
            try:
                user = collection.find_one({"username": self.username})
                if user:
                    username_available = False
                else:
                    username_available = True
                    result = collection.insert_one(user_json)
                    print(f"[DEBUG] User inserted with ID: {result.inserted_id}")
                    return "Finished Pushing To DB"

            except Exception as e:
                print(f"Error: {e}")
                username_available = False

        except Exception as e:
            print(f"[DEBUG] Error inserting user: {e}")
            return f"Error: {str(e)}"

    def __repr__(self):
        return f"User(user_id='{self.user_id}', username='{self.username}')"



