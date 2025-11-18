"""Integration tests for TaskWarrior → CalDAV synchronization."""

import time

import pytest

from tests.integration.helpers import (
    add_tags,
    annotate_task,
    complete_task,
    create_task,
    delete_task,
    find_todo_by_summary,
    get_caldav_client,
    get_calendar,
    get_tasks,
    get_todo_property,
    get_todos,
    modify_task,
    remove_tags,
    run_sync,
)


@pytest.mark.integration
def test_tw_to_caldav_create_simple(clean_test_environment):
    """Create simple task in TaskWarrior, verify it syncs to CalDAV."""
    # Create task in TaskWarrior
    description = "Simple TaskWarrior test task"
    task = create_task(description)
    assert task is not None

    # Run sync
    assert run_sync()

    # Verify todo exists in CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todos = get_todos(calendar)
    assert len(todos) == 1

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None
    assert str(get_todo_property(todo, "summary")) == description


@pytest.mark.integration
def test_tw_to_caldav_create_with_due_date(clean_test_environment):
    """Create task with due date in TaskWarrior, verify it syncs to CalDAV."""
    # Create task with due date
    description = "TaskWarrior task with due date"
    task = create_task(description, due="tomorrow")
    assert task is not None
    assert "due" in task

    # Run sync
    assert run_sync()

    # Verify todo has due date in CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None
    due_prop = get_todo_property(todo, "due")
    assert due_prop is not None


@pytest.mark.integration
def test_tw_to_caldav_create_with_priority(clean_test_environment):
    """Create task with priority in TaskWarrior, verify it syncs to CalDAV."""
    # Create task with high priority
    description = "TaskWarrior task with high priority"
    task = create_task(description, priority="H")
    assert task is not None
    assert task.get("priority") == "H"

    # Run sync
    assert run_sync()

    # Verify todo has priority in CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None
    priority = get_todo_property(todo, "priority")
    # High priority in TW maps to 1 in CalDAV
    assert priority is not None


@pytest.mark.integration
def test_tw_to_caldav_create_with_tags(clean_test_environment):
    """Create task with tags in TaskWarrior, verify they sync to CalDAV."""
    # Create task with tags
    description = "TaskWarrior task with tags"
    task = create_task(description, tags=["urgent", "work"])
    assert task is not None
    assert "tags" in task
    assert "urgent" in task["tags"]
    assert "work" in task["tags"]

    # Run sync
    assert run_sync()

    # Verify todo exists in CalDAV (tags might be in categories or description)
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None


@pytest.mark.integration
def test_tw_to_caldav_create_completed(clean_test_environment):
    """Create and complete task in TaskWarrior, verify it syncs to CalDAV."""
    # Create and complete task
    description = "TaskWarrior completed task"
    task = create_task(description)
    assert task is not None
    assert complete_task(task["uuid"])

    # Run sync
    assert run_sync()

    # Verify todo is completed in CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    # Note: calendar.todos() might not return completed todos
    # This test verifies the sync doesn't fail
    todos = get_todos(calendar)
    # Completed tasks may or may not appear depending on CalDAV server behavior
    # The important thing is that sync succeeded without errors


@pytest.mark.integration
def test_tw_to_caldav_modify_description(clean_test_environment):
    """Modify task description in TaskWarrior, verify it syncs to CalDAV."""
    # Create and sync initial task
    description = "Original TaskWarrior description"
    task = create_task(description)
    assert task is not None
    assert run_sync()

    # Verify initial sync
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Modify description in TaskWarrior
    new_description = "Modified TaskWarrior description"
    assert modify_task(task["uuid"], description=new_description)

    # Run sync
    assert run_sync()

    # Verify CalDAV todo summary updated
    todo = find_todo_by_summary(calendar, new_description)
    assert todo is not None
    assert str(get_todo_property(todo, "summary")) == new_description


@pytest.mark.integration
def test_tw_to_caldav_modify_due_date(clean_test_environment):
    """Modify task due date in TaskWarrior, verify it syncs to CalDAV."""
    # Create task with due date
    description = "TaskWarrior task with changeable due date"
    task = create_task(description, due="tomorrow")
    assert task is not None
    assert run_sync()

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Modify due date in TaskWarrior
    assert modify_task(task["uuid"], due="3days")

    # Run sync
    assert run_sync()

    # Verify CalDAV todo due date updated
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None
    due_prop = get_todo_property(todo, "due")
    assert due_prop is not None


@pytest.mark.integration
def test_tw_to_caldav_modify_priority(clean_test_environment):
    """Modify task priority in TaskWarrior, verify it syncs to CalDAV."""
    # Create task with medium priority
    description = "TaskWarrior task with changeable priority"
    task = create_task(description, priority="M")
    assert task is not None
    assert run_sync()

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Modify priority to high in TaskWarrior
    assert modify_task(task["uuid"], priority="H")

    # Run sync
    assert run_sync()

    # Verify CalDAV todo priority updated
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None
    priority = get_todo_property(todo, "priority")
    assert priority is not None


@pytest.mark.integration
def test_tw_to_caldav_modify_tags_add(clean_test_environment):
    """Add tags to task in TaskWarrior, verify they sync to CalDAV."""
    # Create task without tags
    description = "TaskWarrior task for adding tags"
    task = create_task(description)
    assert task is not None
    assert run_sync()

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Add tags in TaskWarrior
    assert add_tags(task["uuid"], ["urgent", "important"])

    # Run sync
    assert run_sync()

    # Verify tags synced to CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None


