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
    ):
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

            # Export all tasks for this project (all statuses)
            tasks = self.tw.export_tasks(project=project)
            # Filter out deleted tasks - we don't sync those
            for task in tasks:
                if task.status != "deleted":
                    tw_tasks[task.uuid] = task
                    # Build mapping from CalDAV UID to TW task
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
            # This handles the case where CalDAV todo exists but wasn't found in first loop
            tw_task = caldav_uid_to_tw_task.get(caldav_uid)
            if tw_task:
                # Found correlation - this CalDAV todo belongs to a TaskWarrior task
                pair = self._classify_task_pair(tw_task, caldav_todo)
            else:
                # No TaskWarrior task references this CalDAV todo
                pair = self._classify_task_pair(None, caldav_todo)
            task_pairs.append(pair)

        return task_pairs

    def _classify_task_pair(
        self, tw_task: Task | None, caldav_todo: VTodo | None
    ) -> TaskPair:
        """Classify a task pair and determine sync action.

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

        # Check for modifications
        tw_modified = tw_task.modified or tw_task.entry
        caldav_modified = caldav_todo.last_modified or caldav_todo.created

        if tw_modified is None and caldav_modified is None:
            # No timestamps - skip
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.SKIP,
                direction=None,
                reason="No modification timestamps",
            )

        if tw_modified is None:
            # Only CalDAV has timestamp - update TaskWarrior
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.UPDATE,
                direction=SyncDirection.CALDAV_TO_TW,
                reason="CalDAV more recent (TW has no timestamp)",
            )

        if caldav_modified is None:
            # Only TaskWarrior has timestamp - update CalDAV
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.UPDATE,
                direction=SyncDirection.TW_TO_CALDAV,
                reason="TaskWarrior more recent (CalDAV has no timestamp)",
            )

        # Both have timestamps - compare
        # Make timezone-naive for comparison
        tw_timestamp = (
            tw_modified.replace(tzinfo=None) if tw_modified.tzinfo else tw_modified
        )
        caldav_timestamp = (
            caldav_modified.replace(tzinfo=None)
            if caldav_modified.tzinfo
            else caldav_modified
        )

        # Allow small time difference (1 second) to avoid ping-pong
        time_diff = abs((tw_timestamp - caldav_timestamp).total_seconds())
        if time_diff <= 1:
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.SKIP,
                direction=None,
                reason="No changes (timestamps equal)",
            )

        if tw_timestamp > caldav_timestamp:
            return TaskPair(
                tw_task=tw_task,
                caldav_todo=caldav_todo,
                action=SyncAction.UPDATE,
                direction=SyncDirection.TW_TO_CALDAV,
                reason="TaskWarrior more recent",
            )
        return TaskPair(
            tw_task=tw_task,
            caldav_todo=caldav_todo,
            action=SyncAction.UPDATE,
            direction=SyncDirection.CALDAV_TO_TW,
            reason="CalDAV more recent",
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
                task = caldav_to_taskwarrior(pair.caldav_todo)
                task.uuid = pair.tw_task.uuid  # Preserve TaskWarrior UUID

                # Set the project based on which calendar this todo came from
                calendar_id = self.caldav_uid_to_calendar.get(pair.caldav_todo.uid)
                if calendar_id:
                    project = self.config.get_project_for_calendar(calendar_id)
                    if project:
                        task.project = project

                # Build modifications dict from task
                modifications = task.to_dict()
                # Remove uuid and entry from modifications (can't modify these)
                modifications.pop("uuid", None)
                modifications.pop("entry", None)

                # Ensure caldav_uid is included in modifications
                if not modifications.get("caldav_uid"):
                    modifications["caldav_uid"] = pair.caldav_todo.uid

                self.tw.modify_task(pair.tw_task.uuid, modifications)

            self.stats.tw_updated += 1

    def _execute_delete(self, pair: TaskPair) -> None:
        """Execute delete action.

        Args:
            pair: Task pair with DELETE action.
        """
        assert pair.tw_task is not None and pair.caldav_todo is not None

        if pair.direction == SyncDirection.TW_TO_CALDAV:
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
            self.logger.info(
                f"Deleting TaskWarrior task (CalDAV todo cancelled): "
                f"{pair.tw_task.uuid}"
            )

            if not self.dry_run:
                self.tw.delete_task(pair.tw_task.uuid)

            self.stats.tw_deleted += 1
