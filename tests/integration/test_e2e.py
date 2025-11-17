#!/usr/bin/env python3
"""
End-to-end integration test for TaskWarrior ↔ CalDAV synchronization.

This test runs in CI/CD with Docker containers for Radicale and TaskWarrior.
Configuration is provided via environment variables.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import caldav
from icalendar import Calendar, Todo

# Configuration from environment variables
CALDAV_URL = os.getenv("CALDAV_URL", "http://localhost:5232/test-user/")
CALDAV_USERNAME = os.getenv("CALDAV_USERNAME", "test-user")
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD", "test-pass")
CALDAV_CALENDAR_ID = os.getenv("CALDAV_CALENDAR_ID", "test-calendar")
TW_PROJECT = os.getenv("TW_PROJECT", "test")
TASKDATA = os.getenv("TASKDATA", None)


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_section(title):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_success(message):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message):
    """Print info message."""
    print(f"{Colors.YELLOW}→ {message}{Colors.RESET}")


def run_task_command(args):
    """Run a TaskWarrior command and return output."""
    cmd = ["task", *args]
    env = os.environ.copy()
    if TASKDATA:
        env["TASKDATA"] = TASKDATA
        cmd.insert(1, f"rc.data.location={TASKDATA}")

    print_info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.stdout, result.stderr, result.returncode


def get_tw_tasks():
    """Get all pending tasks from TaskWarrior test project."""
    stdout, _, _ = run_task_command(
        ["project:" + TW_PROJECT, "status:pending", "export"]
    )
    if not stdout.strip():
        return []
    return json.loads(stdout)


def create_tw_task(description, **kwargs):
    """Create a task in TaskWarrior."""
    args = ["add", description, "project:" + TW_PROJECT]

    if "due" in kwargs:
        args.append(f"due:{kwargs['due']}")
    if "priority" in kwargs:
        args.append(f"priority:{kwargs['priority']}")

    _stdout, stderr, code = run_task_command(args)

    if code != 0:
        print_error(f"Failed to create task: {stderr}")
        return None

    # Extract UUID from output
    tasks = get_tw_tasks()
    if tasks:
        # Return the most recently created task
        return max(tasks, key=lambda t: t.get("entry", ""))
    return None


def modify_tw_task(uuid, **modifications):
    """Modify a TaskWarrior task."""
    args = ["rc.confirmation=off", uuid, "modify"]

    for key, value in modifications.items():
        if key == "description":
            args.append(value)
        else:
            args.append(f"{key}:{value}")

    _stdout, _stderr, code = run_task_command(args)
    return code == 0


def complete_tw_task(uuid):
    """Mark a TaskWarrior task as done."""
    _stdout, _stderr, code = run_task_command(["rc.confirmation=off", uuid, "done"])
    return code == 0


def delete_tw_task(uuid):
    """Delete a TaskWarrior task."""
    _stdout, _stderr, code = run_task_command(["rc.confirmation=off", uuid, "delete"])
    return code == 0


def get_caldav_client():
    """Create CalDAV client connection."""
    try:
        client = caldav.DAVClient(
            url=CALDAV_URL, username=CALDAV_USERNAME, password=CALDAV_PASSWORD
        )
        principal = client.principal()
        return client, principal
    except Exception as e:
        print_error(f"Failed to connect to CalDAV: {e}")
        return None, None


def get_caldav_calendar(principal):
    """Get the test calendar."""
    try:
        calendars = principal.calendars()
        for cal in calendars:
            if cal.id == CALDAV_CALENDAR_ID or CALDAV_CALENDAR_ID in str(cal.url):
                return cal
        print_error(f"Calendar {CALDAV_CALENDAR_ID} not found")
        return None
    except Exception as e:
        print_error(f"Failed to get calendar: {e}")
        return None


def get_caldav_todos(calendar):
    """Get all todos from CalDAV calendar."""
    try:
        return calendar.todos()
    except Exception as e:
        print_error(f"Failed to get todos: {e}")
        return []


def create_caldav_todo(calendar, summary, **kwargs):
    """Create a todo in CalDAV calendar."""
    try:
        cal = Calendar()
        todo = Todo()

        todo.add("summary", summary)
        todo.add("status", kwargs.get("status", "NEEDS-ACTION"))
        todo.add("uid", f"test-{datetime.now().timestamp()}")

        if "due" in kwargs:
            todo.add("due", kwargs["due"])
        if "priority" in kwargs:
            todo.add("priority", kwargs["priority"])

        cal.add_component(todo)

        calendar.save_todo(cal.to_ical())
        print_success(f"Created CalDAV todo: {summary}")
        return True
    except Exception as e:
        print_error(f"Failed to create CalDAV todo: {e}")
        return False


def run_sync(dry_run=False):
    """Run the twcaldav sync."""
    # Create config file for CI environment
    config_path = Path("/tmp/twcaldav-ci-config.toml")
    config_content = f"""[caldav]
