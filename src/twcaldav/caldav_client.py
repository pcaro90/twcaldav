"""CalDAV client integration module."""

import contextlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import caldav
from icalendar import Calendar, Todo

from twcaldav.logger import get_logger


@dataclass
class VTodo:
    """Represents a CalDAV VTODO (task)."""

    uid: str
    summary: str
    status: str | None = None
    description: str | None = None
    due: datetime | None = None
    priority: int | None = None
    categories: list[str] | None = None
    created: datetime | None = None
    last_modified: datetime | None = None
    taskwarrior_uuid: str | None = None  # Custom property

    @classmethod
    def from_icalendar(cls, todo: Any) -> "VTodo":
        """Create VTodo from icalendar Todo component.

        Args:
            todo: icalendar Todo component.

        Returns:
            VTodo instance.
        """
        uid = str(todo.get("UID", ""))
        summary = str(todo.get("SUMMARY", ""))

        # Optional fields
        status = str(todo.get("STATUS")) if todo.get("STATUS") else None
        description = str(todo.get("DESCRIPTION")) if todo.get("DESCRIPTION") else None

        # Parse datetime fields
        due = todo.get("DUE")
        if due and hasattr(due, "dt"):
            due = due.dt
            # Convert to datetime if it's a date
            if isinstance(due, datetime):
                pass  # Already a datetime
            else:
                # It's a date, convert to datetime
                from datetime import time

                due = datetime.combine(due, time())

        created = todo.get("CREATED")
        if created and hasattr(created, "dt"):
            created = created.dt

        last_modified = todo.get("LAST-MODIFIED")
        if last_modified and hasattr(last_modified, "dt"):
            last_modified = last_modified.dt

        # Parse priority (CalDAV uses 1-9, where 1 is highest)
        priority = None
        if todo.get("PRIORITY"):
            with contextlib.suppress(ValueError, TypeError):
                priority = int(todo.get("PRIORITY"))

        # Parse categories
        categories = None
        if todo.get("CATEGORIES"):
            cats = todo.get("CATEGORIES")
            # icalendar might return vCategory objects or strings
            if isinstance(cats, list):
                categories = []
                for c in cats:
                    # Handle vCategory objects by getting their string representation
                    if hasattr(c, "cats"):  # vCategory has a 'cats' attribute
                        categories.extend(c.cats)
                    else:
                        categories.append(str(c))
            else:
                categories = list(cats.cats) if hasattr(cats, "cats") else [str(cats)]

        # Check for custom X-TASKWARRIOR-UUID property
        taskwarrior_uuid = None
        if todo.get("X-TASKWARRIOR-UUID"):
            taskwarrior_uuid = str(todo.get("X-TASKWARRIOR-UUID"))

        return cls(
            uid=uid,
            summary=summary,
            status=status,
            description=description,
            due=due,
            priority=priority,
            categories=categories,
            created=created,
            last_modified=last_modified,
            taskwarrior_uuid=taskwarrior_uuid,
        )

    def to_icalendar(self) -> Todo:
        """Convert VTodo to icalendar Todo component.

        Returns:
            icalendar Todo component.
        """
        todo = Todo()
        todo.add("UID", self.uid)
        todo.add("SUMMARY", self.summary)

        if self.status:
            todo.add("STATUS", self.status)
        if self.description:
            todo.add("DESCRIPTION", self.description)
        if self.due:
            todo.add("DUE", self.due)
        if self.priority is not None:
            todo.add("PRIORITY", self.priority)
        if self.categories:
            todo.add("CATEGORIES", self.categories)
        if self.created:
            todo.add("CREATED", self.created)
        if self.last_modified:
            todo.add("LAST-MODIFIED", self.last_modified)

        # Add custom TaskWarrior UUID property
        if self.taskwarrior_uuid:
            todo.add("X-TASKWARRIOR-UUID", self.taskwarrior_uuid)

        return todo


class CalDAVError(Exception):
    """Exception raised for CalDAV-related errors."""


