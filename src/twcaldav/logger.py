"""Logging configuration for twcaldav."""

import logging
import sys
from typing import ClassVar


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for terminal output."""

    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET: ClassVar[str] = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color if supported.

        Args:
            record: Log record to format.

        Returns:
            Formatted log message.
        """
        # Add color if output is a terminal
        if sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, "")
            record.levelname = f"{color}{record.levelname}{self.RESET}"

        return super().format(record)


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Configure and return the main application logger.

    Args:
        verbose: If True, set log level to DEBUG. Otherwise INFO.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("twcaldav")

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Set log level
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create formatter
    formatter = ColoredFormatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def get_logger() -> logging.Logger:
    """Get the application logger.

    Returns:
        Logger instance.
    """
    return logging.getLogger("twcaldav")
