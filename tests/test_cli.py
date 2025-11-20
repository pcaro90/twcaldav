"""Tests for CLI module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from twcaldav.cli import main, parse_args


def test_parse_args_defaults():
    """Test default arguments."""
    args = parse_args(["sync"])

    assert args.command == "sync"
    assert args.verbose is False
    assert args.dry_run is False
    assert args.config is None
    assert args.delete is False
    assert args.no_delete is False


def test_parse_args_verbose():
    """Test verbose flag."""
    args = parse_args(["-v", "sync"])
    assert args.verbose is True

    args = parse_args(["--verbose", "sync"])
    assert args.verbose is True


def test_parse_args_dry_run():
    """Test dry-run flag."""
    args = parse_args(["sync", "-n"])
    assert args.dry_run is True

    args = parse_args(["sync", "--dry-run"])
    assert args.dry_run is True


def test_parse_args_config():
    """Test config path argument."""
    args = parse_args(["-c", "/path/to/config.toml", "sync"])
    assert args.config == Path("/path/to/config.toml")

    args = parse_args(["--config", "/another/path.toml", "sync"])
    assert args.config == Path("/another/path.toml")


def test_parse_args_delete():
    """Test delete flag."""
    args = parse_args(["sync", "--delete"])
    assert args.delete is True


def test_parse_args_no_delete():
    """Test no-delete flag."""
    args = parse_args(["sync", "--no-delete"])
    assert args.no_delete is True


def test_parse_args_conflicting_delete_flags():
    """Test that conflicting delete flags raise error."""
    with pytest.raises(SystemExit):
        parse_args(["sync", "--delete", "--no-delete"])


def test_parse_args_combined():
    """Test combining multiple arguments."""
    args = parse_args(["-v", "-c", "/my/config.toml", "sync", "-n", "--delete"])

    assert args.command == "sync"
    assert args.verbose is True
    assert args.dry_run is True
    assert args.config == Path("/my/config.toml")
    assert args.delete is True


# End-to-End Integration Tests


@patch("twcaldav.sync_engine.SyncEngine")
@patch("twcaldav.caldav_client.CalDAVClient")
@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_main_success(
    mock_config_cls, mock_tw_cls, mock_caldav_cls, mock_sync_cls, tmp_path
):
    """Test successful sync execution."""
    # Create a temporary config file
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[sync]
delete_tasks = false

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    # Mock config
    mock_config = MagicMock()
    mock_config.caldav.url = "https://example.com/caldav"
    mock_config.caldav.username = "user"
    mock_config.caldav.password = "pass"
    mock_config.sync.delete_tasks = False
    mock_config.get_mapped_projects.return_value = ["work"]
    mock_config.get_mapped_calendars.return_value = ["Work Tasks"]
    mock_config_cls.from_file.return_value = mock_config

    # Mock TaskWarrior
    mock_tw = MagicMock()
    mock_tw.validate_uda.return_value = True  # UDA is configured
    mock_tw_cls.return_value = mock_tw

    # Mock CalDAV client
    mock_caldav = MagicMock()
    mock_caldav_cls.return_value = mock_caldav

    # Mock sync engine
    mock_sync = MagicMock()
    mock_stats = MagicMock()
    mock_stats.errors = 0
    type(mock_stats).__str__ = lambda self: "Mock stats"
    mock_sync.sync.return_value = mock_stats
    mock_sync_cls.return_value = mock_sync

    # Run main
    result = main(["-c", str(config_file), "sync"])

    # Verify
    assert result == 0
    mock_config_cls.from_file.assert_called_once()
    mock_tw_cls.assert_called_once()
    mock_caldav_cls.assert_called_once_with(
        url="https://example.com/caldav", username="user", password="pass"
    )
    mock_sync_cls.assert_called_once_with(
        config=mock_config,
        tw=mock_tw,
        caldav_client=mock_caldav,
        dry_run=False,
    )
    mock_sync.sync.assert_called_once()


@patch("twcaldav.sync_engine.SyncEngine")
@patch("twcaldav.caldav_client.CalDAVClient")
@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_main_dry_run(
    mock_config_cls, mock_tw_cls, mock_caldav_cls, mock_sync_cls, tmp_path
):
    """Test dry-run mode."""
    # Create config
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    # Mock config
    mock_config = MagicMock()
    mock_config.caldav.url = "https://example.com/caldav"
    mock_config.caldav.username = "user"
    mock_config.caldav.password = "pass"
    mock_config.sync.delete_tasks = False
    mock_config.get_mapped_projects.return_value = ["work"]
    mock_config.get_mapped_calendars.return_value = ["Work Tasks"]
    mock_config_cls.from_file.return_value = mock_config

    # Mock other components
    mock_tw_cls.return_value = MagicMock()
    mock_caldav_cls.return_value = MagicMock()
    mock_sync = MagicMock()
    mock_stats = MagicMock()
    mock_stats.errors = 0
    mock_sync.sync.return_value = mock_stats
    mock_sync_cls.return_value = mock_sync

    # Run with dry-run
    result = main(["-c", str(config_file), "sync", "--dry-run"])

    # Verify dry_run flag was passed
    assert result == 0
    mock_sync_cls.assert_called_once_with(
        config=mock_config,
        tw=mock_tw_cls.return_value,
        caldav_client=mock_caldav_cls.return_value,
        dry_run=True,
    )


@patch("twcaldav.config.Config")
def test_main_config_not_found(mock_config_cls, tmp_path):
    """Test handling of missing config file."""
    mock_config_cls.from_file.side_effect = FileNotFoundError("Config not found")
    config_file = tmp_path / "nonexistent.toml"

    # Run main
    result = main(["-c", str(config_file), "sync"])

    # Should return error code
    assert result == 1


@patch("twcaldav.sync_engine.SyncEngine")
@patch("twcaldav.caldav_client.CalDAVClient")
@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_main_uda_not_configured(
    mock_config_cls, mock_tw_cls, mock_caldav_cls, mock_sync_cls, tmp_path
):
    """Test handling when UDA is not configured."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config.caldav.url = "https://example.com/caldav"
    mock_config.caldav.username = "user"
    mock_config.caldav.password = "pass"
    mock_config.sync.delete_tasks = False
    mock_config.get_mapped_projects.return_value = ["work"]
    mock_config.get_mapped_calendars.return_value = ["Work Tasks"]
    mock_config_cls.from_file.return_value = mock_config

    # Mock TaskWarrior with UDA validation returning False
    mock_tw = MagicMock()
    mock_tw.validate_uda.return_value = False  # UDA not configured
    mock_tw_cls.return_value = mock_tw

    # Run main
    result = main(["-c", str(config_file), "sync"])

    # Should return error code
    assert result == 1

    # Should have called validate_uda
    mock_tw.validate_uda.assert_called_once_with("caldav_uid")


