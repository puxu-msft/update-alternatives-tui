"""Logging configuration for update-alternatives-tui.

This module provides a configured logger and utilities for
consistent logging throughout the application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .constants import APP_NAME, LogConfig, Paths


def setup_logger(
    name: str = APP_NAME,
    level: str = LogConfig.DEFAULT_LEVEL,
    log_file: Optional[Path] = None,
    console: bool = True,
) -> logging.Logger:
    """Set up and return a configured logger.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        console: Whether to output to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=LogConfig.FORMAT,
        datefmt=LogConfig.DATE_FORMAT
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError as e:
            logger.warning(f"Could not create log file: {e}")
    
    return logger


def get_logger(name: str = APP_NAME) -> logging.Logger:
    """Get a logger instance.
    
    This returns an existing logger or creates a new one with
    default configuration if it doesn't exist.
    
    Args:
        name: Logger name (defaults to app name)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Create default logger for the package
logger = setup_logger(APP_NAME, console=False)


class LoggerMixin:
    """Mixin class that provides logging capability to classes.
    
    Classes that inherit from this mixin get a `logger` property
    that returns a logger named after the class.
    
    Example:
        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("Doing something")
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(f"{APP_NAME}.{self.__class__.__name__}")


def log_call(func):
    """Decorator to log function calls.
    
    This decorator logs function entry and exit, including
    arguments and return values at DEBUG level.
    
    Example:
        @log_call
        def my_function(arg1, arg2):
            return result
    """
    def wrapper(*args, **kwargs):
        func_logger = get_logger(f"{APP_NAME}.{func.__module__}")
        func_logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            func_logger.debug(f"{func.__name__} returned {result!r}")
            return result
        except Exception as e:
            func_logger.exception(f"{func.__name__} raised {type(e).__name__}: {e}")
            raise
    return wrapper
