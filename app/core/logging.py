import logging
import sys
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Union, Optional
from pythonjsonlogger import jsonlogger
from logging.handlers import TimedRotatingFileHandler
from contextvars import ContextVar
from app.core.config import settings

# Create context variables here to avoid circular imports
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
user_email_ctx_var: ContextVar[Optional[str]] = ContextVar("user_email", default=None)
user_is_admin_ctx_var: ContextVar[bool] = ContextVar("user_is_admin", default=False)

# LogConfig class removed; all config comes from settings

def setup_logging() -> None:
    """
    Configure Python standard logging for the application.
    - JSON logs in production
    - Colorized logs in development
    - Supports log level from config
    """
    config = settings
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Remove all handlers
    log_level = getattr(logging, str(config.LOG_LEVEL).upper(), logging.INFO)
    root_logger.setLevel(log_level)

    if getattr(config, "LOG_JSON_FORMAT", False):
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(user_id)s %(user_email)s %(is_admin)s'
        )
    else:
        # Simple color formatter for dev
        formatter = logging.Formatter(
            fmt='[%(asctime)s] %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Optional: Add file handler if enabled
    if getattr(config, "LOG_FILE_ENABLED", False):
        base_log_dir = Path(getattr(config, "LOG_FILE_PATH", "./logs"))
        base_log_dir.mkdir(parents=True, exist_ok=True)
        logger_name = getattr(config, "LOGGER_NAME", "daily_challenge")
        
        # Use a consistent base filename for the rotating logs
        log_file = base_log_dir / f"{logger_name}.log"
        
        # Set up TimedRotatingFileHandler for 12-hour rotation
        # when='H' means hours, interval=12 means every 12 hours
        # backupCount=10 keeps up to 10 rotated files before deleting older ones
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='H',
            interval=12,
            backupCount=10,
            encoding='utf-8'
        )
        # This will produce files like daily_challenge.log.2025-05-08_00
        file_handler.suffix = "%Y-%m-%d_%H"
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.info(f"Standard logging initialized: level={config.LOG_LEVEL}, json={getattr(config, 'LOG_JSON_FORMAT', False)}, logdir={getattr(config, 'LOG_FILE_PATH', './logs')}")

# Import context variables from middleware to avoid duplication
# This will be imported when the module is loaded
from app.core.middleware import request_id_ctx_var, user_id_ctx_var, user_email_ctx_var, user_is_admin_ctx_var

class RequestContextFilter(logging.Filter):
    """Filter that adds request and user context to log records."""
    def filter(self, record):
        # If request_id isn't already set in the record or is empty, get it from context
        if not hasattr(record, "request_id") or not record.request_id:
            record.request_id = request_id_ctx_var.get("")
            
        # Always get user context from context variables
        record.user_id = user_id_ctx_var.get("")
        record.user_email = user_email_ctx_var.get("")
        record.is_admin = user_is_admin_ctx_var.get(False)
        return True

logging.getLogger().addFilter(RequestContextFilter())

def get_logger(name: str = None) -> logging.Logger:
    return logging.getLogger(name)
    logger.info(
        f"Logging initialized: level={config.LOG_LEVEL}, "
        f"json={config.JSON_LOGS}, logdir={str(config.LOGS_DIR)}"
    )

    # All handlers now use only the callable formatter, so KeyError is impossible.



