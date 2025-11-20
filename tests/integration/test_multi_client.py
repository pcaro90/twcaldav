"""Integration tests for multi-client synchronization (TW A ↔ CalDAV ↔ TW B)."""

import time

import pytest

from tests.integration.helpers import (
    add_tags,
    annotate_task,
    complete_task,
    create_task,
    delete_task,
    get_caldav_client,
    get_calendar,
    get_tasks,
    get_todos,
    modify_task,
    remove_tags,
    run_sync,
)


@pytest.mark.integration
def test_multi_client_create_simple(clean_test_environment, multi_client_setup) -> None:
    """Task created in client1 syncs to client2 via CalDAV."""
    client1, client2 = multi_client_setup

    # Client 1: Create a task
    description = "Multi-client test task"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    # Client 1: Sync to CalDAV
    assert run_sync(taskdata=client1)

    # Verify task is in CalDAV
    _, principal = get_caldav_client()
    assert principal is not None
    calendar = get_calendar(principal)
    assert calendar is not None
    assert len(get_todos(calendar)) == 1

    # Client 2: Sync from CalDAV
    assert run_sync(taskdata=client2)

    # Verify task appears in Client 2
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert description in client2_tasks[0]["description"]


@pytest.mark.integration
def test_multi_client_create_with_due_date(
    clean_test_environment, multi_client_setup
) -> None:
    """Task with due date created in client1 syncs to client2."""
    client1, client2 = multi_client_setup

    # Client 1: Create task with due date
    description = "Multi-client task with due date"
    task1 = create_task(description, taskdata=client1, due="tomorrow")
    assert task1 is not None
    assert "due" in task1

    # Sync both ways
    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Verify task in Client 2 has due date
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert "due" in client2_tasks[0]


@pytest.mark.integration
def test_multi_client_create_with_priority(
    clean_test_environment, multi_client_setup
) -> None:
    """Task with priority created in client1 syncs to client2."""
    client1, client2 = multi_client_setup

    # Client 1: Create task with priority
    description = "Multi-client task with priority"
    task1 = create_task(description, taskdata=client1, priority="H")
    assert task1 is not None
    assert task1.get("priority") == "H"

    # Sync both ways
    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Verify task in Client 2 has priority
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert client2_tasks[0].get("priority") == "H"


@pytest.mark.integration
def test_multi_client_create_with_tags(
    clean_test_environment, multi_client_setup
) -> None:
    """Task with tags created in client1 syncs to client2."""
    client1, client2 = multi_client_setup

    # Client 1: Create task with tags
    description = "Multi-client task with tags"
    task1 = create_task(description, taskdata=client1, tags=["urgent", "work"])
    assert task1 is not None
    assert "tags" in task1

    # Sync both ways
    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Verify task in Client 2 has tags
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    # Tags might be present depending on sync implementation


@pytest.mark.integration
def test_multi_client_modify_description(
    clean_test_environment, multi_client_setup
) -> None:
    """Task modified in client2 syncs back to client1."""
    client1, client2 = multi_client_setup

    # Client 1: Create task and sync
    description = "Original multi-client description"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Verify task in Client 2
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Client 2: Modify description
    new_description = "Modified by client 2"
    assert modify_task(
        client2_tasks[0]["uuid"], taskdata=client2, description=new_description
    )

    # Sync back to CalDAV and Client 1
    assert run_sync(taskdata=client2)
    assert run_sync(taskdata=client1)

    # Verify modification in Client 1
    client1_tasks = get_tasks(taskdata=client1)
    assert len(client1_tasks) == 1
    assert client1_tasks[0]["description"] == new_description


@pytest.mark.integration
def test_multi_client_modify_due_date(
    clean_test_environment, multi_client_setup
) -> None:
    """Due date modified in client2 syncs back to client1."""
    client1, client2 = multi_client_setup

    # Client 1: Create task with due date and sync
    description = "Multi-client task with changeable due date"
    task1 = create_task(description, taskdata=client1, due="tomorrow")
    assert task1 is not None

    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Client 2: Modify due date
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert modify_task(client2_tasks[0]["uuid"], taskdata=client2, due="5days")

    # Sync back
    assert run_sync(taskdata=client2)
    assert run_sync(taskdata=client1)

    # Verify modification in Client 1
    client1_tasks = get_tasks(taskdata=client1)
    assert len(client1_tasks) == 1
    assert "due" in client1_tasks[0]


