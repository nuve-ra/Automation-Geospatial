import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from typing import Any

class CustomJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'request_id'):
            log_obj['request_id'] = record.request_id
            
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def setup_logger(name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger:
    """Set up logger with both file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_path / log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(CustomJSONFormatter())
        logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomJSONFormatter())
    logger.addHandler(console_handler)
    
    return logger

# Create different loggers for different components
api_logger = setup_logger('api', 'api.log')
db_logger = setup_logger('database', 'database.log')
spatial_logger = setup_logger('spatial', 'spatial.log')

class LoggerMiddleware:
    """Middleware to log all API requests and responses"""
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
            
        start_time = datetime.now()
        
        # Log request
        request = {
            "method": scope.get("method", ""),
            "path": scope.get("path", ""),
            "query_string": scope.get("query_string", b"").decode(),
        }
        
        api_logger.info(f"Incoming request: {json.dumps(request)}")
        
        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                # Log response
                response_status = message["status"]
                api_logger.info(
                    f"Response status: {response_status}, "
                    f"Request duration: {(datetime.now() - start_time).total_seconds()}s"
                )
            await send(message)
            
        try:
            await self.app(scope, receive, wrapped_send)
        except Exception as e:
            api_logger.error(f"Error processing request: {str(e)}", exc_info=True)
            raise

def log_error(error: Exception, context: dict = None) -> None:
    """Centralized error logging function"""
    error_details = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {}
    }
    api_logger.error(json.dumps(error_details), exc_info=True)

class APIException(Exception):
    """Base exception for API errors"""
    def __init__(self, message: str, status_code: int = 500, context: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.context = context or {}
        log_error(self, self.context)
