"""Tests for field mapping module."""

from datetime import UTC, datetime

from twcaldav.caldav_client import VTodo
from twcaldav.field_mapper import (
    caldav_to_taskwarrior,
    taskwarrior_to_caldav,
)
from twcaldav.taskwarrior import Task


class TestTaskWarriorToCalDAV:
    """Tests for TaskWarrior to CalDAV conversion."""

    def test_minimal_conversion(self):
        """Test converting minimal task."""
        task = Task(
            uuid="12345678-1234-1234-1234-123456789012",
            description="Test task",
            status="pending",
            entry=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
        )

        vtodo = taskwarrior_to_caldav(task)

        # CalDAV UID should be generated (UUID4 format)
        assert len(vtodo.uid) == 36  # UUID4 format
        assert "-" in vtodo.uid
        assert vtodo.summary == "Test task"
        assert vtodo.status == "NEEDS-ACTION"

    def test_full_conversion(self):
        """Test converting complete task."""
        task = Task(
            uuid="12345678-1234-1234-1234-123456789012",
            description="Complete task",
            status="pending",
            entry=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
            modified=datetime(2024, 11, 17, 11, 0, 0, tzinfo=UTC),
            project="work",
            due=datetime(2024, 11, 20, 12, 0, 0, tzinfo=UTC),
            priority="H",
            tags=["important", "urgent"],
        )

        vtodo = taskwarrior_to_caldav(task)

        assert vtodo.summary == "Complete task"
        assert vtodo.status == "NEEDS-ACTION"
        assert vtodo.due == datetime(2024, 11, 20, 12, 0, 0, tzinfo=UTC)
        assert vtodo.priority == 1  # H -> 1
        assert vtodo.categories is not None
        assert "work" in vtodo.categories
        assert "important" in vtodo.categories

    def test_status_mapping(self):
        """Test status mapping."""
        # pending -> NEEDS-ACTION
        task = Task(
            uuid="test-uuid",
            description="Test",
            status="pending",
            entry=datetime.now(UTC),
        )
        vtodo = taskwarrior_to_caldav(task)
        assert vtodo.status == "NEEDS-ACTION"

        # completed -> COMPLETED
        task.status = "completed"
        vtodo = taskwarrior_to_caldav(task)
        assert vtodo.status == "COMPLETED"

        # deleted -> CANCELLED
        task.status = "deleted"
        vtodo = taskwarrior_to_caldav(task)
        assert vtodo.status == "CANCELLED"

    def test_priority_mapping(self):
        """Test priority mapping."""
        task = Task(
            uuid="test-uuid",
            description="Test",
            status="pending",
            entry=datetime.now(UTC),
        )

        # H -> 1
        task.priority = "H"
        vtodo = taskwarrior_to_caldav(task)
        assert vtodo.priority == 1

        # M -> 5
        task.priority = "M"
        vtodo = taskwarrior_to_caldav(task)
        assert vtodo.priority == 5

        # L -> 9
        task.priority = "L"
        vtodo = taskwarrior_to_caldav(task)
        assert vtodo.priority == 9

        # None -> None
        task.priority = None
        vtodo = taskwarrior_to_caldav(task)
        assert vtodo.priority is None

    def test_annotations_in_description(self):
        """Test annotations are formatted in description."""
        task = Task(
            uuid="test-uuid",
            description="Test",
            status="pending",
            entry=datetime.now(UTC),
            annotations=[
                {"entry": "20241117T103000Z", "description": "First note"},
                {"entry": "20241117T110000Z", "description": "Second note"},
            ],
        )

        vtodo = taskwarrior_to_caldav(task)

        assert vtodo.description is not None
        assert "--- TaskWarrior Annotations ---" in vtodo.description
        assert "First note" in vtodo.description
        assert "Second note" in vtodo.description

    def test_categories_from_project_and_tags(self):
        """Test categories include project and tags."""
        task = Task(
            uuid="test-uuid",
            description="Test",
            status="pending",
            entry=datetime.now(UTC),
            project="work",
            tags=["urgent", "important"],
        )

        vtodo = taskwarrior_to_caldav(task)

        assert vtodo.categories == ["work", "urgent", "important"]


