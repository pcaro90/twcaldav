# TODO List: TaskWarrior-CalDAV Bridge

Status Legend:
- `[ ]` Not started
- `[~]` In progress
- `[x]` Completed
- `[!]` Blocked

---

## Phase 1: Foundation & Configuration ✓ COMPLETED

### Project Structure
- [x] Create `src/twcaldav/` directory structure
- [x] Create `src/twcaldav/__init__.py`
- [x] Create `src/twcaldav/config.py` module
- [x] Create `src/twcaldav/logger.py` module
- [x] Create `src/twcaldav/cli.py` module
- [x] Create `tests/` directory structure

### Dependencies
- [x] Add `caldav` library via `uv add caldav`
- [x] Add `pytest` for testing via `uv add --dev pytest`
- [x] Add `ruff` for linting via `uv add --dev ruff`
- [x] Add `pytest-cov` for coverage reporting

### Configuration System
- [x] Define TOML configuration schema
- [x] Implement config file loader (`~/.config/twcaldav/config.toml`)
- [x] Implement config validation
- [x] Add support for CalDAV URL, username, password
- [x] Add support for project-calendar mappings
- [x] Add support for deletion behavior setting
- [x] Handle missing/invalid configuration gracefully
- [x] Add example config file in repository (config.toml.example)

### CLI Interface
- [x] Implement argument parser with argparse
- [x] Add `--verbose` / `-v` flag
- [x] Add `--dry-run` / `-n` flag
- [x] Add `--config` option for custom config path
- [x] Add `--help` documentation
- [x] Add version information
- [x] Add `--delete` / `--no-delete` flags for overriding config

### Logging System
- [x] Implement logger with configurable verbosity
- [x] Add DEBUG level for verbose mode
- [x] Add INFO level for normal operation
- [x] Add WARNING/ERROR levels for issues
- [x] Format log messages consistently
- [x] Log to stdout (not file for now)
- [x] Add color support for terminal output

### Testing - Phase 1
- [x] Test config file parsing (12 tests)
- [x] Test config validation
- [x] Test CLI argument parsing (8 tests)
- [x] Test logging at different levels (4 tests)
- [x] All 24 tests passing

---

## Phase 2: TaskWarrior Integration ✓ COMPLETED

### TaskWarrior Wrapper Module
- [x] Create `src/twcaldav/taskwarrior.py` module (362 lines)
- [x] Implement subprocess wrapper for `task` command
- [x] Add error handling for missing `task` binary
- [x] Add error handling for invalid task commands
- [x] Support custom TASKDATA directory via environment variable

### Task Reading
- [x] Implement `task export` JSON parsing
- [x] Implement filter by project
- [x] Implement filter by status (pending, completed, deleted)
- [x] Parse all relevant task fields (uuid, description, due, priority, etc.)
- [x] Parse task annotations
- [x] Handle empty result sets
- [x] Proper datetime handling with timezone support

### Task Creation
- [x] Implement task creation via `task import`
- [x] Support assigning custom UUID during creation
- [x] Map internal fields to TaskWarrior format
- [x] Handle task creation errors
- [x] Task dataclass with from_dict/to_dict methods

### Task Modification
- [x] Implement task modification via `task <uuid> modify`
- [x] Update description, due date, priority, etc.
- [x] Update tags and project
- [x] Handle modification errors
- [x] Support removing attributes (value=None)

### Task Deletion
- [x] Implement task deletion via `task <uuid> delete`
- [x] Add confirmation bypass for programmatic deletion (rc.confirmation=off)
- [x] Handle deletion errors

### Annotation Handling
- [x] Parse existing annotations from task export
- [x] Add new annotations to tasks
- [x] Preserve annotation timestamps
- [x] Format annotations consistently

### Testing - Phase 2
- [x] Test task export parsing (23 tests total)
- [x] Test task filtering by project
- [x] Test task creation with custom UUID
- [x] Test task modification
- [x] Test task deletion
- [x] Test annotation parsing and adding
- [x] Test error handling for invalid operations
- [x] Test Task dataclass serialization/deserialization
- [x] All 23 tests passing
- [x] 95% code coverage for taskwarrior.py

---

## Phase 3: CalDAV Integration

### CalDAV Client Setup
- [ ] Create `src/twcaldav/caldav_client.py` module
- [ ] Implement CalDAV client initialization
- [ ] Implement authentication with username/password
- [ ] Handle connection errors
- [ ] Handle authentication errors

### Calendar Operations
- [ ] Implement calendar discovery/listing
- [ ] Implement calendar access by name/URL
- [ ] Handle missing calendars gracefully
- [ ] Cache calendar references for performance