class CalDAVClient:
    """Interface to CalDAV server."""

    def __init__(self, url: str, username: str, password: str):
        """Initialize CalDAV client.

        Args:
            url: CalDAV server URL.
            username: Username for authentication.
            password: Password for authentication.

        Raises:
            CalDAVError: If connection fails.
        """
        self.url = url
        self.username = username
        self.logger = get_logger()

        try:
            self.logger.debug(f"Connecting to CalDAV server: {url}")
            self.client = caldav.DAVClient(
                url=url, username=username, password=password
            )
            self.principal = self.client.principal()
            self.logger.debug("Successfully connected to CalDAV server")
        except Exception as e:
            raise CalDAVError(f"Failed to connect to CalDAV server: {e}") from e

    def list_calendars(self) -> list[str]:
        """List all available calendars.

        Returns:
            List of calendar names.

        Raises:
            CalDAVError: If listing fails.
        """
        try:
            calendars = self.principal.calendars()
            calendar_names = []
            for cal in calendars:
                name = cal.name
                if name:
                    calendar_names.append(name)
            self.logger.debug(f"Found {len(calendar_names)} calendars")
            return calendar_names
        except Exception as e:
            raise CalDAVError(f"Failed to list calendars: {e}") from e

    def get_calendar(self, name: str) -> Any:
        """Get calendar by name.

        Args:
            name: Calendar name.

        Returns:
            Calendar object.

        Raises:
            CalDAVError: If calendar not found or access fails.
        """
        try:
            calendars = self.principal.calendars()
            for cal in calendars:
                if cal.name == name:
                    self.logger.debug(f"Found calendar: {name}")
                    return cal

            raise CalDAVError(f"Calendar not found: {name}")
        except CalDAVError:
            raise
        except Exception as e:
            raise CalDAVError(f"Failed to get calendar '{name}': {e}") from e

    def get_todos(self, calendar_name: str) -> list[VTodo]:
        """Get all todos from a calendar.

        Args:
            calendar_name: Name of calendar to query.

        Returns:
            List of VTodo objects.

        Raises:
            CalDAVError: If query fails.
        """
        try:
            calendar = self.get_calendar(calendar_name)
            todos = calendar.todos()

            vtodos = []
            for todo in todos:
                try:
                    # Parse the icalendar data
                    cal = Calendar.from_ical(todo.data)
                    for component in cal.walk():
                        if component.name == "VTODO":
                            vtodo = VTodo.from_icalendar(component)
                            vtodos.append(vtodo)
                except Exception as e:
                    self.logger.warning(f"Failed to parse todo: {e}")
                    continue

            self.logger.debug(
                f"Retrieved {len(vtodos)} todos from calendar '{calendar_name}'"
            )
            return vtodos
        except CalDAVError:
            raise
        except Exception as e:
            raise CalDAVError(
                f"Failed to get todos from calendar '{calendar_name}': {e}"
            ) from e

    def create_todo(self, calendar_name: str, vtodo: VTodo) -> None:
        """Create a new todo in a calendar.

        Args:
            calendar_name: Name of calendar.
            vtodo: VTodo object to create.

        Raises:
            CalDAVError: If creation fails.
        """
        try:
            calendar = self.get_calendar(calendar_name)

            # Create iCalendar
            cal = Calendar()
            cal.add("PRODID", "-//twcaldav//twcaldav//EN")
            cal.add("VERSION", "2.0")
            cal.add_component(vtodo.to_icalendar())

            ical_data = cal.to_ical()

            self.logger.debug(
                f"Creating todo in calendar '{calendar_name}': {vtodo.uid}"
            )
            calendar.save_todo(ical_data)
            self.logger.info(f"Created todo {vtodo.uid} in calendar '{calendar_name}'")
        except CalDAVError:
            raise
        except Exception as e:
            raise CalDAVError(
                f"Failed to create todo in calendar '{calendar_name}': {e}"
            ) from e

    def update_todo(self, calendar_name: str, vtodo: VTodo) -> None:
        """Update an existing todo.

        Args:
            calendar_name: Name of calendar.
            vtodo: VTodo object with updated data.

        Raises:
            CalDAVError: If update fails.
        """
        try:
            calendar = self.get_calendar(calendar_name)

            # Find the existing todo by UID
            todos = calendar.todos()
            for todo in todos:
                cal = Calendar.from_ical(todo.data)
                for component in cal.walk():
                    if (
                        component.name == "VTODO"
                        and str(component.get("UID")) == vtodo.uid
                    ):
                        # Update the todo
                        new_cal = Calendar()
                        new_cal.add("PRODID", "-//twcaldav//twcaldav//EN")
                        new_cal.add("VERSION", "2.0")
                        new_cal.add_component(vtodo.to_icalendar())

                        todo.data = new_cal.to_ical()
                        todo.save()
                        self.logger.info(
                            f"Updated todo {vtodo.uid} in calendar '{calendar_name}'"
                        )
                        return

            raise CalDAVError(f"Todo not found: {vtodo.uid}")
        except CalDAVError:
            raise
        except Exception as e:
            raise CalDAVError(
                f"Failed to update todo in calendar '{calendar_name}': {e}"
            ) from e

    def delete_todo(self, calendar_name: str, uid: str) -> None:
        """Delete a todo by UID.

        Args:
            calendar_name: Name of calendar.
            uid: UID of todo to delete.

        Raises:
            CalDAVError: If deletion fails.
        """
        try:
            calendar = self.get_calendar(calendar_name)

            # Find and delete the todo
            todos = calendar.todos()
            for todo in todos:
                cal = Calendar.from_ical(todo.data)
                for component in cal.walk():
                    if component.name == "VTODO" and str(component.get("UID")) == uid:
                        todo.delete()
                        self.logger.info(
                            f"Deleted todo {uid} from calendar '{calendar_name}'"
                        )
                        return

            raise CalDAVError(f"Todo not found: {uid}")
        except CalDAVError:
            raise
        except Exception as e:
            raise CalDAVError(
                f"Failed to delete todo from calendar '{calendar_name}': {e}"
            ) from e

    def get_todo_by_uid(self, calendar_name: str, uid: str) -> VTodo | None:
        """Get a specific todo by UID.

        Args:
            calendar_name: Name of calendar.
            uid: UID of todo.

        Returns:
            VTodo object if found, None otherwise.

        Raises:
            CalDAVError: If query fails.
        """
        todos = self.get_todos(calendar_name)
        for todo in todos:
            if todo.uid == uid:
                return todo
        return None

    def get_todo_by_taskwarrior_uuid(
        self, calendar_name: str, tw_uuid: str
    ) -> VTodo | None:
        """Get a todo by TaskWarrior UUID.

        Args:
            calendar_name: Name of calendar.
            tw_uuid: TaskWarrior UUID.

        Returns:
            VTodo object if found, None otherwise.

        Raises:
            CalDAVError: If query fails.
        """
        todos = self.get_todos(calendar_name)
        for todo in todos:
            if todo.taskwarrior_uuid == tw_uuid:
                return todo
        return None
