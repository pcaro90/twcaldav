"""Task classification logic for synchronization."""

from twcaldav.caldav_client import VTodo
from twcaldav.config import Config
from twcaldav.logger import get_logger
from twcaldav.sync_comparator import TaskComparator
from twcaldav.sync_types import SyncAction, SyncDirection, TaskPair
from twcaldav.taskwarrior import Task


class SyncClassifier:
    """Classifies task pairs to determine sync actions."""

    def __init__(self, config: Config, comparator: TaskComparator) -> None:
        self.config = config
        self.comparator = comparator
        self.logger = get_logger()

    def classify(self, tw_task: Task | None, caldav_todo: VTodo | None) -> TaskPair:
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
            return self._handle_tw_only(tw_task)

        # Only CalDAV todo exists
        if caldav_todo and not tw_task:
            return self._handle_caldav_only(caldav_todo)

        # Both exist - check for modifications
        assert tw_task is not None and caldav_todo is not None
        return self._handle_both_exist(tw_task, caldav_todo)

    def _handle_tw_only(self, tw_task: Task) -> TaskPair:
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

    def _handle_caldav_only(self, caldav_todo: VTodo) -> TaskPair:
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

    def _handle_both_exist(self, tw_task: Task, caldav_todo: VTodo) -> TaskPair:
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

        # Check content first, then use timestamps for conflict resolution
        # Step 1: Compare actual content (not timestamps)
        content_equal = self.comparator.tasks_content_equal(tw_task, caldav_todo)

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

        return self._resolve_conflict(tw_task, caldav_todo)

    def _resolve_conflict(self, tw_task: Task, caldav_todo: VTodo) -> TaskPair:
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
                reason="Content differs, TaskWarrior more recent (CD has no timestamp)",
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
