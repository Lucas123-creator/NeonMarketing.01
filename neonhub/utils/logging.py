import sys
import uuid
from typing import Any, Dict, Optional
from loguru import logger
from ..config.settings import get_settings

def setup_logging() -> None:
    """Configure logging with structured output and trace IDs."""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        format=settings.logging.format,
        level=settings.logging.level,
        serialize=settings.logging.json_format,
        backtrace=settings.debug,
        diagnose=settings.debug
    )
    
    # Add file handler for production
    if settings.environment == "production":
        logger.add(
            "logs/neonhub_{time}.log",
            rotation="500 MB",
            retention="10 days",
            compression="zip",
            format=settings.logging.format,
            level=settings.logging.level,
            serialize=settings.logging.json_format
        )

class TraceLogger:
    """Logger with trace ID for request tracking."""
    
    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        
    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """Log message with trace ID."""
        extra = kwargs.pop("extra", {})
        extra["trace_id"] = self.trace_id
        
        log_func = getattr(logger, level.lower())
        log_func(message, extra=extra, **kwargs)
        
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log("debug", message, **kwargs)
        
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log("info", message, **kwargs)
        
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log("warning", message, **kwargs)
        
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log("error", message, **kwargs)
        
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log("critical", message, **kwargs)
        
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._log("exception", message, **kwargs)

def get_logger(trace_id: Optional[str] = None) -> TraceLogger:
    """Get logger instance with trace ID."""
    return TraceLogger(trace_id) 