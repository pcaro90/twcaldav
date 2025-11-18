# Testing Guide: TaskWarrior-CalDAV Bridge

## Overview

This document describes the testing strategy, setup, and procedures for the TaskWarrior-CalDAV bridge project.

## Testing Philosophy

- **Comprehensive Coverage**: Aim for >80% code coverage
- **Real-World Scenarios**: Test with actual CalDAV servers when possible
- **Multi-Client Support**: Validate that multiple TaskWarrior instances work correctly
- **Safety First**: Ensure dry-run mode prevents all changes
- **Edge Cases**: Test error conditions and boundary cases
- **Regression Prevention**: Add tests for every bug found

---

## Test Environment Setup

### TaskWarrior Test Environment

Create an isolated TaskWarrior environment for testing:

```bash
# Create test data directory
mkdir -p tests/fixtures/taskwarrior
export TASKDATA=tests/fixtures/taskwarrior

# Initialize TaskWarrior
task rc.confirmation=off rc.verbose=nothing status:pending list

# Add test tasks
task add "Test task 1" project:work
task add "Test task 2" project:personal due:tomorrow priority:H
```

**Key Points**:
- Use `TASKDATA` environment variable to isolate test data
- Disable confirmation prompts with `rc.confirmation=off`
- Create fresh test data for each test run
- Use `task rc.json.array=on export` for JSON output

### CalDAV Test Environment

#### Option 1: Mock CalDAV Server (Recommended for CI)

Use `caldav` library's test utilities or create mocks:

```python
from unittest.mock import Mock
import caldav

# Mock CalDAV client for unit tests
def create_mock_caldav_client():
    client = Mock(spec=caldav.DAVClient)
    principal = Mock()
    calendar = Mock()
    # ... configure mocks
    return client
```

#### Option 2: Radicale (Lightweight CalDAV Server)

Install and run Radicale for integration testing:

```bash
# Install Radicale
pip install radicale

# Run Radicale on localhost
radicale --config="" --storage-filesystem-folder=tests/fixtures/radicale
```

Configuration for tests:
- URL: `http://localhost:5232/user/calendar/`
- Username: `user`
- Password: `password`

#### Option 3: Nextcloud Test Instance

For testing against a production-like environment:
- Use Docker to spin up Nextcloud instance
- Configure test calendar
- Use separate credentials for testing

### Test Configuration File

Create `tests/fixtures/test_config.toml`:

```toml
[caldav]
url = "http://localhost:5232/user/"
username = "testuser"
password = "testpass"

[sync]
delete_tasks = false

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "work-calendar"

[[mappings]]
taskwarrior_project = "personal"
caldav_calendar = "personal-calendar"
```

---

## Test Categories

### 1. Unit Tests

Test individual components in isolation.

#### Configuration Tests (`tests/test_config.py`)
- [ ] Parse valid TOML configuration
- [ ] Reject invalid TOML syntax
- [ ] Validate required fields are present
- [ ] Validate CalDAV URL format
- [ ] Validate project-calendar mappings
- [ ] Handle missing config file gracefully
- [ ] Handle malformed mappings

#### TaskWarrior Wrapper Tests (`tests/test_taskwarrior.py`)
- [ ] Execute `task export` and parse JSON
- [ ] Filter tasks by project
- [ ] Filter tasks by status
- [ ] Create task with `task import`
- [ ] Create task with pre-assigned UUID
- [ ] Modify existing task
- [ ] Delete existing task
- [ ] Parse task annotations
- [ ] Add annotations to task
- [ ] Handle missing `task` binary
- [ ] Handle invalid task commands
- [ ] Handle empty result sets

#### CalDAV Client Tests (`tests/test_caldav_client.py`)
- [ ] Connect to CalDAV server
- [ ] Authenticate with valid credentials
- [ ] Reject invalid credentials
- [ ] List calendars
- [ ] Access calendar by name
- [ ] Fetch VTODOs from calendar
- [ ] Parse VTODO properties
- [ ] Create new VTODO
- [ ] Update existing VTODO
- [ ] Delete VTODO
- [ ] Handle connection errors
- [ ] Handle malformed VTODOs
- [ ] Respect dry-run mode

