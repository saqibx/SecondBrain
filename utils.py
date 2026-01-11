"""
Utility functions for error handling, CORS, and decorators.
"""

from flask import jsonify, request
from functools import wraps
from logging_config import get_logger
from typing import Dict, Any, Callable, Tuple

logger = get_logger(__name__)


def get_cors_headers(origin: str = None) -> Dict[str, str]:
    """
    Get CORS headers for response.
    
    Args:
        origin: Allowed origin URL. If None, gets from request
        
    Returns:
        Dictionary of CORS headers
    """
    if origin is None:
        origin = request.headers.get("Origin", "http://localhost:8080")
    
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With"
    }


def error_response(
    message: str,
    status_code: int = 500,
    error_code: str = None,
    details: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_code: Internal error code
        details: Additional error details
        
    Returns:
        Tuple of (response dict, status code)
    """
    response_data = {
        "success": False,
        "error": message,
    }
    
    if error_code:
        response_data["error_code"] = error_code
    
    if details:
        response_data["details"] = details
    
    response = jsonify(response_data)
    
    # Add CORS headers
    for key, value in get_cors_headers().items():
        response.headers[key] = value
    
    logger.warning(
        f"Error response: {message}",
        extra={"status_code": status_code, "error_code": error_code}
    )
    
    return response, status_code


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized success response.
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
        
    Returns:
        Tuple of (response dict, status code)
    """
    response_data = {
        "success": True,
        "message": message,
    }
    
    if data is not None:
        response_data["data"] = data
    
    response = jsonify(response_data)
    
    # Add CORS headers
    for key, value in get_cors_headers().items():
        response.headers[key] = value
    
    return response, status_code


def handle_options_request(allowed_methods: str = "GET, POST, PUT, DELETE, OPTIONS") -> Tuple[Dict[str, str], int]:
    """
    Handle CORS preflight OPTIONS request.
    
    Args:
        allowed_methods: Comma-separated allowed HTTP methods
        
    Returns:
        Tuple of (response dict, status code)
    """
    response = jsonify({"status": "ok"})
    
    cors_headers = get_cors_headers()
    cors_headers["Access-Control-Allow-Methods"] = allowed_methods
    
    for key, value in cors_headers.items():
        response.headers[key] = value
    
    return response, 200


def require_auth(f: Callable) -> Callable:
    """
    Decorator to require authentication via session.

    Usage:
        @app.route('/api/protected', methods=['POST'])
        @require_auth
        def protected_endpoint():
            return {"message": "authenticated"}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session

        # Allow OPTIONS requests to pass through without authentication
        if request.method == "OPTIONS":
            return handle_options_request()

        if not session.get("admin") or not session.get("username"):
            return error_response(
                "Not authenticated",
                status_code=401,
                error_code="AUTH_REQUIRED"
            )

        return f(*args, **kwargs)

    return decorated_function


def require_method(*methods):
    """
    Decorator to require specific HTTP methods.
    
    Usage:
        @require_method("POST", "PUT")
        def endpoint():
            pass
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == "OPTIONS":
                return handle_options_request()
            
            if request.method not in methods:
                return error_response(
                    f"Method {request.method} not allowed",
                    status_code=405,
                    error_code="METHOD_NOT_ALLOWED"
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def validate_json(*required_fields):
    """
    Decorator to validate JSON request body contains required fields.
    
    Usage:
        @validate_json("username", "password")
        def login():
            pass
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            
            if not data:
                return error_response(
                    "Request body must be JSON",
                    status_code=400,
                    error_code="INVALID_JSON"
                )
            
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return error_response(
                    f"Missing required fields: {', '.join(missing_fields)}",
                    status_code=400,
                    error_code="MISSING_FIELDS",
                    details={"missing": missing_fields}
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def safe_api_call(f: Callable) -> Callable:
    """
    Decorator to wrap API endpoints with error handling.
    
    Catches exceptions and returns standardized error responses.
    
    Usage:
        @safe_api_call
        def endpoint():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            return error_response(
                str(e),
                status_code=400,
                error_code="VALIDATION_ERROR"
            )
        except PermissionError as e:
            logger.warning(f"Permission error: {str(e)}")
            return error_response(
                str(e),
                status_code=403,
                error_code="PERMISSION_DENIED"
            )
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}", exc_info=True)
            return error_response(
                "An unexpected error occurred",
                status_code=500,
                error_code="INTERNAL_ERROR"
            )
    
    return decorated_function
