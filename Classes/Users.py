import os
import bcrypt
import jwt
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

load_dotenv()

logger = logging.getLogger(__name__)

# MongoDB connection with error handling
try:
    client = MongoClient(
        os.getenv("MONGO_URI"),
        serverSelectionTimeoutMS=5000,
        retryWrites=True,
        retryReads=True
    )
    # Test connection
    client.admin.command("ping")
    db = client[os.getenv("MONGODB_CLIENT")]
    collection = db[os.getenv("MONGODB_COLLECTION")]
    # Create unique index on username
    collection.create_index("username", unique=True)
    logger.info("MongoDB connection established successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise


class User:
    """User model with secure password handling and database operations"""
    
    def __init__(
        self,
        user_id: str = "",
        username: str = "",
        plain_password: str = "",
        already_hashed: bool = False
    ):
        self.user_id = user_id
        self.username = username
        self.chroma_name = username
        self.created_at = datetime.utcnow()
        self.last_login = None

        # Handle password properly
        if plain_password and not already_hashed:
            self.password = self.hash_password(plain_password)
        elif plain_password and already_hashed:
            self.password = plain_password
        else:
            self.password = ""

    @staticmethod
    def hash_password(plain_text: str) -> str:
        """Hash password using bcrypt with strong salt"""
        if not plain_text:
            raise ValueError("Password cannot be empty")
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(plain_text.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, input_password: str) -> bool:
        """Verify password against hash"""
        try:
            if not self.password:
                logger.warning(f"Password verification failed: no hash stored for {self.username}")
                return False

            result = bcrypt.checkpw(
                input_password.encode('utf-8'),
                self.password.encode('utf-8')
            )
            
            if not result:
                logger.warning(f"Failed password verification attempt for user: {self.username}")
            
            return result

        except Exception as e:
            logger.error(f"Error in password verification for {self.username}: {e}")
            return False

    def generate_jwt(self, secret_key: str = None, hours: int = 12) -> str:
        """Generate JWT token for user"""
        if secret_key is None:
            secret_key = os.getenv("APP_SECRET_KEY")
        
        if not secret_key:
            raise ValueError("APP_SECRET_KEY not configured")
        
        payload = {
            "sub": self.user_id,
            "username": self.username,
            "exp": datetime.utcnow() + timedelta(hours=hours),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    @staticmethod
    def get_user(username: str):
        """Retrieve user from database by username"""
        try:
            if not username or not isinstance(username, str):
                logger.warning("Invalid username provided to get_user")
                return None

            user_data = collection.find_one({"username": username})

            if not user_data:
                logger.debug(f"User not found: {username}")
                return None

            user = User(
                user_id=user_data.get("user_id", ""),
                username=user_data["username"],
                plain_password="",
                already_hashed=True
            )
            user.password = user_data["password"]
            user.created_at = user_data.get("created_at", datetime.utcnow())
            user.last_login = user_data.get("last_login")

            logger.debug(f"User retrieved from database: {username}")
            return user

        except PyMongoError as e:
            logger.error(f"Database error retrieving user {username}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_user: {e}")
            return None

    def set_user(self) -> tuple[bool, str]:
        """
        Create new user in database.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Validate user data
            if not self.username or not self.password:
                return False, "Username and password are required"

            user_document = {
                "user_id": self.user_id,
                "username": self.username,
                "password": self.password,
                "created_at": self.created_at,
                "last_login": self.last_login,
                "is_active": True
            }

            result = collection.insert_one(user_document)
            logger.info(f"User created successfully: {self.username}")
            return True, "User created successfully"

        except DuplicateKeyError:
            logger.warning(f"Attempt to create duplicate user: {self.username}")
            return False, "Username already exists"
        except PyMongoError as e:
            logger.error(f"Database error creating user: {e}")
            return False, f"Database error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in set_user: {e}")
            return False, f"Error: {str(e)}"

    def update_last_login(self) -> bool:
        """Update last login timestamp for user"""
        try:
            collection.update_one(
                {"username": self.username},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            logger.debug(f"Updated last login for user: {self.username}")
            return True
        except Exception as e:
            logger.error(f"Error updating last login for {self.username}: {e}")
            return False

    def __repr__(self):
        return f"User(user_id='{self.user_id}', username='{self.username}')"