#### Field Mapper Tests (`tests/test_field_mapper.py`)
- [ ] Map TaskWarrior status to CalDAV STATUS
- [ ] Map CalDAV STATUS to TaskWarrior status
- [ ] Map TaskWarrior priority to CalDAV PRIORITY
- [ ] Map CalDAV PRIORITY to TaskWarrior priority
- [ ] Map TaskWarrior dates to CalDAV dates
- [ ] Map CalDAV dates to TaskWarrior dates
- [ ] Handle timezone conversions
- [ ] Map tags and project to CATEGORIES
- [ ] Map CATEGORIES to tags and project
- [ ] Handle missing optional fields
- [ ] Preserve unmapped fields

#### Sync Mapping Tests (`tests/test_sync_mapping.py`)
- [ ] Store TaskWarrior UUID in CalDAV
- [ ] Retrieve TaskWarrior UUID from CalDAV
- [ ] Link TaskWarrior task to CalDAV VTODO
- [ ] Find CalDAV VTODO by TaskWarrior UUID
- [ ] Find TaskWarrior task by CalDAV UID
- [ ] Handle unlinked tasks
- [ ] Handle missing UUIDs

#### Annotation Handler Tests (`tests/test_annotations.py`)
- [ ] Parse annotations from CalDAV DESCRIPTION
- [ ] Format annotations for CalDAV DESCRIPTION
- [ ] Preserve user description separate from annotations
- [ ] Handle empty annotations
- [ ] Handle multiple annotations
- [ ] Preserve annotation timestamps
- [ ] Handle annotations with special characters

---

### 2. Integration Tests

Test complete workflows with real or mocked backends.

#### Full Sync Tests (`tests/integration/test_full_sync.py`)

**Test Scenario: New Task in TaskWarrior**
1. Create task in TaskWarrior
2. Run sync
3. Verify task appears in CalDAV
4. Verify all fields mapped correctly
5. Verify UUID linking established

**Test Scenario: New Task in CalDAV**
1. Create VTODO in CalDAV
2. Run sync
3. Verify task appears in TaskWarrior
4. Verify all fields mapped correctly
5. Verify UUID linking established

**Test Scenario: Modify Task in TaskWarrior**
1. Create and sync task
2. Modify task in TaskWarrior
3. Run sync
4. Verify changes appear in CalDAV
5. Verify LAST-MODIFIED updated

**Test Scenario: Modify Task in CalDAV**
1. Create and sync task
2. Modify VTODO in CalDAV
3. Run sync
4. Verify changes appear in TaskWarrior
5. Verify modification timestamp preserved

**Test Scenario: Delete Task in TaskWarrior (deletion enabled)**
1. Create and sync task
2. Delete task in TaskWarrior
3. Run sync with deletion enabled
4. Verify task deleted from CalDAV

**Test Scenario: Delete Task in CalDAV (deletion enabled)**
1. Create and sync task
2. Delete VTODO in CalDAV
3. Run sync with deletion enabled
4. Verify task deleted from TaskWarrior

**Test Scenario: Deletion Disabled**
1. Create and sync task
2. Delete task on one side
3. Run sync with deletion disabled
4. Verify task NOT deleted on other side

**Test Scenario: Round-Trip Sync**
1. Create task in TaskWarrior
2. Run sync (TW → CD)
3. Modify in CalDAV
4. Run sync (CD → TW)
5. Modify in TaskWarrior
6. Run sync (TW → CD)
7. Verify data integrity throughout

---

### 3. Multi-Client Tests

Test scenarios with multiple TaskWarrior clients syncing to the same CalDAV backend.

#### Test Scenario: Two Clients Create Different Tasks
1. Client A creates task "Task A" in project "work"
2. Client A syncs (Task A → CalDAV)
3. Client B syncs (Task A → Client B)
4. Client B creates task "Task B" in project "work"
5. Client B syncs (Task B → CalDAV)
6. Client A syncs (Task B → Client A)
7. Verify both clients have both tasks

#### Test Scenario: Concurrent Modifications (Same Task)
1. Both clients have synced task "Task X"
2. Client A modifies description at T1
3. Client B modifies priority at T2 (T2 > T1)
4. Client B syncs first (priority change → CalDAV)
5. Client A syncs (description change → CalDAV, sees priority change)
6. Verify last-write-wins for timestamps
7. Verify both changes are preserved (if non-conflicting fields)

