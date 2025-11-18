"""Pytest configuration for integration tests."""

import os

import pytest


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


@pytest.fixture(scope="session")
def caldav_url():
    """Get CalDAV URL from environment."""
    return os.getenv("CALDAV_URL", "http://localhost:5232/test-user/")


@pytest.fixture(scope="session")
def caldav_username():
    """Get CalDAV username from environment."""
    return os.getenv("CALDAV_USERNAME", "test-user")


@pytest.fixture(scope="session")
def caldav_password():
    """Get CalDAV password from environment."""
    return os.getenv("CALDAV_PASSWORD", "test-pass")


@pytest.fixture(scope="session")
def caldav_calendar_id():
    """Get CalDAV calendar ID from environment."""
    return os.getenv("CALDAV_CALENDAR_ID", "test-calendar")


@pytest.fixture(scope="session")
def tw_project():
    """Get TaskWarrior project name from environment."""
    return os.getenv("TW_PROJECT", "test")


@pytest.fixture(scope="session")
def taskdata():
    """Get TaskWarrior data directory from environment."""
    return os.getenv("TASKDATA", None)


@pytest.fixture(scope="session", autouse=True)
def clear_test_data_once():
    """Clear test data once at the start of the test session.

    Integration tests are designed to run sequentially with state
    carrying over between tests (e.g., test_caldav_to_tw_create
    expects data from test_tw_to_caldav_create).

    This fixture runs once at the beginning to ensure a clean starting state.
    """
    # Import here to avoid circular imports
    from tests.integration.test_e2e import clear_test_data

    # Clear data before test session
    clear_test_data()

    yield

    # Optional: Clear after all tests complete
    # clear_test_data()
