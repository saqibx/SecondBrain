"""
SecondBrain - AI-powered research and email drafting agent
Main Flask application with production-ready configuration
"""

import os
import sys
import io
import uuid
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, session, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from dotenv import load_dotenv

from config import Config
from logging_config import setup_logging, get_logger
from utils import (
    error_response,
    success_response,
    handle_options_request,
    require_auth,
    safe_api_call,
    validate_json,
)
from Classes.Users import User
from Classes.ChromaDBHandler import ChromaDBHandler
from Agents.AgentMain import app as agent_app, AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Load environment variables
load_dotenv()

# Setup logging
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)
from config get get_config
# Get configuration
config = get_config()

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config)
import redis as redis_lib

if config.SESSION_TYPE == "redis":
    app.config["SESSION_REDIS"] = redis_lib.from_url(config.REDIS_URL)

# Initialize session
import redis
from flask_session import Session

app.config.from_object(Config)

if app.config["SESSION_TYPE"] == "redis":
    app.config["SESSION_REDIS"] = redis.from_url(app.config["REDIS_URL"])

Session(app)


# Initialize CORS with dynamic origins from config
CORS(
    app,
    origins=config.ALLOWED_ORIGINS,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.RATELIMIT_DEFAULT] if config.RATELIMIT_ENABLED else [],
    storage_uri=config.REDIS_URL if config.RATELIMIT_ENABLED else None,
)

logger.info(f"SecondBrain initialized in {os.getenv('FLASK_ENV', 'development')} mode")
logger.info(f"CORS allowed origins: {config.ALLOWED_ORIGINS}")


# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    return error_response(
        "Too many requests. Please try again later.",
        status_code=429,
        error_code="RATE_LIMIT_EXCEEDED"
    )


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return error_response(
        "Endpoint not found",
        status_code=404,
        error_code="NOT_FOUND"
    )


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {e}", exc_info=True)
    return error_response(
        "Internal server error",
        status_code=500,
        error_code="INTERNAL_ERROR"
    )