@patch("twcaldav.config.Config")
def test_main_config_invalid(mock_config_cls, tmp_path):
    """Test handling of invalid config."""
    mock_config_cls.from_file.side_effect = ValueError("Invalid config")

    config_file = tmp_path / "config.toml"
    config_file.write_text("invalid toml")

    # Run main
    result = main(["-c", str(config_file), "sync"])

    # Should return error code
    assert result == 1


@patch("twcaldav.sync_engine.SyncEngine")
@patch("twcaldav.caldav_client.CalDAVClient")
@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_main_delete_flag_override(
    mock_config_cls, mock_tw_cls, mock_caldav_cls, mock_sync_cls, tmp_path
):
    """Test --delete flag overrides config."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[sync]
delete_tasks = false

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config.caldav.url = "https://example.com/caldav"
    mock_config.caldav.username = "user"
    mock_config.caldav.password = "pass"
    mock_config.sync.delete_tasks = False
    mock_config.get_mapped_projects.return_value = ["work"]
    mock_config.get_mapped_calendars.return_value = ["Work Tasks"]
    mock_config_cls.from_file.return_value = mock_config

    mock_tw_cls.return_value = MagicMock()
    mock_caldav_cls.return_value = MagicMock()
    mock_sync = MagicMock()
    mock_stats = MagicMock()
    mock_stats.errors = 0
    mock_sync.sync.return_value = mock_stats
    mock_sync_cls.return_value = mock_sync

    # Run with --delete flag
    result = main(["-c", str(config_file), "sync", "--delete"])

    # Config should be updated to enable deletion
    assert result == 0
    assert mock_config.sync.delete_tasks is True


@patch("twcaldav.sync_engine.SyncEngine")
@patch("twcaldav.caldav_client.CalDAVClient")
@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_main_sync_with_errors(
    mock_config_cls, mock_tw_cls, mock_caldav_cls, mock_sync_cls, tmp_path
):
    """Test handling of sync errors."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config.caldav.url = "https://example.com/caldav"
    mock_config.caldav.username = "user"
    mock_config.caldav.password = "pass"
    mock_config.sync.delete_tasks = False
    mock_config.get_mapped_projects.return_value = ["work"]
    mock_config.get_mapped_calendars.return_value = ["Work Tasks"]
    mock_config_cls.from_file.return_value = mock_config

    mock_tw_cls.return_value = MagicMock()
    mock_caldav_cls.return_value = MagicMock()

    # Mock sync engine with errors
    mock_sync = MagicMock()
    mock_stats = MagicMock()
    mock_stats.errors = 5
    mock_sync.sync.return_value = mock_stats
    mock_sync_cls.return_value = mock_sync

    # Run main
    result = main(["-c", str(config_file), "sync"])

    # Should return error code
    assert result == 1