#### Test Scenario: Conflict Resolution (Same Field)
1. Both clients have synced task "Task Y"
2. Client A changes description to "Description A"
3. Client B changes description to "Description B"
4. Client A syncs first
5. Client B syncs second
6. Verify Client B's change wins (last-write-wins)
7. Verify conflict is logged

---

### 4. Edge Case Tests

Test error conditions and boundary cases.

#### Special Characters
- [ ] Task descriptions with unicode characters
- [ ] Task descriptions with special CalDAV characters
- [ ] Annotations with newlines
- [ ] Annotations with timestamps in description

#### Large Data Sets
- [ ] Sync 100+ tasks
- [ ] Tasks with 50+ annotations
- [ ] Very long task descriptions (>1000 chars)

#### Date/Time Handling
- [ ] Tasks with no due date
- [ ] Tasks with past due dates
- [ ] Tasks due in far future
- [ ] Timezone conversion edge cases
- [ ] Daylight saving time transitions

#### Network Issues
- [ ] CalDAV server unreachable
- [ ] CalDAV server times out
- [ ] CalDAV server returns 5xx errors
- [ ] Network disconnects mid-sync

#### Invalid Data
- [ ] Malformed VTODO in CalDAV
- [ ] Invalid task JSON from TaskWarrior
- [ ] Missing required fields
- [ ] Invalid UUIDs/UIDs

#### Project/Calendar Mapping
- [ ] Task in unmapped project (should be skipped)
- [ ] Task moved to unmapped project (should be deleted from CalDAV?)
- [ ] Task moved between mapped projects (should move calendars)
- [ ] VTODO in unmapped calendar (should be skipped)

---

### 5. Dry-Run Tests

Verify that dry-run mode makes NO changes.

#### Test All Operations in Dry-Run
- [ ] New task creation (both directions) - NO CHANGE
- [ ] Task modification (both directions) - NO CHANGE
- [ ] Task deletion (both directions) - NO CHANGE
- [ ] Verify logging shows what WOULD happen
- [ ] Verify no API calls made to CalDAV
- [ ] Verify no `task` commands executed (except reads)

---

## Running Tests

### Local Development Testing

#### Run Unit Tests Only
```bash
uv run pytest tests/ --ignore=tests/integration -v
```

#### Run Integration Tests (Docker-based)
```bash
# This runs all integration tests in isolated Docker containers
./scripts/run-integration-tests.sh
```

The integration test script will:
1. Start a Radicale CalDAV server in Docker
2. Configure TaskWarrior with required UDAs
3. Run all 51 integration tests (CalDAV→TW, TW→CalDAV, Multi-client)
4. Generate test results XML (`test-results.xml`)
5. Clean up all containers and volumes

**Integration Test Structure:**
- `tests/integration/test_caldav_to_tw.py` - 17 tests: CalDAV → TaskWarrior sync
- `tests/integration/test_tw_to_caldav.py` - 17 tests: TaskWarrior → CalDAV sync
- `tests/integration/test_multi_client.py` - 17 tests: Multi-client synchronization

Each file tests the same scenarios (create, modify, delete, tags, annotations, etc.) in its respective direction.

#### Run All Tests with Coverage
```bash
uv run pytest tests/ --ignore=tests/integration --cov=src/twcaldav --cov-report=html
```

#### Run Specific Unit Test
```bash
uv run pytest tests/test_config.py::test_parse_valid_config -v
```

#### Run Specific Integration Test File
```bash
# Note: Integration tests must run in Docker environment
# Modify docker-compose.test.yml to specify the file, then:
./scripts/run-integration-tests.sh
```

---

## Continuous Integration

### CI/CD Philosophy: Environment Parity

**Key Principle:** Local and CI testing environments are **identical** to ensure reproducibility.

Both local development and GitHub Actions CI use the **same Docker Compose setup** (`docker-compose.test.yml`):

✅ **Benefits:**
- 100% environment parity between local and CI
- CI failures can be reproduced locally exactly
- Single source of truth for test configuration
- Consistent TaskWarrior and CalDAV versions
- No configuration drift between environments

### GitHub Actions Workflow

