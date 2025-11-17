"""Tests for CLI module."""

from pathlib import Path

import pytest

from twcaldav.cli import parse_args


def test_parse_args_defaults():
    """Test default arguments."""
    args = parse_args([])

    assert args.verbose is False
    assert args.dry_run is False
    assert args.config is None
    assert args.delete is False
    assert args.no_delete is False


def test_parse_args_verbose():
    """Test verbose flag."""
    args = parse_args(["-v"])
    assert args.verbose is True

    args = parse_args(["--verbose"])
    assert args.verbose is True


def test_parse_args_dry_run():
    """Test dry-run flag."""
    args = parse_args(["-n"])
    assert args.dry_run is True

    args = parse_args(["--dry-run"])
    assert args.dry_run is True


def test_parse_args_config():
    """Test config path argument."""
    args = parse_args(["-c", "/path/to/config.toml"])
    assert args.config == Path("/path/to/config.toml")

    args = parse_args(["--config", "/another/path.toml"])
    assert args.config == Path("/another/path.toml")


def test_parse_args_delete():
    """Test delete flag."""
    args = parse_args(["--delete"])
    assert args.delete is True


def test_parse_args_no_delete():
    """Test no-delete flag."""
    args = parse_args(["--no-delete"])
    assert args.no_delete is True


def test_parse_args_conflicting_delete_flags():
    """Test that conflicting delete flags raise error."""
    with pytest.raises(SystemExit):
        parse_args(["--delete", "--no-delete"])


def test_parse_args_combined():
    """Test combining multiple arguments."""
    args = parse_args(["-v", "-n", "--config", "/my/config.toml", "--delete"])

    assert args.verbose is True
    assert args.dry_run is True
    assert args.config == Path("/my/config.toml")
    assert args.delete is True