@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_main_client_init_failure(mock_config_cls, mock_tw_cls, tmp_path):
    """Test handling of client initialization failure."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config.caldav.url = "https://example.com/caldav"
    mock_config.caldav.username = "user"
    mock_config.caldav.password = "pass"
    mock_config.sync.delete_tasks = False
    mock_config.get_mapped_projects.return_value = ["work"]
    mock_config.get_mapped_calendars.return_value = ["Work Tasks"]
    mock_config_cls.from_file.return_value = mock_config

    # Mock TaskWarrior to raise exception
    mock_tw_cls.side_effect = Exception("TaskWarrior not found")

    # Run main
    result = main(["-c", str(config_file), "sync"])

    # Should return error code
    assert result == 1


@patch("twcaldav.sync_engine.SyncEngine")
@patch("twcaldav.caldav_client.CalDAVClient")
@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_main_sync_exception(
    mock_config_cls, mock_tw_cls, mock_caldav_cls, mock_sync_cls, tmp_path
):
    """Test handling of sync exception."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config.caldav.url = "https://example.com/caldav"
    mock_config.caldav.username = "user"
    mock_config.caldav.password = "pass"
    mock_config.sync.delete_tasks = False
    mock_config.get_mapped_projects.return_value = ["work"]
    mock_config.get_mapped_calendars.return_value = ["Work Tasks"]
    mock_config_cls.from_file.return_value = mock_config

    mock_tw_cls.return_value = MagicMock()
    mock_caldav_cls.return_value = MagicMock()

    # Mock sync engine to raise exception
    mock_sync = MagicMock()
    mock_sync.sync.side_effect = Exception("Sync failed")
    mock_sync_cls.return_value = mock_sync

    # Run main
    result = main(["-c", str(config_file), "sync"])

    # Should return error code
    assert result == 1


# Tests for new subcommands


def test_parse_args_unlink_subcommand():
    """Test unlink subcommand parsing."""
    args = parse_args(["unlink"])
    assert args.command == "unlink"
    assert args.project is None
    assert args.yes is False
    assert args.dry_run is False

    args = parse_args(["unlink", "--project", "work", "--yes"])
    assert args.command == "unlink"
    assert args.project == "work"
    assert args.yes is True

    args = parse_args(["unlink", "-n"])
    assert args.dry_run is True


def test_parse_args_test_caldav_subcommand():
    """Test test-caldav subcommand parsing."""
    args = parse_args(["test-caldav"])
    assert args.command == "test-caldav"


def test_parse_args_backward_compatibility():
    """Test backward compatibility when no subcommand is provided."""
    # Should default to 'sync' command when no subcommand specified
    # -v is global, but -n is sync-specific, so we can't test them together
    args = parse_args(["-v"])
    assert args.command == "sync"
    assert args.verbose is True
    # dry_run should have default value
    assert args.dry_run is False


