"""
Structured logging configuration for SecondBrain application.
"""

import logging
import logging.config
import os
import json
from datetime import datetime


def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
    """
    
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "()": "logging.Formatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "standard",
                "filename": os.path.join(log_dir, "app.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "standard",
                "filename": os.path.join(log_dir, "error.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10
            }
        },
        "loggers": {
            "": {  # root logger
                "level": log_level,
                "handlers": ["console", "file", "error_file"]
            },
            "flask": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "werkzeug": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # Get root logger
    logger = logging.getLogger()
    logger.info(f"Logging configured at {log_level} level")
    
    return logger


class StructuredLogger:
    """Wrapper for structured logging with contextual information"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}
    
    def set_context(self, **kwargs):
        """Set contextual information to be included in all logs"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear contextual information"""
        self.context.clear()
    
    def _format_message(self, message: str, extra: dict = None) -> str:
        """Format message with context and extra info"""
        extra_info = {**self.context, **(extra or {})}
        if extra_info:
            return f"{message} | {json.dumps(extra_info)}"
        return message
    
    def debug(self, message: str, extra: dict = None):
        """Log debug message"""
        self.logger.debug(self._format_message(message, extra))
    
    def info(self, message: str, extra: dict = None):
        """Log info message"""
        self.logger.info(self._format_message(message, extra))
    
    def warning(self, message: str, extra: dict = None):
        """Log warning message"""
        self.logger.warning(self._format_message(message, extra))
    
    def error(self, message: str, extra: dict = None, exc_info: bool = False):
        """Log error message"""
        self.logger.error(self._format_message(message, extra), exc_info=exc_info)
    
    def critical(self, message: str, extra: dict = None, exc_info: bool = False):
        """Log critical message"""
        self.logger.critical(self._format_message(message, extra), exc_info=exc_info)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)
