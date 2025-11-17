"""Field mapping between TaskWarrior and CalDAV."""

from datetime import datetime
from uuid import uuid4

from twcaldav.caldav_client import VTodo
from twcaldav.taskwarrior import Task


def taskwarrior_to_caldav(task: Task) -> VTodo:
    """Convert TaskWarrior task to CalDAV VTodo.

    Args:
        task: TaskWarrior Task object.

    Returns:
        CalDAV VTodo object.
    """
    # Generate CalDAV UID if needed (based on TaskWarrior UUID)
    uid = f"tw-{task.uuid}@twcaldav"

    # Map status
    # TaskWarrior: pending, completed, deleted, waiting, recurring
    # CalDAV: NEEDS-ACTION, COMPLETED, CANCELLED, IN-PROCESS
    status_map = {
        "pending": "NEEDS-ACTION",
        "completed": "COMPLETED",
        "deleted": "CANCELLED",
        "waiting": "NEEDS-ACTION",
        "recurring": "NEEDS-ACTION",
    }
    status = status_map.get(task.status, "NEEDS-ACTION")

    # Map priority
    # TaskWarrior: H (high), M (medium), L (low), or None
    # CalDAV: 1-9 where 1 is highest, 5 is medium, 9 is lowest
    priority = None
    if task.priority:
        priority_map = {"H": 1, "M": 5, "L": 9}
        priority = priority_map.get(task.priority, 5)

    # Format description with annotations
    description = _format_description_with_annotations(task)

    # Combine tags and project into categories
    categories = []
    if task.project:
        categories.append(task.project)
    if task.tags:
        categories.extend(task.tags)

    return VTodo(
        uid=uid,
        summary=task.description,
        status=status,
        description=description,
        due=task.due,
        priority=priority,
        categories=categories if categories else None,
        created=task.entry,
        last_modified=task.modified,
        taskwarrior_uuid=task.uuid,
    )


def caldav_to_taskwarrior(vtodo: VTodo, existing_task: Task | None = None) -> Task:
    """Convert CalDAV VTodo to TaskWarrior task.

    Args:
        vtodo: CalDAV VTodo object.
        existing_task: Existing TaskWarrior task to update (optional).
                      If provided, preserves entry timestamp and UUID.

    Returns:
        TaskWarrior Task object.
    """
    # Use TaskWarrior UUID from custom property, or existing task, or generate new
    if vtodo.taskwarrior_uuid:
        tw_uuid = vtodo.taskwarrior_uuid
    elif existing_task:
        tw_uuid = existing_task.uuid
    else:
        tw_uuid = str(uuid4())

    # Map status
    # CalDAV: NEEDS-ACTION, COMPLETED, CANCELLED, IN-PROCESS
    # TaskWarrior: pending, completed, deleted
    status_map = {
        "NEEDS-ACTION": "pending",
        "COMPLETED": "completed",
        "CANCELLED": "deleted",
        "IN-PROCESS": "pending",
    }
    status = status_map.get(vtodo.status or "NEEDS-ACTION", "pending")

    # Map priority
    # CalDAV: 1-9 (1=highest, 5=medium, 9=lowest)
    # TaskWarrior: H, M, L
    priority = None
    if vtodo.priority is not None:
        if vtodo.priority <= 3:
            priority = "H"
        elif vtodo.priority <= 6:
            priority = "M"
        else:
            priority = "L"

    # Parse description for annotations
    # If no description field, use summary as description
    desc_field = vtodo.description if vtodo.description else None
    description, annotations = _parse_description_for_annotations(desc_field)

    # If we got empty description from parsing and no annotations, use summary
    if not description and not annotations:
        description = vtodo.summary

    # Extract project from categories (first category is project)
    project = None
    tags = []
    if vtodo.categories:
        project = vtodo.categories[0]
        tags = vtodo.categories[1:] if len(vtodo.categories) > 1 else []

    # Preserve entry timestamp from existing task or use created
    entry = existing_task.entry if existing_task else (vtodo.created or datetime.now())

    return Task(
        uuid=tw_uuid,
        description=description,
        status=status,
        entry=entry,
        modified=vtodo.last_modified or datetime.now(),
        project=project,
        due=vtodo.due,
        priority=priority,
        tags=tags if tags else None,
        annotations=annotations if annotations else None,
    )


def _format_description_with_annotations(task: Task) -> str | None:
    """Format task description with annotations for CalDAV.

    Annotations are appended to the description with special markers.

    Args:
        task: TaskWarrior Task object.

    Returns:
        Formatted description string, or None if no description/annotations.
    """
    if not task.annotations:
        return None

    lines = []
    lines.append("--- TaskWarrior Annotations ---")

    for annotation in task.annotations:
        entry = annotation.get("entry", "")
        desc = annotation.get("description", "")
        # Format: [timestamp] description
        if entry:
            # Parse timestamp if it's a string
            if isinstance(entry, str):
                try:
                    dt = datetime.fromisoformat(entry)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, AttributeError):
                    timestamp = entry
            else:
                timestamp = entry.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{timestamp}] {desc}")
        else:
            lines.append(desc)

    return "\n".join(lines)


def _parse_description_for_annotations(
    description: str | None,
) -> tuple[str, list[dict] | None]:
    """Parse CalDAV description to extract annotations.

    Args:
        description: CalDAV description field.

    Returns:
        Tuple of (user_description, annotations_list).
        User description is empty string if only annotations exist.
        Annotations list is None if no annotations found.
    """
    if not description:
        return "", None

    # Check for annotation marker
    marker = "--- TaskWarrior Annotations ---"
    if marker not in description:
        # No annotations, return as-is
        return description, None

    # Split on marker
    parts = description.split(marker)
    user_desc = parts[0].strip()

    # Parse annotations
    annotations = []
    if len(parts) > 1:
        annotation_text = parts[1].strip()
        for line in annotation_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Parse format: [timestamp] description
            if line.startswith("[") and "]" in line:
                end_bracket = line.index("]")
                timestamp = line[1:end_bracket]
                desc = line[end_bracket + 1 :].strip()

                # Convert timestamp back to TaskWarrior format
                try:
                    dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    entry = dt.strftime("%Y%m%dT%H%M%SZ")
                except ValueError:
                    entry = timestamp

                annotations.append({"entry": entry, "description": desc})
            else:
                # Annotation without timestamp
                annotations.append({"description": line})

    return user_desc, annotations if annotations else None