@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_cmd_unlink_success(mock_config_cls, mock_tw_cls, tmp_path):
    """Test successful unlink execution."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config_cls.from_file.return_value = mock_config

    # Mock TaskWarrior
    mock_tw = MagicMock()
    mock_tw.validate_uda.return_value = True
    mock_tw.export_tasks.return_value = [
        {
            "uuid": "uuid1",
            "description": "Task 1",
            "project": "work",
            "caldav_uid": "uid1",
        },
        {
            "uuid": "uuid2",
            "description": "Task 2",
            "project": "work",
            "caldav_uid": "uid2",
        },
    ]
    mock_tw_cls.return_value = mock_tw

    # Run unlink with --yes flag
    result = main(["-c", str(config_file), "unlink", "--yes"])

    # Verify
    assert result == 0
    mock_tw.export_tasks.assert_called_once_with(["caldav_uid.any:"])
    assert mock_tw.modify_task.call_count == 2


@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_cmd_unlink_with_project_filter(mock_config_cls, mock_tw_cls, tmp_path):
    """Test unlink with project filter."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config_cls.from_file.return_value = mock_config

    mock_tw = MagicMock()
    mock_tw.validate_uda.return_value = True
    mock_tw.export_tasks.return_value = []
    mock_tw_cls.return_value = mock_tw

    # Run unlink with project filter
    result = main(["-c", str(config_file), "unlink", "--project", "work", "--yes"])

    # Verify filter was applied
    assert result == 0
    mock_tw.export_tasks.assert_called_once_with(["caldav_uid.any:", "project:work"])


@patch("twcaldav.taskwarrior.TaskWarrior")
@patch("twcaldav.config.Config")
def test_cmd_unlink_dry_run(mock_config_cls, mock_tw_cls, tmp_path):
    """Test unlink in dry-run mode."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config_cls.from_file.return_value = mock_config

    mock_tw = MagicMock()
    mock_tw.validate_uda.return_value = True
    mock_tw.export_tasks.return_value = [
        {
            "uuid": "uuid1",
            "description": "Task 1",
            "project": "work",
            "caldav_uid": "uid1",
        },
    ]
    mock_tw_cls.return_value = mock_tw

    # Run unlink in dry-run mode
    result = main(["-c", str(config_file), "unlink", "-n"])

    # Verify no modifications were made
    assert result == 0
    mock_tw.modify_task.assert_not_called()


@patch("twcaldav.caldav_client.CalDAVClient")
@patch("twcaldav.config.Config")
def test_cmd_test_caldav_success(mock_config_cls, mock_caldav_cls, tmp_path):
    """Test successful CalDAV connection test."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config.caldav.url = "https://example.com/caldav"
    mock_config.caldav.username = "user"
    mock_config.caldav.password = "pass"
    mock_config.mappings = {"work": "Work Tasks"}
    mock_config_cls.from_file.return_value = mock_config

    # Mock CalDAV client
    mock_caldav = MagicMock()
    mock_caldav.list_calendars.return_value = {
        "Work Tasks": "https://example.com/caldav/work",
        "Personal": "https://example.com/caldav/personal",
    }
    mock_caldav_cls.return_value = mock_caldav

    # Run test-caldav
    result = main(["-c", str(config_file), "test-caldav"])

    # Verify
    assert result == 0
    mock_caldav_cls.assert_called_once_with(
        url="https://example.com/caldav",
        username="user",
        password="pass",
    )
    mock_caldav.list_calendars.assert_called_once()


@patch("twcaldav.caldav_client.CalDAVClient")
@patch("twcaldav.config.Config")
def test_cmd_test_caldav_failure(mock_config_cls, mock_caldav_cls, tmp_path):
    """Test CalDAV connection test failure."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
[caldav]
url = "https://example.com/caldav"
username = "user"
password = "pass"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"
""")

    mock_config = MagicMock()
    mock_config.caldav.url = "https://example.com/caldav"
    mock_config.caldav.username = "user"
    mock_config.caldav.password = "pass"
    mock_config_cls.from_file.return_value = mock_config

    # Mock CalDAV client to raise exception
    mock_caldav_cls.side_effect = Exception("Connection failed")

    # Run test-caldav
    result = main(["-c", str(config_file), "test-caldav"])

    # Should return error code
    assert result == 1