# Health check endpoint
@app.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint for load balancers and monitoring"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Check MongoDB connection
        try:
            from pymongo import MongoClient
            client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = f"disconnected: {str(e)}"
            health_status["status"] = "degraded"
            logger.warning(f"Health check: database disconnected - {e}")
        
        # Check Redis connection
        try:
            import redis
            r = redis.from_url(config.REDIS_URL, socket_connect_timeout=5)
            r.ping()
            health_status["redis"] = "connected"
        except Exception as e:
            health_status["redis"] = f"disconnected: {str(e)}"
            logger.warning(f"Health check: redis disconnected - {e}")
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return success_response(data=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return error_response("Health check failed", status_code=500)


# Authentication endpoints
@app.route('/api/v1/login', methods=['POST', 'OPTIONS'])
@safe_api_call
@limiter.limit(config.RATELIMIT_LOGIN)
def login():
    """User login endpoint"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    data = request.get_json()
    
    if not data:
        return error_response("No data provided", status_code=400, error_code="NO_DATA")
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return error_response(
            "Username and password are required",
            status_code=400,
            error_code="MISSING_CREDENTIALS"
        )
    
    # Get user from database
    user = User.get_user(username=username)
    
    if not user:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return error_response("Invalid credentials", status_code=401, error_code="AUTH_FAILED")
    
    # Verify password
    if not user.verify_password(password):
        logger.warning(f"Failed login attempt for user: {username}")
        return error_response("Invalid credentials", status_code=401, error_code="AUTH_FAILED")
    
    # Update last login
    user.update_last_login()
    
    # Set session
    session['admin'] = True
    session['username'] = username
    session['user_id'] = user.user_id
    session.modified = True
    
    logger.info(f"User logged in successfully: {username}")
    
    return success_response(
        data={"user_id": user.user_id, "username": username},
        message="Login successful",
        status_code=200
    )


@app.route('/api/v1/logout', methods=['POST', 'OPTIONS'])
@safe_api_call
def logout():
    """User logout endpoint"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    username = session.get('username', 'unknown')
    session.clear()
    
    logger.info(f"User logged out: {username}")
    return success_response(message="Logged out successfully", status_code=200)


@app.route('/api/v1/register', methods=['POST', 'OPTIONS'])
@safe_api_call
@limiter.limit(config.RATELIMIT_REGISTER)
def register():
    """User registration endpoint"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    data = request.get_json()
    
    if not data:
        return error_response("No data provided", status_code=400, error_code="NO_DATA")
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return error_response(
            "Username and password are required",
            status_code=400,
            error_code="MISSING_CREDENTIALS"
        )
    
    # Validate password length
    if len(password) < config.PASSWORD_MIN_LENGTH:
        return error_response(
            f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters long",
            status_code=400,
            error_code="WEAK_PASSWORD"
        )
    
    # Validate username format (alphanumeric and underscore only)
    import re
    if not re.match(r'^[a-zA-Z0-9_]{3,32}$', username):
        return error_response(
            "Username must be 3-32 characters and contain only letters, numbers, and underscores",
            status_code=400,
            error_code="INVALID_USERNAME"
        )
    
    # Check if user exists
    existing_user = User.get_user(username=username)
    if existing_user:
        logger.warning(f"Registration attempt for existing user: {username}")
        return error_response("Username already exists", status_code=409, error_code="USER_EXISTS")
    
    # Create new user
    new_user = User(
        user_id=str(uuid.uuid4()),
        username=username,
        plain_password=password,
        already_hashed=False
    )
    
    success, message = new_user.set_user()
    
    if not success:
        logger.error(f"Failed to create user {username}: {message}")
        return error_response(message, status_code=500, error_code="REGISTRATION_FAILED")
    
    # Auto-login after registration
    session['admin'] = True
    session['username'] = username
    session['user_id'] = new_user.user_id
    session['agent_state'] = {
        'messages': [],
        'research_draft': '',
        'email_draft': '',
        'conversation_history': []
    }
    session.modified = True
    
    logger.info(f"New user registered: {username}")
    
    return success_response(
        data={"user_id": new_user.user_id, "username": username},
        message="Registration successful",
        status_code=201
    )


@app.route('/api/v1/auth/status', methods=['GET', 'OPTIONS'])
def auth_status():
    """Check authentication status"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    is_authenticated = session.get("admin", False)
    
    response_data = {
        "authenticated": is_authenticated,
        "username": session.get("username") if is_authenticated else None
    }
    
    return success_response(data=response_data, status_code=200)


# Chat endpoint
@app.route('/api/v1/chat', methods=['POST', 'OPTIONS'])
@safe_api_call
@limiter.limit(config.RATELIMIT_CHAT)
@require_auth
def chat():
    """Chat with the AI agent"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    data = request.get_json()
    
    if not data or 'message' not in data:
        return error_response("No message provided", status_code=400, error_code="NO_MESSAGE")
    
    user_input = data.get('message', '').strip()
    
    if not user_input:
        return error_response("Message cannot be empty", status_code=400, error_code="EMPTY_MESSAGE")
    
    try:
        # Initialize agent state if needed
        if 'agent_state' not in session:
            session['agent_state'] = {
                'messages': [],
                'research_draft': '',
                'email_draft': '',
                'conversation_history': []
            }
        
        # Prepare messages for agent
        agent_messages = []
        for msg in session['agent_state']['messages']:
            if msg['type'] == 'human':
                agent_messages.append(HumanMessage(content=msg['content']))
            elif msg['type'] == 'ai':
                agent_messages.append(AIMessage(content=msg['content']))
        
        agent_messages.append(HumanMessage(content=user_input))
        
        # Create state for agent
        state = {
            "messages": agent_messages,
            "research_draft": session['agent_state']['research_draft'],
            "email_draft": session['agent_state']['email_draft']
        }
        
        # Capture agent output
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            final_state = agent_app.invoke(state)
        finally:
            sys.stdout = sys.__stdout__
        
        agent_response = captured_output.getvalue()
        
        # Update session state
        if final_state:
            session['agent_state']['research_draft'] = final_state.get('research_draft', '')
            session['agent_state']['email_draft'] = final_state.get('email_draft', '')
            
            # Serialize messages
            serializable_messages = []
            for msg in final_state.get('messages', []):
                if isinstance(msg, HumanMessage):
                    serializable_messages.append({'type': 'human', 'content': msg.content})
                elif isinstance(msg, AIMessage):
                    serializable_messages.append({'type': 'ai', 'content': msg.content})
            
            session['agent_state']['messages'] = serializable_messages
            
            # Store conversation
            conversation_entry = {
                'user': user_input,
                'agent': agent_response,
                'research': final_state.get('research_draft', ''),
                'email': final_state.get('email_draft', ''),
                'timestamp': int(datetime.utcnow().timestamp())
            }
            session['agent_state']['conversation_history'].append(conversation_entry)
        
        session.modified = True
        
        logger.info(f"Chat processed for user: {session.get('username')}")
        
        return success_response(
            data={
                "response": agent_response,
                "agent_state": {
                    "research_draft": session['agent_state']['research_draft'],
                    "email_draft": session['agent_state']['email_draft'],
                    "messages_count": len(session['agent_state']['messages']),
                }
            },
            message="Chat processed successfully",
            status_code=200
        )
        
    except Exception as e:
        sys.stdout = sys.__stdout__
        logger.error(f"Chat error: {e}", exc_info=True)
        return error_response(
            "Failed to process chat message",
            status_code=500,
            error_code="CHAT_ERROR"
        )


@app.route('/api/v1/state', methods=['GET', 'OPTIONS'])
@safe_api_call
@require_auth
def get_state():
    """Get current agent state"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    if 'agent_state' not in session:
        session['agent_state'] = {
            'messages': [],
            'research_draft': '',
            'email_draft': '',
            'conversation_history': []
        }
    
    return success_response(
        data={
            "research_draft": session['agent_state']['research_draft'],
            "email_draft": session['agent_state']['email_draft'],
            "messages_count": len(session['agent_state']['messages']),
        },
        status_code=200
    )


@app.route('/api/v1/clear', methods=['POST', 'OPTIONS'])
@safe_api_call
@require_auth
def clear_session_state():
    """Clear the agent session"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    if 'agent_state' in session:
        del session['agent_state']
    session.modified = True
    
    logger.info(f"Session cleared for user: {session.get('username')}")
    return success_response(message="Session cleared successfully", status_code=200)


# API root endpoint
@app.route('/api/v1', methods=['GET', 'OPTIONS'])
def api_root():
    """API root endpoint with documentation"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    return success_response(
        data={
            "name": "SecondBrain API",
            "version": "1.0.0",
            "description": "AI-powered research and email drafting agent",
            "endpoints": {
                "auth": {
                    "POST /api/v1/login": "Login with username/password",
                    "POST /api/v1/logout": "Logout current user",
                    "POST /api/v1/register": "Register new account",
                    "GET /api/v1/auth/status": "Check authentication status",
                },
                "agent": {
                    "POST /api/v1/chat": "Send message to agent",
                    "GET /api/v1/state": "Get current agent state",
                    "POST /api/v1/clear": "Clear agent session",
                },
                "health": {
                    "GET /health": "Health check endpoint",
                }
            }
        },
        status_code=200
    )


@app.route('/', methods=['GET', 'OPTIONS'])
def index():
    """Root endpoint"""
    if request.method == 'OPTIONS':
        return handle_options_request()
    
    return success_response(
        data={"message": "SecondBrain API - See /api/v1 for documentation"},
        status_code=200
    )


# Request/Response logging middleware
@app.before_request
def log_request():
    """Log incoming requests"""
    if not request.path.startswith('/health'):
        logger.debug(
            f"{request.method} {request.path}",
            extra={
                "remote_addr": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", "unknown")
            }
        )


@app.after_request
def log_response(response):
    """Log outgoing responses"""
    if not request.path.startswith('/health'):
        logger.debug(
            f"Response: {response.status_code} for {request.method} {request.path}"
        )
    return response


if __name__ == '__main__':
    host = config.HOST
    port = config.PORT
    debug = config.DEBUG
    
    logger.info(f"Starting SecondBrain on {host}:{port}")
    
    app.run(host=host, port=port, debug=debug, use_reloader=debug)
