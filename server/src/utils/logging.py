"""
Logging configuration for the application.
"""

import logging
import sys
from typing import Dict, Any, Optional

from fastapi import FastAPI
from fastapi.logger import logger as fastapi_logger


def configure_logging(level: str = "INFO") -> None:
    """Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Configure FastAPI logger
    fastapi_logger.setLevel(numeric_level)
    
    # Configure specific loggers
    loggers = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "src.api",
        "src.core",
        "src.utils",
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(numeric_level)
    
    # Set httpx to WARNING level unless in DEBUG mode
    if level.upper() != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Log configuration complete
    logging.info(f"Logging configured with level: {level}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


def setup_app_logging(app: FastAPI, config: Dict[str, Any]) -> None:
    """Set up logging for the FastAPI application.
    
    Args:
        app: FastAPI application
        config: Application configuration
    """
    log_level = config.get("log_level", "INFO")
    configure_logging(log_level)
    
    # Add logging middleware
    @app.middleware("http")
    async def log_requests(request, call_next):
        logger = logging.getLogger("src.api")
        logger.debug(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.debug(f"Response: {response.status_code}")
        return response 