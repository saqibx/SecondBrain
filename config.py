"""
Configuration management for SecondBrain application.
Supports development, staging, and production environments.
"""

import os
from datetime import timedelta
from typing import List


class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False
    
    # Session
    SESSION_TYPE = os.getenv("SESSION_TYPE", "redis")
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_REFRESH_EACH_REQUEST = True

    # Session cookies for cross-site requests (required for frontend on different domain)
    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "None")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True  # Security: prevent JavaScript access to session cookie
    SESSION_USE_SIGNER = True  # Security: sign session cookies
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
    MONGODB_CLIENT = os.getenv("MONGODB_CLIENT", "secondbrain")
    MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "users")
    
    # CORS
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080").split(",")
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    # LLM Models
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
    
    # Rate Limiting
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "100/hour")
    RATELIMIT_LOGIN = os.getenv("RATELIMIT_LOGIN", "5/minute")
    RATELIMIT_REGISTER = os.getenv("RATELIMIT_REGISTER", "3/hour")
    RATELIMIT_CHAT = os.getenv("RATELIMIT_CHAT", "30/minute")
    
    # File Upload
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB in bytes
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "DATA")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Security
    PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    ACCOUNT_LOCKOUT_DURATION = int(os.getenv("ACCOUNT_LOCKOUT_DURATION", "900"))  # 15 minutes
    
    # ChromaDB
    CHROMA_DIR = os.getenv("CHROMA_DIR", "Classes/chroma_db")
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5895"))
    
    # API
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
    
    @staticmethod
    def validate_required_vars():
        """Validate that all required environment variables are set"""
        required_vars = {
            "APP_SECRET_KEY": "Flask session secret key",
            "MONGO_URI": "MongoDB connection string",
            "MONGODB_CLIENT": "MongoDB database name",
            "MONGODB_COLLECTION": "MongoDB collection name",
            "OPENAI_API_KEY": "OpenAI API key for LLM",
            "TAVILY_API_KEY": "Tavily API key for research",
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables:\n" + 
                "\n".join(f"  - {var}" for var in missing_vars) +
                f"\n\nPlease set these variables in your .env file or environment."
            )


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    SESSION_TYPE = "filesystem"  # Use filesystem for easier local testing
    TESTING = False
    RATELIMIT_ENABLED = False  # Disable rate limiting in dev


class StagingConfig(Config):
    """Staging environment configuration"""
    DEBUG = False
    TESTING = False
    SESSION_TYPE = "redis"


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False
    SESSION_TYPE = "redis"
    # In production, CORS must be explicitly configured
    # ALLOWED_ORIGINS should be set via environment variable


class TestingConfig(Config):
    """Testing environment configuration"""
    DEBUG = True
    TESTING = True
    SESSION_TYPE = "filesystem"
    RATELIMIT_ENABLED = False
    # Use in-memory or test database
    MONGO_URI = "mongodb://localhost:27017"
    MONGODB_CLIENT = "secondbrain_test"


def get_config():
    """Get configuration based on environment"""
    env = os.getenv("FLASK_ENV", "development").lower()
    
    configs = {
        "development": DevelopmentConfig,
        "staging": StagingConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    
    config_class = configs.get(env, DevelopmentConfig)
    
    # Validate in non-test environments
    if env != "testing":
        config_class.validate_required_vars()
    
    return config_class
