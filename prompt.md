We are going to create a new bridge between TaskWarrior (TW) and CalDAV (CD)
servers, to bi-directionally sync both

## Requirements

- The bridge will be executed periodically (e.g. cron).
- A TW project is mapped to a CD calendar. Tasks without mapping (e.g. in
  non-mapped projects) should not be synced.
- When a new task is created in TW, it should be created in CD.
- When a new task is created in CD, it should be created in TW.
- When an existing task is modified in either platform, it should be updated in
  the other.
- When an existing task is deleted in either platform, it should be deleted in
  the other (ONLY if specified in config or executed with speficif parameter).
- Contemplate that many TaskWarrior clients (e.g. my two computers) may be
  syncing against the same CalDAV backend.
- Map as many compatible fields as posible.
- TW annotations should be stored in CD descriptions, in a format that allows to
  keep track of changes.
- Program should be very verbose when `-v/--verbose` is specified.
- Program should have a `-n/--dry-run` option to avoid making changes.
- Program should have extensive testing.

## Architecture decisions

- There should be a TOML config file in `~/.config/twcaldav/config.toml`, which
  should include, at least:
  - CalDAV URL + user + password
  - Project-calendar mapping
  - Default behavior for deleted tasks
- PENDING: CalDAV UIDs are not modifiable. TW UUIDs are not modifiable after
  creation (but they can be assigned when creating a task using `task import`).
  Using a local "mapping database" linking TW-UUID and CD-UIDs may break
  mutiple-TW setups. It's still pending to define a good linking strategy.

## Project-level decisions

- Implementation will be done in Python.
- Dependencies will be added with `uv`. `pyproject.toml` will NOT be edited
  manually, only through `uv`.
- Format will strictly follow `ruff`.
- Interaction with TW should be done exclusively through the `task` binary.
- CalDAV interaction will use the `caldav` Python library, see tutorial
  https://caldav.readthedocs.io/stable/tutorial.html

## Planning actions

- Create an implementation plan for this project, as a general guideline. Organize the implementation in Phases, do not detail tasks for each Phase in this file. This plan will be stored in PLAN.md
- Low-level tasks, both implemented and pending, will be stored in TODO.md
- Testing information will be stored in TESTING.md
