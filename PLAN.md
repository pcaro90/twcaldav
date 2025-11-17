# Implementation Plan: TaskWarrior-CalDAV Bridge

## Overview

This document outlines the phased implementation plan for the bi-directional sync bridge between TaskWarrior and CalDAV servers.

## Phase 1: Foundation & Configuration

**Objective**: Establish the basic project infrastructure, configuration handling, and CLI interface.

**Key Deliverables**:
- Project structure with proper module organization
- TOML configuration file parser for `~/.config/twcaldav/config.toml`
- Logging system with verbosity levels
- CLI argument parser supporting `--verbose`, `--dry-run`, and other flags
- Configuration validation and error handling

**Dependencies to Add**:
- `caldav` - CalDAV client library
- `tomli` or `tomllib` (Python 3.11+) - TOML parsing
- Testing framework (pytest)

**Success Criteria**:
- Configuration file can be loaded and validated
- CLI arguments are properly parsed
- Logging works at different verbosity levels
- All code passes ruff formatting checks

---

## Phase 2: TaskWarrior Integration

**Objective**: Create a reliable interface to TaskWarrior through the `task` binary.

**Key Deliverables**:
- TaskWarrior wrapper module that executes `task` commands
- Functions to export tasks in JSON format
- Functions to filter tasks by project
- Functions to create tasks using `task import` (allows UUID assignment)
- Functions to modify existing tasks
- Functions to delete tasks
- Parser for TaskWarrior JSON export format
- Handling of TaskWarrior annotations

**Technical Considerations**:
- Use subprocess to execute `task` binary
- Parse JSON output from `task export`
- Handle task creation with pre-assigned UUIDs via `task import`
- Ensure proper escaping of task attributes
- Handle TaskWarrior errors gracefully

**Success Criteria**:
- Can read all tasks from specified projects
- Can create new tasks with custom UUIDs
- Can modify existing tasks
- Can delete tasks
- All TaskWarrior operations are properly logged

---

## Phase 3: CalDAV Integration

**Objective**: Implement CalDAV client functionality for VTODO management.

**Key Deliverables**:
- CalDAV client initialization with authentication
- Calendar discovery and listing
- VTODO (task) creation
- VTODO reading and parsing
- VTODO updating
- VTODO deletion
- Field mapping between CalDAV properties and internal representation

**Technical Considerations**:
- Use the `caldav` Python library
- Handle authentication securely (credentials from config)
- Parse VTODO components properly
- Map CalDAV fields to internal task representation
- Handle CalDAV-specific errors and connection issues
- Support different CalDAV server implementations

**Success Criteria**:
- Can connect to CalDAV server and authenticate
- Can list calendars
- Can create, read, update, and delete VTODOs
- All CalDAV operations respect dry-run mode
- Proper error handling for network issues

---

## Phase 4: Synchronization Strategy

**Objective**: Design and implement the core synchronization logic and solve the UUID/UID linking problem.

**Key Deliverables**:
- UUID/UID linking mechanism (CRITICAL ARCHITECTURAL DECISION)
- Conflict detection strategy using modification timestamps
- Field mapping between TaskWarrior and CalDAV formats
- Annotation handling in CalDAV descriptions
- Sync state tracking without local database

**Critical Architectural Decision - UUID/UID Linking**:

The challenge: CalDAV UIDs and TaskWarrior UUIDs are both immutable, and we need to support multiple TaskWarrior clients syncing with the same CalDAV backend without a local mapping database.

**Proposed Solutions**:

1. **Store TW UUID in CalDAV extended property** (RECOMMENDED)
   - Store TaskWarrior UUID in a custom X-TASKWARRIOR-UUID property
   - Use CalDAV UID as-is (server-generated or client-generated)
   - Lookup tasks by searching for X-TASKWARRIOR-UUID property
   - Pros: Clean separation, no collisions, works with multiple clients
   - Cons: Requires CalDAV server to support custom properties

2. **Deterministic UID derivation**
   - Generate CalDAV UID from TaskWarrior UUID (e.g., `tw-{uuid}@domain`)
   - Pros: No storage needed, deterministic
   - Cons: May not work if CalDAV server generates its own UIDs

3. **Embed mapping in CalDAV description**
   - Store TW UUID in a hidden marker in the description field
   - Pros: Universal compatibility
   - Cons: Clutters description, fragile parsing

**Recommendation**: Attempt Solution 1 (custom property), fall back to Solution 3 if not supported.

**Field Mapping Strategy**:

| TaskWarrior Field | CalDAV VTODO Property | Notes |
|-------------------|----------------------|-------|
| uuid | X-TASKWARRIOR-UUID | Custom property |
| description | SUMMARY | Main task title |
| annotations | DESCRIPTION | Formatted with timestamps |
| due | DUE | Date/time |
| status | STATUS | pending→NEEDS-ACTION, completed→COMPLETED |
| priority | PRIORITY | H→1, M→5, L→9 |
| project | CATEGORIES | Or use separate calendars |
| tags | CATEGORIES | Comma-separated |
| modified | LAST-MODIFIED | Timestamp |
| entry | CREATED | Timestamp |

**Annotation Format in CalDAV Description**:
```
[User description if any]

--- TaskWarrior Annotations ---
[2024-11-17 10:30:00] First annotation
[2024-11-17 11:45:00] Second annotation
```

**Success Criteria**:
- UUID/UID linking works reliably across multiple clients
- All compatible fields are mapped bidirectionally
- Annotations are preserved and trackable
- Conflict detection identifies which side changed most recently

---

## Phase 5: Bi-directional Sync Logic

**Objective**: Implement the full synchronization algorithm for both directions.

