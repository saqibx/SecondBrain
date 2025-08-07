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
    def __init__(self, user_id: str = "", username: str = "", plain_password: str = "", already_hashed: bool = False):
        self.user_id = user_id
        self.username = username

        # Handle password properly
        if plain_password and not already_hashed:
            self.password = self.hash_password(plain_password)
        elif plain_password and already_hashed:
            self.password = plain_password  # It's already hashed
        else:
            self.password = ""  # Will be set later when loading from DB

        self.chroma_name = username

    def hash_password(self, plain_text: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain_text.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, input_password: str) -> bool:
        try:
            print(f"[DEBUG] Verifying password for user: {self.username}")
            print(f"[DEBUG] Input password: {input_password}")
            print(f"[DEBUG] Stored hash starts with: {self.password[:10]}...")

            # Make sure we have a password hash
            if not self.password:
                print("[DEBUG] No password hash stored")
                return False

            # Verify using bcrypt
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

            # Create User object with the database data
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


# # Test function to help debug your user system
# def test_user_authentication():
#     """Test function to verify your user system works"""
#     try:
#         print("=== Testing User Authentication ===")
#
#         # Test 1: Try to get an existing user
#         test_username = "saqib"  # Replace with an actual username from your DB
#         user = User.get_user(test_username)
#
#         if user:
#             print(f"✓ User found: {user}")
#
#             # Test password verification with a known password
#             test_password = "your_actual_password"  # Replace with actual password
#             is_valid = user.verify_password(test_password)
#             print(f"✓ Password verification: {is_valid}")
#
#             # Test with wrong password
#             wrong_password = "wrongpassword"
#             is_invalid = user.verify_password(wrong_password)
#             print(f"✓ Wrong password verification: {is_invalid}")
#
#         else:
#             print(f"✗ User '{test_username}' not found")
#
#             # Optionally create a test user
#             print("Creating test user...")
#             new_user = User(
#                 user_id="test123",
#                 username="testuser",
#                 plain_password="testpass123",
#                 already_hashed=False
#             )
#             result = new_user.set_user()
#             print(f"✓ Test user created: {result}")
#
#     except Exception as e:
#         print(f"✗ Test error: {e}")
#         import traceback
#         traceback.print_exc()



