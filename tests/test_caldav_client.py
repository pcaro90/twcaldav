"""Tests for CalDAV client module."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from icalendar import Calendar, Todo

from twcaldav.caldav_client import CalDAVClient, CalDAVError, VTodo


class TestVTodo:
    """Tests for VTodo dataclass."""

    def test_from_icalendar_minimal(self) -> None:
        """Test creating VTodo from minimal icalendar component."""
        todo = Todo()
        todo.add("UID", "test-uid-123")
        todo.add("SUMMARY", "Test task")

        vtodo = VTodo.from_icalendar(todo)

        assert vtodo.uid == "test-uid-123"
        assert vtodo.summary == "Test task"
        assert vtodo.status is None
        assert vtodo.description is None
        assert vtodo.due is None

    def test_from_icalendar_full(self) -> None:
        """Test creating VTodo from complete icalendar component."""
        todo = Todo()
        todo.add("UID", "test-uid-123")
        todo.add("SUMMARY", "Complete task")
        todo.add("STATUS", "NEEDS-ACTION")
        todo.add("DESCRIPTION", "Task description")
        todo.add("DUE", datetime(2024, 11, 20, 12, 0, 0, tzinfo=UTC))
        todo.add("PRIORITY", 5)
        todo.add("CATEGORIES", ["work", "important"])
        todo.add("CREATED", datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC))
        todo.add("LAST-MODIFIED", datetime(2024, 11, 17, 11, 0, 0, tzinfo=UTC))

        vtodo = VTodo.from_icalendar(todo)

        assert vtodo.uid == "test-uid-123"
        assert vtodo.summary == "Complete task"
        assert vtodo.status == "NEEDS-ACTION"
        assert vtodo.description == "Task description"
        assert vtodo.due == datetime(2024, 11, 20, 12, 0, 0, tzinfo=UTC)
        assert vtodo.priority == 5
        assert vtodo.categories == ["work", "important"]

    def test_to_icalendar_minimal(self) -> None:
        """Test converting minimal VTodo to icalendar."""
        vtodo = VTodo(
            uid="test-uid-123",
            summary="Test task",
        )

        todo = vtodo.to_icalendar()

        assert str(todo.get("UID")) == "test-uid-123"
        assert str(todo.get("SUMMARY")) == "Test task"
        assert todo.get("STATUS") is None

    def test_to_icalendar_full(self) -> None:
        """Test converting complete VTodo to icalendar."""
        vtodo = VTodo(
            uid="test-uid-123",
            summary="Complete task",
            status="NEEDS-ACTION",
            description="Task description",
            due=datetime(2024, 11, 20, 12, 0, 0, tzinfo=UTC),
            priority=5,
            categories=["work", "important"],
            created=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
            last_modified=datetime(2024, 11, 17, 11, 0, 0, tzinfo=UTC),
        )

        todo = vtodo.to_icalendar()

        assert str(todo.get("UID")) == "test-uid-123"
        assert str(todo.get("SUMMARY")) == "Complete task"
        assert str(todo.get("STATUS")) == "NEEDS-ACTION"
        assert str(todo.get("DESCRIPTION")) == "Task description"
        assert todo.get("PRIORITY") == 5
        # X-TASKWARRIOR-UUID no longer included (using UDA instead)


class TestCalDAVClient:
    """Tests for CalDAVClient class."""

    @patch("caldav.DAVClient")
    def test_init_success(self, mock_dav_client) -> None:
        """Test successful initialization."""
        mock_principal = Mock()
        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )

        assert client.url == "https://caldav.example.com"
        assert client.username == "user"
        mock_dav_client.assert_called_once()

    @patch("caldav.DAVClient")
    def test_init_connection_failure(self, mock_dav_client) -> None:
        """Test initialization with connection failure."""
        mock_dav_client.side_effect = Exception("Connection failed")

        with pytest.raises(CalDAVError, match="Failed to connect"):
            CalDAVClient(
                url="https://caldav.example.com", username="user", password="pass"
            )

    @patch("caldav.DAVClient")
    def test_list_calendars(self, mock_dav_client) -> None:
        """Test listing calendars."""
        mock_cal1 = Mock()
        mock_cal1.name = "Work"
        mock_cal2 = Mock()
        mock_cal2.name = "Personal"

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_cal1, mock_cal2]

        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )
        calendars = client.list_calendars()

        assert calendars == ["Work", "Personal"]

    @patch("caldav.DAVClient")
    def test_get_calendar_found(self, mock_dav_client) -> None:
        """Test getting calendar by ID."""
        mock_cal1 = Mock()
        mock_cal1.id = "Work"
        mock_cal2 = Mock()
        mock_cal2.id = "Personal"

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_cal1, mock_cal2]

        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )
        calendar = client.get_calendar("Work")

        assert calendar == mock_cal1

    @patch("caldav.DAVClient")
    def test_get_calendar_not_found(self, mock_dav_client) -> None:
        """Test getting non-existent calendar."""
        mock_cal = Mock()
        mock_cal.id = "Work"

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_cal]

        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )

        with pytest.raises(CalDAVError, match="Calendar not found"):
            client.get_calendar("NonExistent")

    @patch("caldav.DAVClient")
    def test_get_todos(self, mock_dav_client) -> None:
        """Test getting todos from calendar."""
        # Create mock todo
        todo_component = Todo()
        todo_component.add("UID", "test-uid-123")
        todo_component.add("SUMMARY", "Test task")

        cal = Calendar()
        cal.add_component(todo_component)

        mock_todo = Mock()
        mock_todo.data = cal.to_ical()

        mock_calendar = Mock()
        mock_calendar.id = "Work"
        mock_calendar.todos.return_value = [mock_todo]

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_calendar]

        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )
        todos = client.get_todos("Work")

        assert len(todos) == 1
        assert todos[0].uid == "test-uid-123"
        assert todos[0].summary == "Test task"

    @patch("caldav.DAVClient")
    def test_create_todo(self, mock_dav_client) -> None:
        """Test creating a todo."""
        mock_calendar = Mock()
        mock_calendar.id = "Work"
        mock_calendar.save_todo = Mock()

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_calendar]

        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )

        vtodo = VTodo(uid="test-uid-123", summary="Test task")
        client.create_todo("Work", vtodo)

        mock_calendar.save_todo.assert_called_once()

    @patch("caldav.DAVClient")
    def test_delete_todo(self, mock_dav_client) -> None:
        """Test deleting a todo."""
        # Create mock todo
        todo_component = Todo()
        todo_component.add("UID", "test-uid-123")
        todo_component.add("SUMMARY", "Test task")

        cal = Calendar()
        cal.add_component(todo_component)

        mock_todo = Mock()
        mock_todo.data = cal.to_ical()
        mock_todo.delete = Mock()

        mock_calendar = Mock()
        mock_calendar.id = "Work"
        mock_calendar.todos.return_value = [mock_todo]

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_calendar]

        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )
        client.delete_todo("Work", "test-uid-123")

        mock_todo.delete.assert_called_once()

    @patch("caldav.DAVClient")
    def test_get_todo_by_uid(self, mock_dav_client) -> None:
        """Test getting todo by UID."""
        # Create mock todos
        todo1 = Todo()
        todo1.add("UID", "test-uid-123")
        todo1.add("SUMMARY", "Task 1")

        todo2 = Todo()
        todo2.add("UID", "test-uid-456")
        todo2.add("SUMMARY", "Task 2")

        cal1 = Calendar()
        cal1.add_component(todo1)
        cal2 = Calendar()
        cal2.add_component(todo2)

        mock_todo1 = Mock()
        mock_todo1.data = cal1.to_ical()
        mock_todo2 = Mock()
        mock_todo2.data = cal2.to_ical()

        mock_calendar = Mock()
        mock_calendar.id = "Work"
        mock_calendar.todos.return_value = [mock_todo1, mock_todo2]

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_calendar]

        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )
        todo = client.get_todo_by_uid("Work", "test-uid-456")

        assert todo is not None
        assert todo.uid == "test-uid-456"
        assert todo.summary == "Task 2"

    @patch("caldav.DAVClient")
    def test_cancel_todo(self, mock_dav_client) -> None:
        """Test cancelling a todo (setting status to CANCELLED)."""
        # Create mock todo with NEEDS-ACTION status
        todo_component = Todo()
        todo_component.add("UID", "test-uid-123")
        todo_component.add("SUMMARY", "Test task")
        todo_component.add("STATUS", "NEEDS-ACTION")

        cal = Calendar()
        cal.add_component(todo_component)

        mock_todo = Mock()
        mock_todo.data = cal.to_ical()
        mock_todo.save = Mock()

        mock_calendar = Mock()
        mock_calendar.id = "Work"
        mock_calendar.todos.return_value = [mock_todo]

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_calendar]

        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )
        client.cancel_todo("Work", "test-uid-123")

        # Verify save was called
        mock_todo.save.assert_called_once()

        # Verify the updated data has CANCELLED status
        updated_cal = Calendar.from_ical(mock_todo.data)
        for component in updated_cal.walk():
            if component.name == "VTODO":
                assert str(component.get("STATUS")) == "CANCELLED"

    @patch("caldav.DAVClient")
    def test_cancel_todo_not_found(self, mock_dav_client) -> None:
        """Test cancelling a non-existent todo."""
        mock_calendar = Mock()
        mock_calendar.id = "Work"
        mock_calendar.todos.return_value = []

        mock_principal = Mock()
        mock_principal.calendars.return_value = [mock_calendar]

        mock_client_instance = Mock()
        mock_client_instance.principal.return_value = mock_principal
        mock_dav_client.return_value = mock_client_instance

        client = CalDAVClient(
            url="https://caldav.example.com", username="user", password="pass"
        )

        with pytest.raises(CalDAVError, match="Todo not found"):
            client.cancel_todo("Work", "nonexistent-uid")
