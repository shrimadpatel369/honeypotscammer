"""
Structured logging configuration for the application
Logs all API requests, responses, and important events
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import sys

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Custom formatter for structured logging
class StructuredFormatter(logging.Formatter):
    """Format logs as structured JSON"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "request_data"):
            log_data["request"] = record.request_data
        if hasattr(record, "response_data"):
            log_data["response"] = record.response_data
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "error"):
            log_data["error"] = record.error
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ReadableFormatter(logging.Formatter):
    """Format logs in human-readable format"""
    
    def format(self, record):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {record.levelname:8s} | {record.name:30s} | {record.getMessage()}"
        
        # Add session ID if present
        if hasattr(record, "session_id"):
            log_msg += f" | Session: {record.session_id}"
            
        # Add duration if present
        if hasattr(record, "duration_ms"):
            log_msg += f" | Duration: {record.duration_ms}ms"
        
        return log_msg


def setup_logging(debug: bool = False):
    """
    Setup logging configuration with multiple handlers
    
    Creates three log files:
    - app.log: All application logs (readable format)
    - requests.log: All API requests/responses (structured JSON)
    - errors.log: Only errors and exceptions
    """
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler (readable format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ReadableFormatter())
    root_logger.addHandler(console_handler)
    
    # Application log file (readable format)
    app_log_file = LOGS_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    app_file_handler = logging.FileHandler(app_log_file, encoding='utf-8')
    app_file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    app_file_handler.setFormatter(ReadableFormatter())
    root_logger.addHandler(app_file_handler)
    
    # Requests log file (structured JSON)
    requests_log_file = LOGS_DIR / f"requests_{datetime.now().strftime('%Y%m%d')}.log"
    requests_file_handler = logging.FileHandler(requests_log_file, encoding='utf-8')
    requests_file_handler.setLevel(logging.INFO)
    requests_file_handler.setFormatter(StructuredFormatter())
    
    # Create a separate logger for requests
    request_logger = logging.getLogger("api.requests")
    request_logger.addHandler(requests_file_handler)
    request_logger.propagate = False  # Don't propagate to root logger
    
    # Error log file (readable format)
    error_log_file = LOGS_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_file_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(ReadableFormatter())
    root_logger.addHandler(error_file_handler)
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized - Logs directory: {LOGS_DIR.absolute()}")
    logging.info(f"Log files: {app_log_file.name}, {requests_log_file.name}, {error_log_file.name}")


def log_request(
    session_id: str,
    request_data: Dict[str, Any],
    masked_headers: Dict[str, str]
):
    """Log incoming API request with all details"""
    logger = logging.getLogger("api.requests")
    
    log_record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "",
        0,
        f"Incoming Request - Session: {session_id}",
        (),
        None
    )
    log_record.session_id = session_id
    log_record.request_data = {
        "headers": masked_headers,
        "body": request_data
    }
    
    logger.handle(log_record)


def log_response(
    session_id: str,
    response_data: Dict[str, Any],
    duration_ms: float,
    status_code: int = 200
):
    """Log API response with timing information"""
    logger = logging.getLogger("api.requests")
    
    log_record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "",
        0,
        f"Outgoing Response - Session: {session_id}",
        (),
        None
    )
    log_record.session_id = session_id
    log_record.response_data = {
        "status_code": status_code,
        "body": response_data
    }
    log_record.duration_ms = round(duration_ms, 2)
    
    logger.handle(log_record)


def log_error(
    session_id: str,
    error_message: str,
    error_details: Dict[str, Any] = None
):
    """Log error with context"""
    logger = logging.getLogger("api.requests")
    
    log_record = logger.makeRecord(
        logger.name,
        logging.ERROR,
        "",
        0,
        f"Error - Session: {session_id} - {error_message}",
        (),
        None
    )
    log_record.session_id = session_id
    log_record.error = error_details or {}
    
    logger.handle(log_record)


def mask_sensitive_data(headers: Dict[str, str]) -> Dict[str, str]:
    """Mask sensitive information in headers"""
    masked = headers.copy()
    sensitive_keys = ["x-api-key", "authorization", "api-key", "token"]
    
    for key in sensitive_keys:
        if key in masked:
            value = masked[key]
            if len(value) > 8:
                masked[key] = value[:4] + "****" + value[-4:]
            else:
                masked[key] = "****"
    
    return masked