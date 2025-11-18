"""Pytest configuration for integration tests."""

import os
from pathlib import Path

import pytest

from tests.integration.helpers import (
    CALDAV_CALENDAR_ID,
    TW_PROJECT,
    clear_caldav,
    clear_taskwarrior,
    get_caldav_client,
    get_calendar,
)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring Docker environment",
    )


@pytest.fixture(scope="session", autouse=True)
def check_integration_environment():
    """Check if integration test environment is available.

    Integration tests require:
    - CALDAV_URL environment variable
    - Radicale server running
    - TaskWarrior installed

    Raises:
        pytest.skip: If environment is not configured for integration tests.
    """
    caldav_url = os.getenv("CALDAV_URL")

    if not caldav_url:
        pytest.skip(
            "Integration tests require Docker environment. "
            "Run with: ./scripts/run-integration-tests.sh"
        )


@pytest.fixture(scope="function")
def clean_test_environment():
    """Clean both TaskWarrior and CalDAV before each test.

    This fixture ensures each test starts with a clean slate.
    """
    taskdata = os.getenv("TASKDATA")

    # Clean before test
    clear_taskwarrior(taskdata, TW_PROJECT)

    client, principal = get_caldav_client()
    if principal:
        calendar = get_calendar(principal, CALDAV_CALENDAR_ID)
        if calendar:
            clear_caldav(calendar)

    yield

    # Optional: clean after test (can be commented out for debugging)
    # clear_taskwarrior(taskdata, TW_PROJECT)
    # if principal and calendar:
    #     clear_caldav(calendar)


@pytest.fixture(scope="function")
def multi_client_setup(tmp_path):
    """Setup two clean TaskWarrior clients for multi-client tests.

    Returns:
        Tuple of (client1_path, client2_path) as strings.
    """
    client1_path = tmp_path / "tw_client1"
    client2_path = tmp_path / "tw_client2"

    # Create directories
    client1_path.mkdir(parents=True, exist_ok=True)
    client2_path.mkdir(parents=True, exist_ok=True)

    # Setup UDA configuration for both clients
    for path in [client1_path, client2_path]:
        # Create taskrc with UDA config
        taskrc = path / "taskrc"
        taskrc.write_text(
            f"""data.location={path}
uda.caldav_uid.type=string
uda.caldav_uid.label=CalDAV UID
confirmation=off
"""
        )

    # Clear CalDAV to start fresh for multi-client tests
    client, principal = get_caldav_client()
    if principal:
        calendar = get_calendar(principal, CALDAV_CALENDAR_ID)
        if calendar:
            clear_caldav(calendar)

    yield str(client1_path), str(client2_path)

    # Cleanup is handled by pytest's tmp_path fixture
