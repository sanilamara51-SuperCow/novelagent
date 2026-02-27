import logging
import logging.handlers
import os

from rich.logging import RichHandler


def get_logger(name: str = "novel", level: str | None = None) -> logging.Logger:
    """
    Get a configured logger with both console and file handlers.
    
    Args:
        name: Logger name
        level: Log level string (e.g., "DEBUG", "INFO"). Defaults to INFO.
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Return existing logger if already configured
    if logger.handlers:
        return logger
    
    # Determine log level
    if level is None:
        log_level = logging.INFO
    else:
        log_level = getattr(logging, level.upper())
    
    logger.setLevel(log_level)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Console handler with Rich
    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=False
    )
    console_handler.setLevel(log_level)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/novel.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    
    # File formatter
    file_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# Module-level convenience
logger = get_logger()