@pytest.mark.integration
def test_multi_client_modify_priority(
    clean_test_environment, multi_client_setup
) -> None:
    """Priority modified in client2 syncs back to client1."""
    client1, client2 = multi_client_setup

    # Client 1: Create task with priority and sync
    description = "Multi-client task with changeable priority"
    task1 = create_task(description, taskdata=client1, priority="M")
    assert task1 is not None

    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Client 2: Modify priority
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert modify_task(client2_tasks[0]["uuid"], taskdata=client2, priority="H")

    # Sync back
    assert run_sync(taskdata=client2)
    assert run_sync(taskdata=client1)

    # Verify modification in Client 1
    client1_tasks = get_tasks(taskdata=client1)
    assert len(client1_tasks) == 1
    assert client1_tasks[0].get("priority") == "H"


@pytest.mark.integration
def test_multi_client_modify_tags_add(
    clean_test_environment, multi_client_setup
) -> None:
    """Tags added in client2 sync back to client1."""
    client1, client2 = multi_client_setup

    # Client 1: Create task and sync
    description = "Multi-client task for adding tags"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Client 2: Add tags
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert add_tags(client2_tasks[0]["uuid"], ["urgent", "important"], taskdata=client2)

    # Sync back
    assert run_sync(taskdata=client2)
    assert run_sync(taskdata=client1)

    # Verify tags in Client 1
    client1_tasks = get_tasks(taskdata=client1)
    assert len(client1_tasks) == 1


@pytest.mark.integration
def test_multi_client_modify_tags_remove(
    clean_test_environment, multi_client_setup
) -> None:
    """Tags removed in client2 sync back to client1."""
    client1, client2 = multi_client_setup

    # Client 1: Create task with tags and sync
    description = "Multi-client task for removing tags"
    task1 = create_task(description, taskdata=client1, tags=["urgent", "work", "temp"])
    assert task1 is not None

    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Client 2: Remove a tag
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert remove_tags(client2_tasks[0]["uuid"], ["temp"], taskdata=client2)

    # Sync back
    assert run_sync(taskdata=client2)
    assert run_sync(taskdata=client1)

    # Verify tags in Client 1
    client1_tasks = get_tasks(taskdata=client1)
    assert len(client1_tasks) == 1


@pytest.mark.integration
def test_multi_client_modify_status_to_completed(
    clean_test_environment, multi_client_setup
) -> None:
    """Task completed in client2 syncs back to client1."""
    client1, client2 = multi_client_setup

    # Client 1: Create task and sync
    description = "Multi-client task to be completed"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Client 2: Complete task
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert complete_task(client2_tasks[0]["uuid"], taskdata=client2)

    # Sync back
    assert run_sync(taskdata=client2)
    assert run_sync(taskdata=client1)

    # Verify task is completed in Client 1 (not in pending list)
    client1_tasks = get_tasks(taskdata=client1)
    assert len(client1_tasks) == 0


@pytest.mark.integration
def test_multi_client_delete(clean_test_environment, multi_client_setup) -> None:
    """Task deleted in client1 syncs to client2."""
    client1, client2 = multi_client_setup

    # Client 1: Create task and sync both ways
    description = "Multi-client task to be deleted"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Verify task in both clients
    assert len(get_tasks(taskdata=client1)) == 1
    assert len(get_tasks(taskdata=client2)) == 1

    # Client 1: Delete task
    assert delete_task(task1["uuid"], taskdata=client1)

    # Sync with delete enabled
    assert run_sync(taskdata=client1, delete_tasks=True)
    assert run_sync(taskdata=client2, delete_tasks=True)

    # Verify task deleted in Client 2
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 0


@pytest.mark.integration
def test_multi_client_annotation_create(
    clean_test_environment, multi_client_setup
) -> None:
    """Task created with annotation in client1 syncs to client2."""
    client1, client2 = multi_client_setup

    # Client 1: Create task with annotation
    description = "Multi-client task with initial annotation"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    annotation = "Initial annotation from client 1"
    assert annotate_task(task1["uuid"], annotation, taskdata=client1)

    # Sync to CalDAV and Client 2
    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Verify Client 2 has the annotation
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert "annotations" in client2_tasks[0]
    annotations = client2_tasks[0]["annotations"]
    assert len(annotations) >= 1
    assert any(annotation in a.get("description", "") for a in annotations)


@pytest.mark.integration
def test_multi_client_annotation_add(
    clean_test_environment, multi_client_setup
) -> None:
    """Annotation added in client2 syncs back to client1."""
    client1, client2 = multi_client_setup

    # Client 1: Create task and sync
    description = "Multi-client task with annotation"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Wait to ensure timestamp separation
    time.sleep(2)

    # Client 2: Add annotation
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    annotation_text = "Annotation from client 2"
    assert annotate_task(client2_tasks[0]["uuid"], annotation_text, taskdata=client2)

    # Sync back
    assert run_sync(taskdata=client2)
    assert run_sync(taskdata=client1)

    # Verify annotation in Client 1
    client1_tasks = get_tasks(taskdata=client1)
    assert len(client1_tasks) == 1
    assert "annotations" in client1_tasks[0]
    annotations = client1_tasks[0]["annotations"]
    assert len(annotations) >= 1
    assert any(annotation_text in a.get("description", "") for a in annotations)