url = "{CALDAV_URL.rstrip("/")}"
username = "{CALDAV_USERNAME}"
password = "{CALDAV_PASSWORD}"

[[mappings]]
taskwarrior_project = "{TW_PROJECT}"
caldav_calendar = "{CALDAV_CALENDAR_ID}"

[sync]
delete_tasks = false
"""
    config_path.write_text(config_content)

    args = ["uv", "run", "twcaldav", "--config", str(config_path)]
    if dry_run:
        args.append("--dry-run")

    print_info(f"Running sync: {' '.join(args)}")
    env = os.environ.copy()
    if TASKDATA:
        env["TASKDATA"] = TASKDATA
    result = subprocess.run(args, cwd="/app" if Path("/app").exists() else ".", env=env)
    return result.returncode == 0


def clear_test_data():
    """Clear all test data from TaskWarrior and CalDAV."""
    print_section("CLEANUP: Clearing Test Data")

    # Clear TaskWarrior
    result = subprocess.run(
        [
            "task",
            f"rc.data.location={TASKDATA}" if TASKDATA else "",
            "project:test",
            "rc.verbose=nothing",
            "export",
        ],
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        tasks_to_clear = json.loads(result.stdout)
        print_info(f"Found {len(tasks_to_clear)} tasks to clear (all statuses)")

        for task in tasks_to_clear:
            uuid = task.get("uuid")
            status = task.get("status", "")
            if uuid:
                if status == "deleted":
                    continue
                if status == "completed":
                    subprocess.run(
                        [
                            "task",
                            f"rc.data.location={TASKDATA}" if TASKDATA else "",
                            "rc.confirmation=off",
                            "rc.verbose=nothing",
                            uuid,
                            "delete",
                        ],
                        capture_output=True,
                        text=True,
                    )
                else:
                    subprocess.run(
                        [
                            "task",
                            f"rc.data.location={TASKDATA}" if TASKDATA else "",
                            "rc.confirmation=off",
                            "rc.verbose=nothing",
                            uuid,
                            "delete",
                        ],
                        capture_output=True,
                        text=True,
                    )
    else:
        print_info("No tasks found to clear")

    # Purge deleted tasks
    subprocess.run(
        [
            "task",
            f"rc.data.location={TASKDATA}" if TASKDATA else "",
            "rc.confirmation=off",
            "rc.verbose=nothing",
            "purge",
        ],
        input="y\ny\n",
        capture_output=True,
        text=True,
    )

    tasks = get_tw_tasks()
    print_success(f"Cleared TaskWarrior test project (remaining pending: {len(tasks)})")

    # Clear CalDAV
    _client, principal = get_caldav_client()
    if principal:
        calendar = get_caldav_calendar(principal)
        if calendar:
            todos = get_caldav_todos(calendar)
            count = 0
            for todo in todos:
                try:
                    todo.delete()
                    count += 1
                except Exception as e:
                    print_error(f"Failed to delete todo: {e}")
            print_success(f"Cleared {count} todos from CalDAV")


def verify_initial_state():
    """Verify both TaskWarrior and CalDAV are empty."""
    print_section("PHASE 1: Verify Initial State")

    # Check TaskWarrior
    tasks = get_tw_tasks()
    if len(tasks) == 0:
        print_success("TaskWarrior test project is empty")
    else:
        print_error(f"TaskWarrior has {len(tasks)} tasks, expected 0")
        return False

    # Check CalDAV
    _client, principal = get_caldav_client()
    if not principal:
        return False

    calendar = get_caldav_calendar(principal)
    if not calendar:
        return False

    todos = get_caldav_todos(calendar)
    if len(todos) == 0:
        print_success("CalDAV calendar is empty")
    else:
        print_error(f"CalDAV has {len(todos)} todos, expected 0")
        return False

    return True


def test_tw_to_caldav_create():
    """Test creating tasks in TaskWarrior and syncing to CalDAV."""
    print_section("PHASE 2: TaskWarrior → CalDAV (Create)")

    # Create tasks
    print_info("Creating 3 tasks in TaskWarrior...")
    create_tw_task("Test task 1 - Simple pending")
    create_tw_task("Test task 2 - With due date", due="tomorrow", priority="H")
    task3 = create_tw_task("Test task 3 - Will be completed")

    if task3:
        complete_tw_task(task3["uuid"])

    # Verify in TW (only pending tasks)
    tasks = get_tw_tasks()
    print_success(f"TaskWarrior has {len(tasks)} pending tasks (1 completed)")

    # Run sync
    print_info("\nRunning sync...")
    if not run_sync():
        print_error("Sync failed")
        return False

    # Verify in CalDAV
    # Note: calendar.todos() may not return COMPLETED todos
    _client, principal = get_caldav_client()
    calendar = get_caldav_calendar(principal)
    todos = get_caldav_todos(calendar)

    if len(todos) == 2:
        print_success(f"✓ CalDAV now has {len(todos)} todos (expected 2 pending)")
        return True
    print_error(
        f"CalDAV has {len(todos)} todos, expected 2 (completed task may not be returned"
        " by calendar.todos())"
    )
    return False


def test_caldav_to_tw_create():
    """Test creating todos in CalDAV and syncing to TaskWarrior."""
    print_section("PHASE 3: CalDAV → TaskWarrior (Create)")

    # Get CalDAV client
    _client, principal = get_caldav_client()
    calendar = get_caldav_calendar(principal)

    # Create todos in CalDAV
    print_info("Creating 2 todos in CalDAV...")
    create_caldav_todo(calendar, "CalDAV test todo 1")
    create_caldav_todo(calendar, "CalDAV test todo 2 - High priority", priority=1)

    # Run sync
    print_info("\nRunning sync...")
    if not run_sync():
        print_error("Sync failed")
        return False

    # Verify in TaskWarrior (only pending tasks)
    tasks = get_tw_tasks()
    # Should have 2 original pending + 2 new from CalDAV = 4 pending
    if len(tasks) == 4:
        print_success(f"TaskWarrior now has {len(tasks)} pending tasks (expected 4)")
        return True
    print_error(f"TaskWarrior has {len(tasks)} pending tasks, expected 4")
    return False


def test_tw_to_caldav_modify():
    """Test modifying task in TaskWarrior and syncing to CalDAV."""
    print_section("PHASE 4: TaskWarrior → CalDAV (Modify)")

    # Get a task to modify
    tasks = get_tw_tasks()
    if not tasks:
        print_error("No tasks to modify")
        return False

    task = tasks[0]
    original_desc = task["description"]

    print_info(f"Modifying task: {original_desc}")
    modify_tw_task(task["uuid"], description=f"{original_desc} [MODIFIED]", due="2days")

    # Run sync
    print_info("\nRunning sync...")
    if not run_sync():
        print_error("Sync failed")
        return False

    print_success("Sync completed - verify CalDAV todo was updated")
    return True


def test_caldav_to_tw_modify():
    """Test modifying todo in CalDAV and syncing to TaskWarrior."""
    print_section("PHASE 5: CalDAV → TaskWarrior (Modify)")

    # Get CalDAV client
    _client, principal = get_caldav_client()
    calendar = get_caldav_calendar(principal)

    # Get a CalDAV todo to modify (one we created in phase 3)
    todos = get_caldav_todos(calendar)
    if not todos:
        print_error("No todos to modify")
        return False

    # Find a specific todo to modify
    todo_to_modify = None
    for todo in todos:
        try:
            ical = Calendar.from_ical(todo.data)
            for component in ical.walk():
                if component.name == "VTODO":
                    summary = str(component.get("summary", ""))
                    if "CalDAV test todo 1" in summary:
                        todo_to_modify = todo
                        break
            if todo_to_modify:
                break
        except Exception as e:
            print_error(f"Error parsing todo: {e}")
            continue

    if not todo_to_modify:
        print_error("Could not find 'CalDAV test todo 1' to modify")
        return False

    # Get the current data and modify it
    try:
        ical = Calendar.from_ical(todo_to_modify.data)
        original_summary = None

        for component in ical.walk():
            if component.name == "VTODO":
                original_summary = str(component.get("summary", ""))
                print_info(f"Modifying CalDAV todo: {original_summary}")

                # Modify the component
                component["summary"] = f"{original_summary} [MODIFIED IN CALDAV]"
                component["priority"] = 3  # Change priority
                break

        if not original_summary:
            print_error("Could not find VTODO component")
            return False

        # Update the todo with modified data using the caldav library's method
        todo_to_modify.data = ical.to_ical()
        todo_to_modify.save()

        print_success(f"Modified CalDAV todo: {original_summary} [MODIFIED IN CALDAV]")
    except Exception as e:
        print_error(f"Failed to modify CalDAV todo: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Run sync
    print_info("\nRunning sync...")
    if not run_sync():
        print_error("Sync failed")
        return False

    # Verify in TaskWarrior - check if the modification was synced
    tasks = get_tw_tasks()
    found_modified = False
    for task in tasks:
        if "[MODIFIED IN CALDAV]" in task.get("description", ""):
            found_modified = True
            print_success(f"✓ TaskWarrior task updated: {task['description']}")
            break

    if found_modified:
        return True

    print_error("Modified CalDAV todo was not synced to TaskWarrior")
    return False


def test_dry_run():
    """Test dry-run mode."""
    print_section("PHASE 6: Dry-Run Mode")

    # Create a new task
    print_info("Creating new task in TaskWarrior...")
    create_tw_task("Dry run test task - should not sync")

    get_tw_tasks()

    # Get CalDAV todo count before
    _client, principal = get_caldav_client()
    calendar = get_caldav_calendar(principal)
    todos_before = len(get_caldav_todos(calendar))

    # Run sync in dry-run mode
    print_info("\nRunning sync in DRY-RUN mode...")
    run_sync(dry_run=True)

    # Verify CalDAV didn't change
    todos_after = len(get_caldav_todos(calendar))

    if todos_after == todos_before:
        print_success("✓ CalDAV unchanged (dry-run worked)")
        return True
    print_error(f"CalDAV changed: {todos_before} → {todos_after} (dry-run failed)")
    return False


def main():
    """Run all integration tests."""
    print(f"\n{Colors.BOLD}TaskWarrior ↔ CalDAV Integration Test (CI/CD){Colors.RESET}")
    print(f"CalDAV URL: {CALDAV_URL}")
    print(f"Calendar: {CALDAV_CALENDAR_ID}")
    print(f"Project: {TW_PROJECT}")
    print(f"TaskData: {TASKDATA or 'default'}")

    # Always clean before running tests in CI
    clear_test_data()

    # Run tests
    tests = [
        ("Initial State", verify_initial_state),
        ("TW → CalDAV (Create)", test_tw_to_caldav_create),
        ("CalDAV → TW (Create)", test_caldav_to_tw_create),
        ("TW → CalDAV (Modify)", test_tw_to_caldav_modify),
        ("CalDAV → TW (Modify)", test_caldav_to_tw_modify),
        ("Dry-Run Mode", test_dry_run),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test '{name}' raised exception: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status:6}{Colors.RESET} {name}")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} passed{Colors.RESET}\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
