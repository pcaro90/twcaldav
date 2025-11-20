"""Tests for logger module."""

import logging

from twcaldav.logger import get_logger, setup_logger


def test_setup_logger_default() -> None:
    """Test logger setup with default settings."""
    logger = setup_logger(verbose=False)

    assert logger.name == "twcaldav"
    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1


def test_setup_logger_verbose() -> None:
    """Test logger setup with verbose mode."""
    logger = setup_logger(verbose=True)

    assert logger.name == "twcaldav"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1


def test_get_logger() -> None:
    """Test getting the logger."""
    setup_logger(verbose=False)
    logger = get_logger()

    assert logger.name == "twcaldav"
    assert isinstance(logger, logging.Logger)


def test_logger_no_duplicate_handlers() -> None:
    """Test that multiple setup calls don't create duplicate handlers."""
    logger1 = setup_logger(verbose=False)
    logger2 = setup_logger(verbose=True)

    # Should be the same logger
    assert logger1 is logger2
    # Should only have one handler
    assert len(logger2.handlers) == 1
