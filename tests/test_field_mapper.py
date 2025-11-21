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

    def test_minimal_conversion(self) -> None:
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

    def test_full_conversion(self) -> None:
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
        # Project is not synced to categories - only tags are synced
        assert vtodo.categories == ["important", "urgent"]

    def test_status_mapping(self) -> None:
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

    def test_priority_mapping(self) -> None:
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

    def test_annotations_in_description(self) -> None:
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

    def test_categories_from_tags_only(self) -> None:
        """Test categories include only tags (not project)."""
        task = Task(
            uuid="test-uuid",
            description="Test",
            status="pending",
            entry=datetime.now(UTC),
            project="work",
            tags=["urgent", "important"],
        )

        vtodo = taskwarrior_to_caldav(task)

        # Project is not synced to categories - only tags
        assert vtodo.categories == ["urgent", "important"]

    def test_scheduled_to_dtstart(self) -> None:
        """Test scheduled field is mapped to DTSTART."""
        task = Task(
            uuid="test-uuid",
            description="Task with scheduled date",
            status="pending",
            entry=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
            scheduled=datetime(2024, 11, 20, 9, 0, 0, tzinfo=UTC),
        )

        vtodo = taskwarrior_to_caldav(task)

        assert vtodo.dtstart == datetime(2024, 11, 20, 9, 0, 0, tzinfo=UTC)

    def test_scheduled_none_maps_to_no_dtstart(self) -> None:
        """Test None scheduled does not set DTSTART."""
        task = Task(
            uuid="test-uuid",
            description="Task without scheduled",
            status="pending",
            entry=datetime.now(UTC),
            scheduled=None,
        )

        vtodo = taskwarrior_to_caldav(task)

        assert vtodo.dtstart is None