**Key Deliverables**:
- TaskWarrior → CalDAV sync engine
- CalDAV → TaskWarrior sync engine
- Deletion handling (with configuration respect)
- Dry-run mode implementation
- Project-to-calendar mapping enforcement
- Error recovery and partial sync handling

**Sync Algorithm**:

1. **Initialization**:
   - Load configuration
   - Connect to CalDAV
   - Load project-calendar mappings

2. **Discovery Phase**:
   - Get all TW tasks in mapped projects
   - Get all CalDAV VTODOs in mapped calendars
   - Build correlation between TW and CD tasks using UUID/UID linking

3. **Classification Phase**:
   For each side (TW and CD), classify tasks as:
   - New (exists on one side only)
   - Modified (exists on both, modified timestamp differs)
   - Deleted (was in mapping, now missing)
   - Unchanged (exists on both, timestamps match)

4. **Conflict Resolution**:
   - If modified on both sides, use latest timestamp (last-write-wins)
   - Log conflicts for user awareness

5. **Sync Execution** (respecting dry-run mode):
   - Create new tasks on target side
   - Update modified tasks on older side
   - Delete tasks if configured (and both sides agree it's deleted)
   - Update sync state

6. **Verification**:
   - Log summary of changes
   - Report any errors or skipped tasks

**Edge Cases to Handle**:
- Task moved to unmapped project (should it be deleted from CalDAV?)
- Task moved between mapped projects (move between calendars)
- Multiple TW clients making simultaneous changes
- Network failures mid-sync
- CalDAV server limits/throttling

**Success Criteria**:
- New tasks sync in both directions
- Modified tasks sync to the other side
- Deletions are handled per configuration
- Dry-run mode makes no actual changes
- All edge cases are handled gracefully
- Comprehensive logging of all actions

---

## Phase 6: Testing & Validation

**Objective**: Ensure reliability through comprehensive testing.

**Key Deliverables**:
- Unit tests for each module
- Integration tests for sync scenarios
- Multi-client scenario tests
- Edge case tests
- Test documentation in TESTING.md
- CI/CD setup (optional but recommended)

**Test Categories**:

1. **Unit Tests**:
   - Configuration parsing
   - TaskWarrior command generation
   - CalDAV client operations
   - Field mapping functions
   - UUID/UID linking logic

2. **Integration Tests**:
   - Full sync cycle (TW → CD → TW)
   - New task creation on both sides
   - Task modification sync
   - Task deletion sync
   - Project-calendar mapping enforcement

3. **Multi-Client Tests**:
   - Two TW clients syncing to same CalDAV
   - Conflict resolution scenarios
   - Concurrent modifications

4. **Edge Case Tests**:
   - Network failures
   - Invalid CalDAV responses
   - Missing configuration values
   - Tasks with special characters
   - Large annotation sets

**Testing Infrastructure**:
- Mock CalDAV server or use test CalDAV instance
- Isolated TaskWarrior data directory for tests
- Fixtures for common test scenarios
- Automated test execution

**Success Criteria**:
- >80% code coverage
- All critical paths tested
- Multi-client scenarios validated
- Edge cases handled properly
- Tests pass consistently

---

## Phase 7: Documentation & Polish

**Objective**: Finalize documentation and prepare for release.

**Key Deliverables**:
- Complete README with setup instructions
- Configuration file format documentation
- Usage examples and common workflows
- Troubleshooting guide
- Code cleanup and final ruff compliance check
- Performance optimization if needed

**Documentation Sections**:

1. **README.md**:
   - Project description and features
   - Installation instructions
   - Quick start guide
   - Configuration examples
   - Usage examples
   - Troubleshooting

2. **Configuration Guide**:
   - Complete config.toml format
   - All available options
   - Project-calendar mapping examples
   - Security considerations

3. **Usage Examples**:
   - First-time setup
   - Manual sync execution
   - Cron job setup
   - Dry-run testing
   - Handling specific scenarios

**Success Criteria**:
- Clear, comprehensive documentation
- New users can set up and use the tool
- All code follows ruff formatting
- Ready for production use

---

## Implementation Timeline

**Estimated Effort by Phase**:
- Phase 1: 1-2 days
- Phase 2: 2-3 days
- Phase 3: 2-3 days
- Phase 4: 3-4 days (includes architectural decision)
- Phase 5: 4-5 days
- Phase 6: 3-4 days
- Phase 7: 1-2 days

**Total Estimated Time**: 16-23 days of focused development

**Critical Path**: Phases 1 → 2 → 3 → 4 → 5 are sequential. Phase 6 can run in parallel with later phases. Phase 7 is final.

---

## Risk Mitigation

**High-Risk Items**:
1. **UUID/UID linking in multi-client setup**: Resolve early in Phase 4
2. **CalDAV server compatibility**: Test with multiple servers
3. **Race conditions with multiple clients**: Careful testing in Phase 6
4. **Data loss during sync**: Implement dry-run and extensive logging

**Mitigation Strategies**:
- Prototype critical components early
- Test with real CalDAV servers (Nextcloud, Radicale, etc.)
- Always support dry-run mode for safety
- Comprehensive logging for debugging
- Clear error messages for users

---

## Success Metrics

The project will be considered successful when:
- ✓ Bi-directional sync works reliably
- ✓ Multiple TaskWarrior clients can sync to same CalDAV
- ✓ All configured fields are synced properly
- ✓ Annotations are preserved
- ✓ Deletions are handled per configuration
- ✓ Dry-run mode prevents accidental changes
- ✓ Comprehensive test coverage
- ✓ Clear documentation for setup and usage
- ✓ Zero data loss in normal operation