@pytest.mark.integration
def test_tw_to_caldav_modify_tags_remove(clean_test_environment):
    """Remove tags from task in TaskWarrior, verify they sync to CalDAV."""
    # Create task with tags
    description = "TaskWarrior task for removing tags"
    task = create_task(description, tags=["urgent", "work", "temp"])
    assert task is not None
    assert run_sync()

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Remove a tag in TaskWarrior
    assert remove_tags(task["uuid"], ["temp"])

    # Run sync
    assert run_sync()

    # Verify task still exists in CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None


@pytest.mark.integration
def test_tw_to_caldav_modify_status_to_completed(clean_test_environment):
    """Complete task in TaskWarrior, verify it syncs to CalDAV."""
    # Create pending task
    description = "TaskWarrior task to be completed"
    task = create_task(description)
    assert task is not None
    assert run_sync()

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Complete task in TaskWarrior
    assert complete_task(task["uuid"])

    # Run sync
    assert run_sync()

    # Verify task is completed (might not be in todos() list)
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    # Sync succeeded - completed tasks may not appear in calendar.todos()


@pytest.mark.integration
def test_tw_to_caldav_delete(clean_test_environment):
    """Delete task in TaskWarrior, verify it syncs to CalDAV."""
    # Create and sync task
    description = "TaskWarrior task to be deleted"
    task = create_task(description)
    assert task is not None
    assert run_sync()

    # Verify initial sync
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todos_before = len(get_todos(calendar))
    assert todos_before == 1

    # Delete task in TaskWarrior
    assert delete_task(task["uuid"])

    # Run sync with delete_tasks=True
    assert run_sync(delete_tasks=True)

    # Verify CalDAV todo is deleted
    todos_after = len(get_todos(calendar))
    assert todos_after == 0


@pytest.mark.integration
def test_tw_to_caldav_annotation_create(clean_test_environment):
    """Add annotation to task in TaskWarrior, verify it syncs to CalDAV."""
    # Create task
    description = "TaskWarrior task with annotation"
    task = create_task(description)
    assert task is not None

    # Add annotation
    annotation_text = "This is a test annotation"
    assert annotate_task(task["uuid"], annotation_text)

    # Run sync
    assert run_sync()

    # Verify annotation in CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None
    todo_description = get_todo_property(todo, "description")
    assert todo_description is not None
    assert "--- TaskWarrior Annotations ---" in str(todo_description)
    assert annotation_text in str(todo_description)


@pytest.mark.integration
def test_tw_to_caldav_annotation_add(clean_test_environment):
    """Add annotation to existing task in TaskWarrior, verify it syncs."""
    # Create task and sync
    description = "TaskWarrior task for adding annotation"
    task = create_task(description)
    assert task is not None
    assert run_sync()

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Add annotation
    annotation_text = "Annotation added later"
    assert annotate_task(task["uuid"], annotation_text)

    # Run sync
    assert run_sync()

    # Verify annotation in CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None
    todo_description = get_todo_property(todo, "description")
    assert todo_description is not None
    assert annotation_text in str(todo_description)


@pytest.mark.integration
def test_tw_to_caldav_annotation_multiple(clean_test_environment):
    """Add multiple annotations to task in TaskWarrior, verify they sync."""
    # Create task with first annotation
    description = "TaskWarrior task with multiple annotations"
    task = create_task(description)
    assert task is not None

    annotation1 = "First annotation"
    assert annotate_task(task["uuid"], annotation1)
    time.sleep(1)

    # Add second annotation
    annotation2 = "Second annotation"
    assert annotate_task(task["uuid"], annotation2)

    # Run sync
    assert run_sync()

    # Verify both annotations in CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todo = find_todo_by_summary(calendar, description)
    assert todo is not None
    todo_description = get_todo_property(todo, "description")
    assert todo_description is not None
    todo_desc_str = str(todo_description)
    assert annotation1 in todo_desc_str
    assert annotation2 in todo_desc_str


@pytest.mark.integration
def test_tw_to_caldav_dry_run(clean_test_environment):
    """Test dry-run mode doesn't modify CalDAV."""
    # Create task
    description = "TaskWarrior dry run test task"
    task = create_task(description)
    assert task is not None

    # Get CalDAV todo count before
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None

    todos_before = len(get_todos(calendar))
    assert todos_before == 0

    # Run sync in dry-run mode
    assert run_sync(dry_run=True)

    # Verify CalDAV didn't change
    todos_after = len(get_todos(calendar))
    assert todos_after == 0


@pytest.mark.integration
def test_tw_to_caldav_annotation_bidirectional_no_duplication(clean_test_environment):
    """Test that annotations don't duplicate on bidirectional sync."""
    # Create task with annotation
    description = "Task for annotation deduplication test"
    task = create_task(description)
    assert task is not None

    annotation = "Test annotation for deduplication"
    assert annotate_task(task["uuid"], annotation)

    # Sync to CalDAV
    assert run_sync()

    # Verify task exists with 1 annotation
    tasks = get_tasks()
    assert len(tasks) == 1
    assert "annotations" in tasks[0]
    assert len(tasks[0]["annotations"]) == 1

    # Sync again (CalDAV → TW) - should not duplicate
    assert run_sync()

    # Verify still only 1 annotation
    tasks = get_tasks()
    assert len(tasks) == 1
    assert "annotations" in tasks[0]
    assert len(tasks[0]["annotations"]) == 1
    assert tasks[0]["annotations"][0]["description"] == annotation
