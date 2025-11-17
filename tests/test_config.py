"""Tests for configuration module."""

from pathlib import Path

import pytest

from twcaldav.config import (
    CalDAVConfig,
    Config,
    ProjectCalendarMapping,
    SyncConfig,
)


def test_config_from_dict_valid():
    """Test parsing valid configuration dictionary."""
    data = {
        "caldav": {
            "url": "https://caldav.example.com",
            "username": "testuser",
            "password": "testpass",
        },
        "mappings": [
            {
                "taskwarrior_project": "work",
                "caldav_calendar": "Work Calendar",
            },
            {
                "taskwarrior_project": "personal",
                "caldav_calendar": "Personal",
            },
        ],
        "sync": {
            "delete_tasks": True,
        },
    }

    config = Config.from_dict(data)

    assert config.caldav.url == "https://caldav.example.com"
    assert config.caldav.username == "testuser"
    assert config.caldav.password == "testpass"
    assert len(config.mappings) == 2
    assert config.mappings[0].taskwarrior_project == "work"
    assert config.mappings[0].caldav_calendar == "Work Calendar"
    assert config.sync.delete_tasks is True


def test_config_missing_caldav_section():
    """Test error when caldav section is missing."""
    data = {
        "mappings": [
            {
                "taskwarrior_project": "work",
                "caldav_calendar": "Work Calendar",
            }
        ]
    }

    with pytest.raises(ValueError, match="Missing required section: \\[caldav\\]"):
        Config.from_dict(data)


def test_config_missing_caldav_url():
    """Test error when caldav URL is missing."""
    data = {
        "caldav": {
            "username": "testuser",
            "password": "testpass",
        },
        "mappings": [
            {
                "taskwarrior_project": "work",
                "caldav_calendar": "Work Calendar",
            }
        ],
    }

    with pytest.raises(ValueError, match="Missing required field in \\[caldav\\]: url"):
        Config.from_dict(data)


def test_config_missing_mappings_section():
    """Test error when mappings section is missing."""
    data = {
        "caldav": {
            "url": "https://caldav.example.com",
            "username": "testuser",
            "password": "testpass",
        }
    }

    with pytest.raises(
        ValueError, match="Missing required section: \\[\\[mappings\\]\\]"
    ):
        Config.from_dict(data)


def test_config_empty_mappings():
    """Test error when mappings list is empty."""
    data = {
        "caldav": {
            "url": "https://caldav.example.com",
            "username": "testuser",
            "password": "testpass",
        },
        "mappings": [],
    }

    with pytest.raises(
        ValueError, match="\\[\\[mappings\\]\\] must be a non-empty list"
    ):
        Config.from_dict(data)


def test_config_missing_mapping_field():
    """Test error when mapping is missing required field."""
    data = {
        "caldav": {
            "url": "https://caldav.example.com",
            "username": "testuser",
            "password": "testpass",
        },
        "mappings": [
            {
                "taskwarrior_project": "work",
                # Missing caldav_calendar
            }
        ],
    }

    with pytest.raises(ValueError, match="Missing 'caldav_calendar' in mapping 1"):
        Config.from_dict(data)


def test_config_sync_defaults():
    """Test that sync config has proper defaults."""
    data = {
        "caldav": {
            "url": "https://caldav.example.com",
            "username": "testuser",
            "password": "testpass",
        },
        "mappings": [
            {
                "taskwarrior_project": "work",
                "caldav_calendar": "Work Calendar",
            }
        ],
        # No sync section
    }

    config = Config.from_dict(data)
    assert config.sync.delete_tasks is False


def test_get_calendar_for_project():
    """Test getting calendar for a project."""
    config = Config(
        caldav=CalDAVConfig(
            url="https://caldav.example.com",
            username="testuser",
            password="testpass",
        ),
        mappings=[
            ProjectCalendarMapping(
                taskwarrior_project="work",
                caldav_calendar="Work Calendar",
            ),
            ProjectCalendarMapping(
                taskwarrior_project="personal",
                caldav_calendar="Personal",
            ),
        ],
        sync=SyncConfig(delete_tasks=False),
    )

    assert config.get_calendar_for_project("work") == "Work Calendar"
    assert config.get_calendar_for_project("personal") == "Personal"
    assert config.get_calendar_for_project("unknown") is None


def test_get_project_for_calendar():
    """Test getting project for a calendar."""
    config = Config(
        caldav=CalDAVConfig(
            url="https://caldav.example.com",
            username="testuser",
            password="testpass",
        ),
        mappings=[
            ProjectCalendarMapping(
                taskwarrior_project="work",
                caldav_calendar="Work Calendar",
            ),
            ProjectCalendarMapping(
                taskwarrior_project="personal",
                caldav_calendar="Personal",
            ),
        ],
        sync=SyncConfig(delete_tasks=False),
    )

    assert config.get_project_for_calendar("Work Calendar") == "work"
    assert config.get_project_for_calendar("Personal") == "personal"
    assert config.get_project_for_calendar("Unknown") is None


def test_get_mapped_projects():
    """Test getting all mapped projects."""
    config = Config(
        caldav=CalDAVConfig(
            url="https://caldav.example.com",
            username="testuser",
            password="testpass",
        ),
        mappings=[
            ProjectCalendarMapping(
                taskwarrior_project="work",
                caldav_calendar="Work Calendar",
            ),
            ProjectCalendarMapping(
                taskwarrior_project="personal",
                caldav_calendar="Personal",
            ),
        ],
        sync=SyncConfig(delete_tasks=False),
    )

    projects = config.get_mapped_projects()
    assert projects == ["work", "personal"]


def test_get_mapped_calendars():
    """Test getting all mapped calendars."""
    config = Config(
        caldav=CalDAVConfig(
            url="https://caldav.example.com",
            username="testuser",
            password="testpass",
        ),
        mappings=[
            ProjectCalendarMapping(
                taskwarrior_project="work",
                caldav_calendar="Work Calendar",
            ),
            ProjectCalendarMapping(
                taskwarrior_project="personal",
                caldav_calendar="Personal",
            ),
        ],
        sync=SyncConfig(delete_tasks=False),
    )

    calendars = config.get_mapped_calendars()
    assert calendars == ["Work Calendar", "Personal"]


def test_config_from_file_not_found():
    """Test error when config file doesn't exist."""
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        Config.from_file(Path("/nonexistent/path/config.toml"))