class TestCalDAVToTaskWarrior:
    """Tests for CalDAV to TaskWarrior conversion."""

    def test_minimal_conversion(self) -> None:
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

    def test_full_conversion(self) -> None:
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
        # Project is not set from categories - it will be set by sync engine
        assert task.project is None
        assert task.tags == ["work", "urgent"]
        assert task.priority == "H"

    def test_status_mapping(self) -> None:
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

    def test_priority_mapping(self) -> None:
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

    def test_annotations_from_description(self) -> None:
        """Test parsing annotations from description."""
        vtodo = VTodo(
            uid="test-uid",
            summary="Test",
            description=(
                "--- TaskWarrior Annotations ---\n"
                "20241117T103000Z|First note\n"
                "20241117T110000Z|Second note"
            ),
            created=datetime.now(UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        # When description only contains annotations, use summary as description
        assert task.description == "Test"
        assert task.annotations is not None
        assert len(task.annotations) == 2
        assert task.annotations[0]["entry"] == "20241117T103000Z"
        assert task.annotations[0]["description"] == "First note"
        assert task.annotations[1]["entry"] == "20241117T110000Z"
        assert task.annotations[1]["description"] == "Second note"

    def test_preserve_existing_task_entry(self) -> None:
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

    def test_categories_to_tags_only(self) -> None:
        """Test categories are mapped to tags only (not project)."""
        vtodo = VTodo(
            uid="test-uid",
            summary="Test",
            categories=["work", "urgent", "important"],
            created=datetime.now(UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        # Project is not set from categories - it will be set by sync engine
        assert task.project is None
        assert task.tags == ["work", "urgent", "important"]

    def test_dtstart_to_scheduled(self) -> None:
        """Test DTSTART is mapped to scheduled field."""
        vtodo = VTodo(
            uid="test-uid",
            summary="Task with start date",
            created=datetime.now(UTC),
            dtstart=datetime(2024, 11, 20, 9, 0, 0, tzinfo=UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        assert task.scheduled == datetime(2024, 11, 20, 9, 0, 0, tzinfo=UTC)

    def test_dtstart_none_maps_to_no_scheduled(self) -> None:
        """Test None DTSTART does not set scheduled."""
        vtodo = VTodo(
            uid="test-uid",
            summary="Task without start date",
            created=datetime.now(UTC),
            dtstart=None,
        )

        task = caldav_to_taskwarrior(vtodo)

        assert task.scheduled is None

    def test_round_trip_conversion(self) -> None:
        """Test converting back and forth preserves data."""
        original_task = Task(
            uuid="12345678-1234-1234-1234-123456789012",
            description="Round trip test",
            status="pending",
            entry=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
            project="work",
            priority="H",
            due=datetime(2024, 11, 20, 12, 0, 0, tzinfo=UTC),
            scheduled=datetime(2024, 11, 19, 9, 0, 0, tzinfo=UTC),
            tags=["important"],
        )

        # Convert to CalDAV
        vtodo = taskwarrior_to_caldav(original_task)

        # Convert back to TaskWarrior
        converted_task = caldav_to_taskwarrior(vtodo, existing_task=original_task)

        # Check key fields are preserved
        assert converted_task.uuid == original_task.uuid
        assert converted_task.description == original_task.description
        assert converted_task.status == original_task.status
        # Project is not synced via CalDAV - it will be None after round trip
        # The sync engine sets project based on calendar mapping
        assert converted_task.project is None
        assert converted_task.tags == original_task.tags
        assert converted_task.priority == original_task.priority
        assert converted_task.due == original_task.due
        assert converted_task.scheduled == original_task.scheduled

    def test_annotation_deduplication(self) -> None:
        """Test that annotations are deduplicated when merging."""
        # Create existing task with annotations
        existing_task = Task(
            uuid="test-uuid",
            description="Test task",
            status="pending",
            entry=datetime(2024, 11, 17, 10, 0, 0, tzinfo=UTC),
            annotations=[
                {"entry": "20241117T103000Z", "description": "Existing note 1"},
                {"entry": "20241117T110000Z", "description": "Existing note 2"},
            ],
        )

        # Create VTodo with overlapping and new annotations
        vtodo = VTodo(
            uid="test-uid",
            summary="Test task",
            description=(
                "--- TaskWarrior Annotations ---\n"
                "20241117T103000Z|Existing note 1\n"  # Duplicate
                "20241117T120000Z|New note 3"  # New
            ),
            created=datetime.now(UTC),
        )

        # Convert with existing task (should merge and deduplicate)
        task = caldav_to_taskwarrior(vtodo, existing_task=existing_task)

        # Should have 3 annotations total (2 existing + 1 new, no duplicate)
        assert task.annotations is not None
        assert len(task.annotations) == 3
        assert task.annotations[0]["description"] == "Existing note 1"
        assert task.annotations[1]["description"] == "Existing note 2"
        assert task.annotations[2]["description"] == "New note 3"

    def test_annotation_with_pipe_in_description(self) -> None:
        """Test annotations with pipe character in description."""
        vtodo = VTodo(
            uid="test-uid",
            summary="Test",
            description=(
                "--- TaskWarrior Annotations ---\n"
                "20241117T103000Z|Check API | POST /users"
            ),
            created=datetime.now(UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        assert task.annotations is not None
        assert len(task.annotations) == 1
        # Description should include the pipe after split on first pipe
        assert task.annotations[0]["description"] == "Check API | POST /users"

    def test_malformed_annotation_skipped(self) -> None:
        """Test that malformed annotations are skipped with warning."""
        vtodo = VTodo(
            uid="test-uid",
            summary="Test",
            description=(
                "--- TaskWarrior Annotations ---\n"
                "20241117T103000Z|Valid note\n"
                "Invalid line without pipe\n"  # Malformed
                "BADTIMESTAMP|Another note\n"  # Invalid timestamp
                "20241117T110000Z|Another valid note"
            ),
            created=datetime.now(UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        # Should only have 2 valid annotations
        assert task.annotations is not None
        assert len(task.annotations) == 2
        assert task.annotations[0]["description"] == "Valid note"
        assert task.annotations[1]["description"] == "Another valid note"

    def test_user_description_with_annotations(self) -> None:
        """Test CalDAV description with user text and annotations."""
        vtodo = VTodo(
            uid="test-uid",
            summary="Test",
            description=(
                "Some user description text\n"
                "--- TaskWarrior Annotations ---\n"
                "20241117T103000Z|Note 1"
            ),
            created=datetime.now(UTC),
        )

        task = caldav_to_taskwarrior(vtodo)

        # User description is extracted but not used (TW uses summary)
        assert task.description == "Some user description text"
        assert task.annotations is not None
        assert len(task.annotations) == 1
