"""Synchronization engine for TaskWarrior and CalDAV."""

from dataclasses import dataclass
from enum import Enum

from twcaldav.caldav_client import CalDAVClient, VTodo
from twcaldav.config import Config
from twcaldav.field_mapper import caldav_to_taskwarrior, taskwarrior_to_caldav
from twcaldav.logger import get_logger
from twcaldav.taskwarrior import Task, TaskWarrior


class SyncAction(Enum):
    """Represents possible sync actions."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SKIP = "skip"


class SyncDirection(Enum):
    """Represents sync direction."""

    TW_TO_CALDAV = "tw_to_caldav"
    CALDAV_TO_TW = "caldav_to_tw"


@dataclass
class TaskPair:
    """Represents a pair of related tasks from TaskWarrior and CalDAV."""

    tw_task: Task | None
    caldav_todo: VTodo | None
    action: SyncAction
    direction: SyncDirection | None
    reason: str


@dataclass
class SyncStats:
    """Statistics for a sync operation."""

    tw_created: int = 0
    tw_updated: int = 0
    tw_deleted: int = 0
    caldav_created: int = 0
    caldav_updated: int = 0
    caldav_deleted: int = 0
    skipped: int = 0
    errors: int = 0

    def __str__(self) -> str:
        """Format sync statistics for display."""
        lines = [
            "Sync Statistics:",
            (
                f"  TaskWarrior: {self.tw_created} created, "
                f"{self.tw_updated} updated, {self.tw_deleted} deleted"
            ),
            (
                f"  CalDAV: {self.caldav_created} created, "
                f"{self.caldav_updated} updated, {self.caldav_deleted} deleted"
            ),
            f"  Skipped: {self.skipped}",
            f"  Errors: {self.errors}",
        ]
        return "\n".join(lines)


class SyncEngine:
    """Synchronization engine for TaskWarrior and CalDAV."""

    def __init__(
        self,
        config: Config,
        tw: TaskWarrior,
        caldav_client: CalDAVClient,
        dry_run: bool = False,
    ) -> None:
        """Initialize sync engine.

        Args:
            config: Configuration object.
            tw: TaskWarrior client.
            caldav_client: CalDAV client.
            dry_run: If True, don't make any changes.
        """
        self.config = config
        self.tw = tw
        self.caldav = caldav_client
        self.dry_run = dry_run
        self.logger = get_logger()
        self.stats = SyncStats()
        self.caldav_uid_to_calendar: dict[
            str, str
        ] = {}  # Maps CalDAV UID to calendar ID

    def sync(self) -> SyncStats:
        """Perform bi-directional synchronization.

        Returns:
            Sync statistics.
        """
        self.logger.info("Starting synchronization...")
        if self.dry_run:
            self.logger.info("DRY RUN MODE: No changes will be made")

        try:
            # Discovery phase
            task_pairs = self._discover_and_correlate()

            # Classify and execute sync actions
            for pair in task_pairs:
                self._execute_sync_action(pair)

            self.logger.info("Synchronization complete")
            self.logger.info(str(self.stats))

        except Exception as e:
            self.logger.error(f"Sync failed: {e}")
            self.stats.errors += 1
            raise

        return self.stats

    def _discover_and_correlate(self) -> list[TaskPair]:
        """Discover tasks and correlate them between TaskWarrior and CalDAV.

        Returns:
            List of task pairs with sync actions.
        """
        self.logger.debug("Discovering tasks...")

        # Collect all tasks from TaskWarrior in mapped projects
        tw_tasks: dict[str, Task] = {}
        caldav_uid_to_tw_task: dict[str, Task] = {}  # Map CalDAV UID to TW task

        for mapping in self.config.mappings:
            project = mapping.taskwarrior_project
            self.logger.debug(f"Loading TaskWarrior tasks from project: {project}")

            # Export all tasks for this project (all statuses including deleted)
            # We need deleted tasks to detect deletions and sync them to CalDAV
            tasks = self.tw.export_tasks(project=project)
            for task in tasks:
                tw_tasks[task.uuid] = task
                # Build mapping from CalDAV UID to TW task (including deleted ones)
                if task.caldav_uid:
                    caldav_uid_to_tw_task[task.caldav_uid] = task

        self.logger.info(f"Found {len(tw_tasks)} TaskWarrior tasks in mapped projects")

        # Collect all VTODOs from CalDAV in mapped calendars
        caldav_todos: dict[str, VTodo] = {}
        caldav_uid_to_calendar: dict[str, str] = {}  # Map CalDAV UID to calendar ID

        for mapping in self.config.mappings:
            calendar_id = mapping.caldav_calendar
            self.logger.debug(f"Loading CalDAV todos from calendar ID: {calendar_id}")
            todos = self.caldav.get_todos(calendar_id)

            for todo in todos:
                caldav_todos[todo.uid] = todo
                caldav_uid_to_calendar[todo.uid] = (
                    calendar_id  # Store which calendar this todo is from
                )

        self.logger.info(f"Found {len(caldav_todos)} CalDAV todos in mapped calendars")

        # Store calendar mapping for later use
        self.caldav_uid_to_calendar = caldav_uid_to_calendar

        # Correlate tasks and classify actions
        task_pairs = []

        # Process TaskWarrior tasks
        processed_caldav_uids: set[str] = set()
        for _tw_uuid, tw_task in tw_tasks.items():
            # Look for corresponding CalDAV todo via UDA
            caldav_todo = None
            if tw_task.caldav_uid:
                caldav_todo = caldav_todos.get(tw_task.caldav_uid)
                if caldav_todo:
                    processed_caldav_uids.add(caldav_todo.uid)

            pair = self._classify_task_pair(tw_task, caldav_todo)
            task_pairs.append(pair)

        # Process CalDAV todos that don't have TaskWarrior counterparts
        for caldav_uid, caldav_todo in caldav_todos.items():
            # Skip if already processed via TaskWarrior UDA
            if caldav_uid in processed_caldav_uids:
                continue

            # Check if there's a TaskWarrior task that references this CalDAV UID
            # This handles the case where CalDAV todo exists but wasn't found in the
            # first loop
            tw_task = caldav_uid_to_tw_task.get(caldav_uid)
            if tw_task:
                # Found correlation - this CalDAV todo belongs to a TaskWarrior task
                pair = self._classify_task_pair(tw_task, caldav_todo)
            else:
                # No TaskWarrior task references this CalDAV todo
                pair = self._classify_task_pair(None, caldav_todo)
            task_pairs.append(pair)

        return task_pairs

    def _tasks_content_equal(self, tw_task: Task, caldav_todo: VTodo) -> bool:
        """Compare task content (not timestamps) to detect real changes.

        Args:
            tw_task: TaskWarrior task.
            caldav_todo: CalDAV todo.

        Returns:
            True if content is identical, False if any field differs.
        """
        # Compare description/summary
        if tw_task.description != caldav_todo.summary:
            self.logger.debug(
                f"Content differs: description/summary - "
                f"TW:'{tw_task.description}' vs CD:'{caldav_todo.summary}'"
            )
            return False

        # Compare status
        status_map = {
            "pending": "NEEDS-ACTION",
            "completed": "COMPLETED",
            "deleted": "CANCELLED",
            "waiting": "NEEDS-ACTION",
            "recurring": "NEEDS-ACTION",
        }
        expected_caldav_status = status_map.get(tw_task.status, "NEEDS-ACTION")
        actual_caldav_status = caldav_todo.status or "NEEDS-ACTION"
        if expected_caldav_status != actual_caldav_status:
            self.logger.debug(
                f"Content differs: status - "
                f"TW:'{tw_task.status}' ({expected_caldav_status}) vs "
                f"CD:{actual_caldav_status}"
            )
            return False

        # Compare due date (handle None and timezone differences)
        tw_due = tw_task.due.replace(tzinfo=None) if tw_task.due else None
        cd_due = caldav_todo.due.replace(tzinfo=None) if caldav_todo.due else None
        if tw_due != cd_due:
            self.logger.debug(f"Content differs: due - TW:{tw_due} vs CD:{cd_due}")
            return False

        # Compare priority
        priority_map = {"H": 1, "M": 5, "L": 9}
        expected_caldav_priority = (
            priority_map.get(tw_task.priority) if tw_task.priority else None
        )
        if expected_caldav_priority != caldav_todo.priority:
            self.logger.debug(
                f"Content differs: priority - "
                f"TW:{tw_task.priority} ({expected_caldav_priority}) vs "
                f"CD:{caldav_todo.priority}"
            )
            return False

        # Compare tags/categories
        tw_tags = set(tw_task.tags or [])
        cd_categories = set(caldav_todo.categories or [])
        if tw_tags != cd_categories:
            self.logger.debug(
                f"Content differs: tags/categories - TW:{tw_tags} vs CD:{cd_categories}"
            )
            return False

        # Compare annotations (stored in CalDAV description)
        from twcaldav.field_mapper import _format_description_with_annotations

        expected_caldav_description = _format_description_with_annotations(tw_task)
        actual_caldav_description = caldav_todo.description

        # Normalize None vs empty string
        expected_desc = expected_caldav_description or ""
        actual_desc = actual_caldav_description or ""

        if expected_desc != actual_desc:
            self.logger.debug(
                f"Content differs: annotations/description - "
                f"TW has {len(expected_desc)} chars vs CD has {len(actual_desc)} chars"
            )
            return False

        return True

    def _classify_task_pair(
        self, tw_task: Task | None, caldav_todo: VTodo | None
    ) -> TaskPair:
        """Classify a task pair and determine sync action.

        Uses hybrid approach:
        1. First checks if content differs (fields comparison)
        2. If content is identical, skip update (no spurious updates)
        3. If content differs, use Last Write Wins (timestamp) for conflict resolution

        Args:
            tw_task: TaskWarrior task (or None if not exists).
            caldav_todo: CalDAV todo (or None if not exists).

        Returns:
            TaskPair with classified action.
        """
        # Both missing - should not happen
        if tw_task is None and caldav_todo is None:
            return TaskPair(
                tw_task=None,
                caldav_todo=None,
                action=SyncAction.SKIP,
                direction=None,
                reason="Both tasks missing",
            )

        # Only TaskWarrior task exists
        if tw_task and not caldav_todo:
            if tw_task.status == "deleted":
                return TaskPair(
                    tw_task=tw_task,
                    caldav_todo=None,
                    action=SyncAction.SKIP,
                    direction=None,
                    reason="TaskWarrior task deleted, no CalDAV todo to remove",
                )

            # Check if TW task has caldav_uid - if so, CalDAV todo was deleted
            if tw_task.caldav_uid:
                if self.config.sync.delete_tasks:
                    return TaskPair(
                        tw_task=tw_task,
                        caldav_todo=None,
                        action=SyncAction.DELETE,
                        direction=SyncDirection.CALDAV_TO_TW,
                        reason="CalDAV todo deleted externally",
                    )
                return TaskPair(
                    tw_task=tw_task,
                    caldav_todo=None,
                    action=SyncAction.SKIP,
                    direction=None,
                    reason="CalDAV todo deleted externally, but deletion disabled",
                )

            # New TaskWarrior task without caldav_uid
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=None,
                action=SyncAction.CREATE,
                direction=SyncDirection.TW_TO_CALDAV,
                reason="New TaskWarrior task",
            )

        # Only CalDAV todo exists
        if caldav_todo and not tw_task:
            if caldav_todo.status == "CANCELLED":
                return TaskPair(
                    tw_task=None,
                    caldav_todo=caldav_todo,
                    action=SyncAction.SKIP,
                    direction=None,
                    reason="CalDAV todo cancelled, no TaskWarrior task to remove",
                )
            return TaskPair(
                tw_task=None,
                caldav_todo=caldav_todo,
                action=SyncAction.CREATE,
                direction=SyncDirection.CALDAV_TO_TW,
                reason="New CalDAV todo",
            )

        # Both exist - check for modifications
        assert tw_task is not None and caldav_todo is not None

        # Handle deletion
        if tw_task.status == "deleted" and caldav_todo.status != "CANCELLED":
            if self.config.sync.delete_tasks:
                return TaskPair(
                    tw_task=tw_task,
                    caldav_todo=caldav_todo,
                    action=SyncAction.DELETE,
                    direction=SyncDirection.TW_TO_CALDAV,
                    reason="TaskWarrior task deleted",
                )
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.SKIP,
                direction=None,
                reason="TaskWarrior task deleted, but deletion disabled",
            )

        if caldav_todo.status == "CANCELLED" and tw_task.status != "deleted":
            if self.config.sync.delete_tasks:
                return TaskPair(
                    tw_task=tw_task,
                    caldav_todo=caldav_todo,
                    action=SyncAction.DELETE,
                    direction=SyncDirection.CALDAV_TO_TW,
                    reason="CalDAV todo cancelled",
                )
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.SKIP,
                direction=None,
                reason="CalDAV todo cancelled, but deletion disabled",
            )

        # Both deleted/cancelled - skip
        if tw_task.status == "deleted" and caldav_todo.status == "CANCELLED":
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.SKIP,
                direction=None,
                reason="Both deleted",
            )

        # Hybrid approach: Check content first, then use timestamps for conflict resolution
        # Step 1: Compare actual content (not timestamps)
        content_equal = self._tasks_content_equal(tw_task, caldav_todo)

        if content_equal:
            # Content is identical - no update needed regardless of timestamps
            # This prevents spurious updates due to TW's import behavior
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.SKIP,
                direction=None,
                reason="No changes (content identical)",
            )

        # Step 2: Content differs - use Last Write Wins for conflict resolution
        self.logger.debug(
            f"Content differs between TW:{tw_task.uuid} and CD:{caldav_todo.uid}"
        )

        tw_modified = tw_task.modified or tw_task.entry
        caldav_modified = caldav_todo.last_modified or caldav_todo.created

        if tw_modified is None and caldav_modified is None:
            # No timestamps but content differs - prefer TaskWarrior
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.UPDATE,
                direction=SyncDirection.TW_TO_CALDAV,
                reason="Content differs, no timestamps (preferring TW)",
            )

        if tw_modified is None:
            # Only CalDAV has timestamp - update TaskWarrior
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.UPDATE,
                direction=SyncDirection.CALDAV_TO_TW,
                reason="Content differs, CalDAV more recent (TW has no timestamp)",
            )

        if caldav_modified is None:
            # Only TaskWarrior has timestamp - update CalDAV
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.UPDATE,
                direction=SyncDirection.TW_TO_CALDAV,
                reason="Content differs, TaskWarrior more recent (CalDAV has no timestamp)",
            )

        # Both have timestamps - compare (Last Write Wins)
        # Make timezone-naive for comparison
        tw_timestamp = (
            tw_modified.replace(tzinfo=None) if tw_modified.tzinfo else tw_modified
        )
        caldav_timestamp = (
            caldav_modified.replace(tzinfo=None)
            if caldav_modified.tzinfo
            else caldav_modified
        )

        # Log timestamp comparisons for debugging
        time_diff = abs((tw_timestamp - caldav_timestamp).total_seconds())
        self.logger.debug(
            f"Timestamp comparison - TW:{tw_timestamp.isoformat()} "
            f"CD:{caldav_timestamp.isoformat()} "
            f"diff:{time_diff}s"
        )

        if tw_timestamp > caldav_timestamp:
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.UPDATE,
                direction=SyncDirection.TW_TO_CALDAV,
                reason="Content differs, TaskWarrior more recent",
            )
        return TaskPair(
            tw_task=tw_task,
            caldav_todo=caldav_todo,
            action=SyncAction.UPDATE,
            direction=SyncDirection.CALDAV_TO_TW,
            reason="Content differs, CalDAV more recent",
        )

    def _execute_sync_action(self, pair: TaskPair) -> None:
        """Execute the sync action for a task pair.

        Args:
            pair: Task pair with classified action.
        """
        if pair.action == SyncAction.SKIP:
            self.logger.debug(
                f"Skipping: {pair.reason} - "
                f"TW:{pair.tw_task.uuid if pair.tw_task else 'None'} / "
                f"CD:{pair.caldav_todo.uid if pair.caldav_todo else 'None'}"
            )
            self.stats.skipped += 1
            return

        try:
            if pair.action == SyncAction.CREATE:
                self._execute_create(pair)
            elif pair.action == SyncAction.UPDATE:
                self._execute_update(pair)
            elif pair.action == SyncAction.DELETE:
                self._execute_delete(pair)

        except Exception as e:
            self.logger.error(
                f"Error executing {pair.action.value} for "
                f"TW:{pair.tw_task.uuid if pair.tw_task else 'None'} / "
                f"CD:{pair.caldav_todo.uid if pair.caldav_todo else 'None'}: {e}"
            )
            self.stats.errors += 1

    def _execute_create(self, pair: TaskPair) -> None:
        """Execute create action.

        Args:
            pair: Task pair with CREATE action.
        """
        if pair.direction == SyncDirection.TW_TO_CALDAV:
            assert pair.tw_task is not None
            self.logger.info(
                f"Creating CalDAV todo from TaskWarrior task: {pair.tw_task.uuid}"
            )

            if not self.dry_run:
                # Convert TaskWarrior task to CalDAV todo
                vtodo = taskwarrior_to_caldav(pair.tw_task)

                # Get the calendar for this task's project
                calendar_name = self.config.get_calendar_for_project(
                    pair.tw_task.project or ""
                )
                if not calendar_name:
                    self.logger.warning(
                        f"No calendar mapping for project: {pair.tw_task.project}"
                    )
                    self.stats.skipped += 1
                    return

                self.caldav.create_todo(calendar_name, vtodo)

                # Update TaskWarrior task with CalDAV UID
                self.tw.modify_task(pair.tw_task.uuid, {"caldav_uid": vtodo.uid})
                self.logger.debug(
                    f"Set caldav_uid UDA to {vtodo.uid} on task {pair.tw_task.uuid}"
                )

            self.stats.caldav_created += 1

        elif pair.direction == SyncDirection.CALDAV_TO_TW:
            assert pair.caldav_todo is not None
            self.logger.info(
                f"Creating TaskWarrior task from CalDAV todo: {pair.caldav_todo.uid}"
            )

            if not self.dry_run:
                # Convert CalDAV todo to TaskWarrior task
                task = caldav_to_taskwarrior(pair.caldav_todo)

                # Set the project based on which calendar this todo came from
                calendar_id = self.caldav_uid_to_calendar.get(pair.caldav_todo.uid)
                if calendar_id:
                    project = self.config.get_project_for_calendar(calendar_id)
                    if project:
                        task.project = project

                self.tw.create_task(task)

            self.stats.tw_created += 1

    def _execute_update(self, pair: TaskPair) -> None:
        """Execute update action.

        Args:
            pair: Task pair with UPDATE action.
        """
        assert pair.tw_task is not None and pair.caldav_todo is not None

        if pair.direction == SyncDirection.TW_TO_CALDAV:
            self.logger.info(
                f"Updating CalDAV todo from TaskWarrior: {pair.tw_task.uuid}"
            )

            if not self.dry_run:
                # Convert TaskWarrior task to CalDAV todo (preserving UID)
                vtodo = taskwarrior_to_caldav(pair.tw_task)
                vtodo.uid = pair.caldav_todo.uid  # Preserve CalDAV UID

                # Get the calendar
                calendar_name = self.config.get_calendar_for_project(
                    pair.tw_task.project or ""
                )
                if not calendar_name:
                    self.logger.warning(
                        f"No calendar mapping for project: {pair.tw_task.project}"
                    )
                    self.stats.skipped += 1
                    return

                self.caldav.update_todo(calendar_name, vtodo)

            self.stats.caldav_updated += 1

        elif pair.direction == SyncDirection.CALDAV_TO_TW:
            self.logger.info(
                f"Updating TaskWarrior task from CalDAV: {pair.caldav_todo.uid}"
            )

            if not self.dry_run:
                # Convert CalDAV todo to TaskWarrior task (preserving UUID)
                # Pass existing task to enable annotation deduplication
                task = caldav_to_taskwarrior(
                    pair.caldav_todo, existing_task=pair.tw_task
                )
                task.uuid = pair.tw_task.uuid  # Preserve TaskWarrior UUID
                task.entry = pair.tw_task.entry  # Preserve entry timestamp

                # Set the project based on which calendar this todo came from
                calendar_id = self.caldav_uid_to_calendar.get(pair.caldav_todo.uid)
                if calendar_id:
                    project = self.config.get_project_for_calendar(calendar_id)
                    if project:
                        task.project = project

                # Ensure caldav_uid is set
                if not task.caldav_uid:
                    task.caldav_uid = pair.caldav_todo.uid

                # Use import_tasks to update - this properly handles all fields
                # including annotations, unlike modify_task
                self.tw.import_tasks([task])

            self.stats.tw_updated += 1

    def _execute_delete(self, pair: TaskPair) -> None:
        """Execute delete action.

        Args:
            pair: Task pair with DELETE action.
        """
        assert pair.tw_task is not None  # TW task must always exist for DELETE

        if pair.direction == SyncDirection.TW_TO_CALDAV:
            assert (
                pair.caldav_todo is not None
            )  # CalDAV todo must exist for TW→CalDAV delete
            self.logger.info(
                f"Deleting CalDAV todo (TaskWarrior task deleted): "
                f"{pair.caldav_todo.uid}"
            )

            if not self.dry_run:
                # Get the calendar
                calendar_name = self.config.get_calendar_for_project(
                    pair.tw_task.project or ""
                )
                if not calendar_name:
                    self.logger.warning(
                        f"No calendar mapping for project: {pair.tw_task.project}"
                    )
                    self.stats.skipped += 1
                    return

                self.caldav.delete_todo(calendar_name, pair.caldav_todo.uid)

            self.stats.caldav_deleted += 1

        elif pair.direction == SyncDirection.CALDAV_TO_TW:
            # CalDAV todo may be None if it was deleted externally (not just cancelled)
            caldav_info = (
                f" (caldav_uid: {pair.tw_task.caldav_uid})"
                if pair.tw_task.caldav_uid
                else ""
            )
            self.logger.info(
                f"Deleting TaskWarrior task (CalDAV todo deleted){caldav_info}: "
                f"{pair.tw_task.uuid}"
            )

            if not self.dry_run:
                self.tw.delete_task(pair.tw_task.uuid)

            self.stats.tw_deleted += 1