class TestCalDAVToTaskWarrior:
    """Tests for CalDAV to TaskWarrior conversion."""

    def test_minimal_conversion(self):
        """Test converting minimal VTodo."""
        vtodo = VTodo(
            uid="caldav-uid-123",
            summary="Test task",
            created=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        assert task.description == "Test task"
        assert task.status == "pending"
        assert task.entry == datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC)

    def test_full_conversion(self):
        """Test converting complete VTodo."""
        vtodo = VTodo(
            uid="caldav-uid-123",
            summary="Complete task",
            status="NEEDS-ACTION",
            due=datetime(2024, 11, 20, 12, 0, 0, tzinfo=UTC),
            priority=1,
            categories=["work", "urgent"],
            created=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
            last_modified=datetime(2024, 11, 17, 11, 0, 0, tzinfo=UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        # TW UUID is generated, CalDAV UID stored in UDA
        assert len(task.uuid) == 36  # UUID4 format
        assert task.caldav_uid == "caldav-uid-123"
        assert task.description == "Complete task"
        assert task.status == "pending"
        assert task.project == "work"
        assert task.tags == ["urgent"]
        assert task.priority == "H"

    def test_status_mapping(self):
        """Test status mapping."""
        vtodo = VTodo(uid="test-uid", summary="Test", created=datetime.now(UTC))

        # NEEDS-ACTION -> pending
        vtodo.status = "NEEDS-ACTION"
        task = caldav_to_taskwarrior(vtodo)
        assert task.status == "pending"

        # COMPLETED -> completed
        vtodo.status = "COMPLETED"
        task = caldav_to_taskwarrior(vtodo)
        assert task.status == "completed"

        # CANCELLED -> deleted
        vtodo.status = "CANCELLED"
        task = caldav_to_taskwarrior(vtodo)
        assert task.status == "deleted"

        # IN-PROCESS -> pending
        vtodo.status = "IN-PROCESS"
        task = caldav_to_taskwarrior(vtodo)
        assert task.status == "pending"

    def test_priority_mapping(self):
        """Test priority mapping."""
        vtodo = VTodo(uid="test-uid", summary="Test", created=datetime.now(UTC))

        # 1-3 -> H
        vtodo.priority = 1
        task = caldav_to_taskwarrior(vtodo)
        assert task.priority == "H"

        vtodo.priority = 3
        task = caldav_to_taskwarrior(vtodo)
        assert task.priority == "H"

        # 4-6 -> M
        vtodo.priority = 5
        task = caldav_to_taskwarrior(vtodo)
        assert task.priority == "M"

        # 7-9 -> L
        vtodo.priority = 9
        task = caldav_to_taskwarrior(vtodo)
        assert task.priority == "L"

        # None -> None
        vtodo.priority = None
        task = caldav_to_taskwarrior(vtodo)
        assert task.priority is None

    def test_annotations_from_description(self):
        """Test parsing annotations from description."""
        vtodo = VTodo(
            uid="test-uid",
            summary="Test",
            description=(
                "--- TaskWarrior Annotations ---\n"
                "[2024-11-17 10:30:00] First note\n"
                "[2024-11-17 11:00:00] Second note"
            ),
            created=datetime.now(UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        assert task.description == ""
        assert task.annotations is not None
        assert len(task.annotations) == 2
        assert task.annotations[0]["description"] == "First note"
        assert task.annotations[1]["description"] == "Second note"

    def test_preserve_existing_task_entry(self):
        """Test preserving entry timestamp from existing task."""
        original_entry = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        existing_task = Task(
            uuid="existing-uuid",
            description="Original",
            status="pending",
            entry=original_entry,
        )

        vtodo = VTodo(
            uid="test-uid",
            summary="Updated task",
            created=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
        )

        task = caldav_to_taskwarrior(vtodo, existing_task=existing_task)

        assert task.entry == original_entry
        assert task.uuid == "existing-uuid"

    def test_project_from_first_category(self):
        """Test extracting project from first category."""
        vtodo = VTodo(
            uid="test-uid",
            summary="Test",
            categories=["work", "urgent", "important"],
            created=datetime.now(UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        assert task.project == "work"
        assert task.tags == ["urgent", "important"]

    def test_round_trip_conversion(self):
        """Test converting back and forth preserves data."""
        original_task = Task(
            uuid="12345678-1234-1234-1234-123456789012",
            description="Round trip test",
            status="pending",
            entry=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
            project="work",
            priority="H",
            due=datetime(2024, 11, 20, 12, 0, 0, tzinfo=UTC),
        )

        # Convert to CalDAV
        vtodo = taskwarrior_to_caldav(original_task)

        # Convert back to TaskWarrior
        converted_task = caldav_to_taskwarrior(vtodo, existing_task=original_task)

        # Check key fields are preserved
        assert converted_task.uuid == original_task.uuid
        assert converted_task.description == original_task.description
        assert converted_task.status == original_task.status
        assert converted_task.project == original_task.project
        assert converted_task.priority == original_task.priority
        assert converted_task.due == original_task.due