The CI workflow (`.github/workflows/ci.yml`) has three jobs:

1. **Lint** - Runs Ruff linter and formatter checks
2. **Unit Tests** - Runs unit tests with coverage reporting
3. **Integration Tests** - Runs the same Docker Compose setup as local development:
   ```yaml
   integration-tests:
     runs-on: ubuntu-latest
     steps:
       - name: Checkout code
         uses: actions/checkout@v4
       
       - name: Run integration tests with Docker Compose
         run: bash scripts/run-integration-tests.sh
   ```

### Test Results

Both local and CI generate JUnit XML test results (`test-results.xml`) for:
- Test result parsing in CI
- Integration with test reporting tools
- Historical test trend analysis

### Verifying CI Parity

To verify that CI will pass before pushing:

```bash
# Run exactly what CI runs:
./scripts/run-integration-tests.sh

# If this passes locally, CI should pass too!
```

---

## Test Architecture

### Integration Test Design

The integration tests follow these principles:

1. **Independence**: Each test is self-contained and can run in any order
2. **Clean State**: Each test starts with a clean TaskWarrior + CalDAV environment
3. **Real Components**: Uses actual Radicale CalDAV server and TaskWarrior binary
4. **Comprehensive Coverage**: Tests all CRUD operations, edge cases, and sync directions
5. **Consistent Scenarios**: All three test files test the same 17 scenarios

### Helper Functions (`tests/integration/helpers.py`)

Centralized utility functions for:
- TaskWarrior operations (create, modify, delete, annotate tasks)
- CalDAV operations (create, modify, delete todos)
- Sync execution with various configurations
- Environment cleanup and setup

### Test Fixtures (`tests/integration/conftest.py`)

Provides pytest fixtures:
- `clean_test_environment`: Cleans both TW and CalDAV before each test
- `multi_client_setup`: Sets up two isolated TaskWarrior clients for multi-client tests

### Environment Configuration

All integration tests use environment variables defined in `docker-compose.test.yml`:
```bash
CALDAV_URL=http://radicale:5232/test-user/
CALDAV_USERNAME=test-user
CALDAV_PASSWORD=test-pass
CALDAV_CALENDAR_ID=test-calendar
TW_PROJECT=test
TASKDATA=/tmp/taskwarrior-test
```

---

## Test Data Management

### Fixtures

Store reusable test data in `tests/fixtures/`:
- `test_config.toml` - Sample configuration
- `sample_tasks.json` - TaskWarrior export examples
- `sample_vtodos.ics` - CalDAV VTODO examples

### Factories

Create test data factories for generating test objects:

```python
def create_test_task(uuid=None, description="Test task", project="work"):
    """Factory for creating test TaskWarrior tasks."""
    return {
        "uuid": uuid or str(uuid4()),
        "description": description,
        "project": project,
        "status": "pending",
        "entry": "20241117T100000Z",
    }

def create_test_vtodo(uid=None, summary="Test VTODO"):
    """Factory for creating test CalDAV VTODOs."""
    # ... create VTODO object
```

---

## Known Limitations

Document known limitations and acceptable behaviors:

1. **Timestamp Precision**: CalDAV timestamps may have different precision than TaskWarrior
2. **Timezone Handling**: May lose timezone information in some conversions
3. **Concurrent Modifications**: Last-write-wins may lose some changes in rare race conditions
4. **Large Annotations**: Very large annotation sets may impact performance
5. **CalDAV Server Variations**: Some features may not work with all CalDAV servers

---

## Reporting Test Failures

When reporting test failures, include:
1. Test name and file
2. Full error message and stack trace
3. Test environment (OS, Python version, CalDAV server)
4. Steps to reproduce
5. Expected vs. actual behavior

---

## Test Maintenance

- Review and update tests when features change
- Add regression tests for every bug found
- Keep test fixtures up to date
- Regularly run tests against new CalDAV server versions
- Monitor test execution time and optimize slow tests

---

## Future Testing Enhancements

- [ ] Performance benchmarking
- [ ] Load testing with thousands of tasks
- [ ] Chaos testing (random failures)
- [ ] Security testing (credential handling)
- [ ] Cross-platform testing (Linux, macOS, Windows)
- [ ] CalDAV server compatibility matrix