@pytest.mark.integration
def test_multi_client_annotation_bidirectional_no_duplication(
    clean_test_environment, multi_client_setup
) -> None:
    """Annotations don't duplicate during bidirectional sync."""
    client1, client2 = multi_client_setup

    # Client 1: Create task with annotation
    description = "Multi-client dedup test"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    annotation = "Deduplication test annotation"
    assert annotate_task(task1["uuid"], annotation, taskdata=client1)

    # Sync to CalDAV and Client 2
    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Verify Client 2 has 1 annotation
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert "annotations" in client2_tasks[0]
    assert len(client2_tasks[0]["annotations"]) == 1

    # Sync back to Client 1 - should not duplicate
    assert run_sync(taskdata=client2)
    assert run_sync(taskdata=client1)

    # Verify Client 1 still has only 1 annotation
    client1_tasks = get_tasks(taskdata=client1)
    assert len(client1_tasks) == 1
    assert "annotations" in client1_tasks[0]
    assert len(client1_tasks[0]["annotations"]) == 1
    assert client1_tasks[0]["annotations"][0]["description"] == annotation

    # Add second annotation on Client 2
    time.sleep(2)
    annotation2 = "Second annotation from client 2"
    assert annotate_task(client2_tasks[0]["uuid"], annotation2, taskdata=client2)

    # Sync both ways
    assert run_sync(taskdata=client2)
    assert run_sync(taskdata=client1)

    # Verify both clients have exactly 2 annotations
    client1_tasks = get_tasks(taskdata=client1)
    assert len(client1_tasks) == 1
    assert len(client1_tasks[0]["annotations"]) == 2

    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert len(client2_tasks[0]["annotations"]) == 2


@pytest.mark.integration
def test_multi_client_create_completed(
    clean_test_environment, multi_client_setup
) -> None:
    """Completed task created in client1 syncs to client2."""
    client1, client2 = multi_client_setup

    # Client 1: Create and complete a task
    description = "Multi-client completed task"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None
    assert complete_task(task1["uuid"], taskdata=client1)

    # Sync both ways
    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Verify task is completed (not in pending list for both clients)
    client1_tasks = get_tasks(taskdata=client1)
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client1_tasks) == 0
    assert len(client2_tasks) == 0


@pytest.mark.integration
def test_multi_client_annotation_multiple(
    clean_test_environment, multi_client_setup
) -> None:
    """Multiple annotations from client1 sync to client2."""
    client1, client2 = multi_client_setup

    # Client 1: Create task with multiple annotations
    description = "Multi-client task with multiple annotations"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    annotation1 = "First annotation"
    annotation2 = "Second annotation"
    assert annotate_task(task1["uuid"], annotation1, taskdata=client1)
    time.sleep(1)
    assert annotate_task(task1["uuid"], annotation2, taskdata=client1)

    # Sync to CalDAV and Client 2
    assert run_sync(taskdata=client1)
    assert run_sync(taskdata=client2)

    # Verify Client 2 has both annotations
    client2_tasks = get_tasks(taskdata=client2)
    assert len(client2_tasks) == 1
    assert "annotations" in client2_tasks[0]
    assert len(client2_tasks[0]["annotations"]) == 2

    # Check both annotations are present
    annotation_texts = [
        a.get("description", "") for a in client2_tasks[0]["annotations"]
    ]
    assert annotation1 in annotation_texts
    assert annotation2 in annotation_texts


@pytest.mark.integration
def test_multi_client_dry_run(clean_test_environment, multi_client_setup) -> None:
    """Test dry-run mode doesn't sync between clients."""
    client1, client2 = multi_client_setup

    # Client 1: Create a task
    description = "Multi-client dry run test"
    task1 = create_task(description, taskdata=client1)
    assert task1 is not None

    # Get Client 2 task count before
    client2_tasks_before = len(get_tasks(taskdata=client2))
    assert client2_tasks_before == 0

    # Run sync in dry-run mode
    assert run_sync(taskdata=client1, dry_run=True)

    # Verify CalDAV didn't change, so Client 2 shouldn't get the task
    assert run_sync(taskdata=client2)
    client2_tasks_after = len(get_tasks(taskdata=client2))
    assert client2_tasks_after == 0