### VTODO Reading
- [ ] Implement fetching all VTODOs from a calendar
- [ ] Parse VTODO components
- [ ] Extract SUMMARY, DESCRIPTION, DUE, STATUS, PRIORITY
- [ ] Extract CATEGORIES (tags/project)
- [ ] Extract CREATED, LAST-MODIFIED timestamps
- [ ] Extract custom properties (X-TASKWARRIOR-UUID)
- [ ] Handle malformed VTODOs

### VTODO Creation
- [ ] Implement VTODO creation
- [ ] Set SUMMARY from task description
- [ ] Set DESCRIPTION from annotations
- [ ] Set DUE from task due date
- [ ] Set STATUS from task status
- [ ] Set PRIORITY from task priority
- [ ] Set CATEGORIES from tags
- [ ] Set custom X-TASKWARRIOR-UUID property
- [ ] Handle creation errors

### VTODO Updating
- [ ] Implement VTODO update
- [ ] Update all mapped fields
- [ ] Preserve fields we don't manage
- [ ] Handle update errors
- [ ] Respect LAST-MODIFIED timestamp

### VTODO Deletion
- [ ] Implement VTODO deletion
- [ ] Handle deletion errors
- [ ] Respect dry-run mode

### Field Mapping
- [ ] Create bidirectional field mapping functions
- [ ] Map TaskWarrior status to CalDAV STATUS
- [ ] Map TaskWarrior priority to CalDAV PRIORITY
- [ ] Map TaskWarrior dates to CalDAV dates (handle timezones)
- [ ] Map tags/project to CATEGORIES
- [ ] Handle missing/optional fields

### Testing - Phase 3
- [ ] Test CalDAV connection and authentication
- [ ] Test calendar discovery
- [ ] Test VTODO reading and parsing
- [ ] Test VTODO creation
- [ ] Test VTODO updating
- [ ] Test VTODO deletion
- [ ] Test field mapping functions
- [ ] Test error handling
- [ ] Test with mock CalDAV server or test instance

---

## Phase 4: Synchronization Strategy

### UUID/UID Linking (CRITICAL)
- [ ] Research CalDAV custom property support
- [ ] Test X-TASKWARRIOR-UUID property with target CalDAV servers
- [ ] Implement UUID/UID linking via custom property (preferred)
- [ ] Implement fallback: embedding UUID in DESCRIPTION (if needed)
- [ ] Create `src/twcaldav/sync_mapping.py` module
- [ ] Implement lookup: CalDAV UID → TaskWarrior UUID
- [ ] Implement lookup: TaskWarrior UUID → CalDAV UID
- [ ] Handle tasks that exist on only one side
- [ ] Document chosen approach in PLAN.md

### Field Mapping Implementation
- [ ] Create `src/twcaldav/field_mapper.py` module
- [ ] Implement TaskWarrior → CalDAV field mapping
- [ ] Implement CalDAV → TaskWarrior field mapping
- [ ] Handle optional/missing fields gracefully
- [ ] Document all field mappings

### Annotation Handling
- [ ] Design annotation format for CalDAV DESCRIPTION
- [ ] Implement annotation extraction from DESCRIPTION
- [ ] Implement annotation formatting for DESCRIPTION
- [ ] Preserve user description separate from annotations
- [ ] Handle annotation conflicts/merging

### Conflict Detection
- [ ] Compare LAST-MODIFIED timestamps
- [ ] Implement last-write-wins strategy
- [ ] Log conflicts for user awareness
- [ ] Handle missing timestamps

### Sync State Tracking
- [ ] Design stateless sync approach (no local DB)
- [ ] Use modification timestamps for state
- [ ] Handle first-time sync (all tasks are "new")
- [ ] Consider adding sync metadata to CalDAV

### Testing - Phase 4
- [ ] Test UUID/UID linking with various scenarios
- [ ] Test field mapping bidirectionally
- [ ] Test annotation preservation
- [ ] Test conflict detection
- [ ] Test with multiple TaskWarrior clients

---

## Phase 5: Bi-directional Sync Logic

### Core Sync Engine
- [ ] Create `src/twcaldav/sync_engine.py` module
- [ ] Implement main sync orchestration function
- [ ] Implement dry-run mode throughout

### Task Discovery
- [ ] Load all TaskWarrior tasks from mapped projects
- [ ] Load all CalDAV VTODOs from mapped calendars
- [ ] Build correlation map between TW and CD tasks
- [ ] Identify tasks that exist on only one side

### Task Classification
- [ ] Classify tasks as: new, modified, deleted, unchanged
- [ ] Use timestamps for modification detection
- [ ] Handle missing tasks (deletions vs. filtering)
- [ ] Log classification results

### TaskWarrior → CalDAV Sync
- [ ] Create new VTODOs for new TW tasks
- [ ] Update existing VTODOs for modified TW tasks
- [ ] Delete VTODOs for deleted TW tasks (if configured)
- [ ] Handle sync errors gracefully
- [ ] Log all operations

