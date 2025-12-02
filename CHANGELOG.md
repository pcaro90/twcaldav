## v1.1.2 (2025-12-02)

### Fix

- improve sync logging

## v1.1.1 (2025-12-02)

### Fix

- fix sync edge case

## v1.1.0 (2025-11-22)

### Feat

- add TaskWarrior end ↔ CalDAV COMPLETED field mapping
- add TaskWarrior wait ↔ CalDAV X-TASKWARRIOR-WAIT field mapping

## v1.0.0 (2025-11-22)

### Feat

- add TaskWarrior scheduled ↔ CalDAV DTSTART field mapping
- improve sync algorithm
- improve cli
- improve cli use
- sync also completed tasks
- sync TaskWarrior annotations
- change sync method
- implement Phase 7
- implement Phase 5
- implement Phase 4
- implement Phase 3
- implement Phase 2
- implement Phase 1

### Fix

- add debug timestamp info
- use docker compose
- improve tags sync logic
- improve deletion logic
- set project in CD->TW sync

### Refactor

- **sync**: extract TaskComparator and SyncClassifier from SyncEngine
