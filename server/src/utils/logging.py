"""
Logging configuration for the application.

Provides a standard logging setup and a small adapter that preserves the
"structured" call style used previously (e.g., logger.info("msg", key=value)).
This keeps call sites concise while emitting a single formatted string to the
standard Python logging backend.
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
    
    # Set noisy libraries to WARNING or ERROR level
    if level.upper() != "DEBUG":
        # HTTP client library
        logging.getLogger("httpx").setLevel(logging.WARNING)
        # PDF parsing libraries
        logging.getLogger("pdfminer").setLevel(logging.ERROR)
        logging.getLogger("pdfminer.psparser").setLevel(logging.ERROR)
        logging.getLogger("pdfminer.pdfinterp").setLevel(logging.ERROR)
        logging.getLogger("pdfminer.pdfpage").setLevel(logging.ERROR)
        logging.getLogger("pdfminer.pdfdocument").setLevel(logging.ERROR)
        logging.getLogger("pdfminer.converter").setLevel(logging.ERROR)
        logging.getLogger("pdfminer.cmapdb").setLevel(logging.ERROR)
        logging.getLogger("pdfminer.layout").setLevel(logging.ERROR)
    else:
        # Even in DEBUG mode, set pdfminer to WARNING to avoid overwhelming logs
        logging.getLogger("pdfminer").setLevel(logging.WARNING)
    
    # Log configuration complete
    logging.info(f"Logging configured with level: {level}")


class StructuredLoggerAdapter:
    """Lightweight adapter to allow logger.info("msg", key=value) usage.

    Converts keyword arguments into a simple " key=value" suffix appended to the
    log message and forwards to the standard library logger.
    """

    def __init__(self, base_logger: logging.Logger) -> None:
        self._logger = base_logger

    @staticmethod
    def _merge_message(msg: str, kwargs: Dict[str, Any]) -> str:
        if not kwargs:
            return msg
        suffix_parts = []
        for k, v in kwargs.items():
            # Avoid extremely long or binary outputs; fall back to repr for clarity
            try:
                text = str(v)
            except Exception:
                text = repr(v)
            suffix_parts.append(f"{k}={text}")
        return f"{msg} | " + " ".join(suffix_parts)

    def debug(self, msg: str, *args: Any, exc_info: Optional[bool] = None, stack_info: bool = False, stacklevel: int = 1, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        self._logger.debug(self._merge_message(msg, kwargs), *args, exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra)

    def info(self, msg: str, *args: Any, exc_info: Optional[bool] = None, stack_info: bool = False, stacklevel: int = 1, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        self._logger.info(self._merge_message(msg, kwargs), *args, exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra)

    def warning(self, msg: str, *args: Any, exc_info: Optional[bool] = None, stack_info: bool = False, stacklevel: int = 1, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        self._logger.warning(self._merge_message(msg, kwargs), *args, exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra)

    # Alias warn to warning to support existing calls
    warn = warning

    def error(self, msg: str, *args: Any, exc_info: Optional[bool] = None, stack_info: bool = False, stacklevel: int = 1, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        self._logger.error(self._merge_message(msg, kwargs), *args, exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra)

    def exception(self, msg: str, *args: Any, exc_info: Optional[bool] = True, stack_info: bool = False, stacklevel: int = 1, extra: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        # By default, include exception info
        self._logger.error(self._merge_message(msg, kwargs), *args, exc_info=True, stack_info=stack_info, stacklevel=stacklevel, extra=extra)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


def get_structured_logger(name: str) -> StructuredLoggerAdapter:
    """Get a structured logger adapter that supports key=value kwargs.

    Args:
        name: Logger name

    Returns:
        StructuredLoggerAdapter
    """
    return StructuredLoggerAdapter(logging.getLogger(name))


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