### CalDAV → TaskWarrior Sync
- [ ] Create new TW tasks for new VTODOs
- [ ] Update existing TW tasks for modified VTODOs
- [ ] Delete TW tasks for deleted VTODOs (if configured)
- [ ] Handle sync errors gracefully
- [ ] Log all operations

### Deletion Handling
- [ ] Check configuration for deletion behavior
- [ ] Implement deletion when enabled
- [ ] Skip deletion when disabled
- [ ] Log deletion actions clearly
- [ ] Respect CLI parameter override for deletions

### Project-Calendar Mapping
- [ ] Enforce project-calendar mapping from config
- [ ] Skip tasks in unmapped projects
- [ ] Skip VTODOs in unmapped calendars
- [ ] Handle tasks moved between projects
- [ ] Log skipped tasks

### Edge Case Handling
- [ ] Handle task moved to unmapped project
- [ ] Handle task moved between mapped projects
- [ ] Handle network failures mid-sync
- [ ] Handle partial sync scenarios
- [ ] Handle CalDAV server errors
- [ ] Implement retry logic where appropriate

### Sync Summary
- [ ] Count new/modified/deleted tasks
- [ ] Log summary at end of sync
- [ ] Report any errors or warnings
- [ ] Suggest actions for user if needed

### Testing - Phase 5
- [ ] Test full sync cycle (TW → CD → TW)
- [ ] Test new task creation both directions
- [ ] Test task modification sync both directions
- [ ] Test task deletion sync (when enabled)
- [ ] Test project-calendar mapping enforcement
- [ ] Test dry-run mode (no changes made)
- [ ] Test edge cases (moved projects, network failures)
- [ ] Test with multiple TW clients
- [ ] Test concurrent modifications

---

## Phase 6: Testing & Validation

### Test Infrastructure
- [ ] Set up test TaskWarrior data directory
- [ ] Set up test CalDAV server or mock
- [ ] Create test fixtures for common scenarios
- [ ] Create helper functions for test setup/teardown

### Unit Tests
- [ ] Complete unit tests for config module
- [ ] Complete unit tests for TaskWarrior wrapper
- [ ] Complete unit tests for CalDAV client
- [ ] Complete unit tests for field mapper
- [ ] Complete unit tests for sync mapping
- [ ] Complete unit tests for sync engine

### Integration Tests
- [ ] Test full sync with real/mock CalDAV server
- [ ] Test multi-client scenarios
- [ ] Test conflict resolution
- [ ] Test all sync directions

### Edge Case Tests
- [ ] Test with special characters in task descriptions
- [ ] Test with large numbers of annotations
- [ ] Test with missing optional fields
- [ ] Test with invalid dates
- [ ] Test with network interruptions
- [ ] Test with CalDAV server errors

### Coverage
- [ ] Measure code coverage
- [ ] Aim for >80% coverage
- [ ] Add tests for uncovered critical paths

### Documentation - Testing
- [ ] Complete TESTING.md with setup instructions
- [ ] Document test scenarios
- [ ] Document how to run tests
- [ ] Document known limitations

---

## Phase 7: Documentation & Polish

### README
- [ ] Write project description
- [ ] Add installation instructions
- [ ] Add quick start guide
- [ ] Add configuration examples
- [ ] Add usage examples
- [ ] Add troubleshooting section
- [ ] Add contributing guidelines (if open source)

### Configuration Documentation
- [ ] Document complete config.toml format
- [ ] Provide example configurations
- [ ] Document all available options
- [ ] Add security best practices

### Usage Examples
- [ ] Document first-time setup
- [ ] Document manual sync execution
- [ ] Document cron job setup
- [ ] Document dry-run usage
- [ ] Document handling common scenarios

### Code Polish
- [ ] Run ruff formatter on all code
- [ ] Fix any linting issues
- [ ] Add docstrings to all functions
- [ ] Add type hints where helpful
- [ ] Remove debug code
- [ ] Clean up commented code

### Performance
- [ ] Profile sync performance
- [ ] Optimize slow operations if needed
- [ ] Add caching where appropriate
- [ ] Test with large task sets

### Final Checks
- [ ] Test on clean system
- [ ] Verify all dependencies are in pyproject.toml
- [ ] Verify ruff compliance
- [ ] Review all documentation
- [ ] Test example configurations

---

## Future Enhancements (Post-Release)

These are not part of the initial implementation but could be added later:

- [ ] Support for task dependencies
- [ ] Support for recurring tasks
- [ ] Web UI for configuration
- [ ] Support for other task managers (Todoist, etc.)
- [ ] Conflict resolution strategies beyond last-write-wins
- [ ] Backup/restore functionality
- [ ] Performance metrics and reporting
- [ ] Plugin system for custom field mappings

---

## Notes

- Update this file as tasks are completed
- Add new tasks as they are discovered
- Move completed phases to an archive section if needed
- Reference specific line numbers when fixing bugs
