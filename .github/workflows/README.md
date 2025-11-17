# CI/CD Integration Testing

This project uses automated integration testing in CI/CD pipelines with Docker containers.

## Overview

The CI/CD workflow runs three types of tests:

1. **Lint** - Code quality checks with Ruff
2. **Unit Tests** - Fast, isolated tests (118 tests)
3. **Integration Tests** - Full end-to-end tests with real CalDAV server and TaskWarrior

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  GitHub Actions Pipeline                 │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Radicale   │  │ TaskWarrior  │  │  Test Runner │  │
│  │  (CalDAV)    │◄─┤    + uv +    │◄─┤   (Python)   │  │
│  │  Container   │  │   twcaldav   │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│       :5232           /taskdata        test_e2e.py      │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Running Tests Locally

### Prerequisites

- Docker and Docker Compose installed
- Or: TaskWarrior, Python 3.13, and uv installed

### Option 1: Docker Compose (Recommended)

Run the full integration test suite in Docker:

```bash
./scripts/run-integration-tests.sh
```

Or manually:

```bash
# Build and run
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

### Option 2: Local Services

If you have Radicale and TaskWarrior installed locally:

```bash
# Start Radicale on port 5232
docker run -d -p 5232:5232 --name radicale tomsquest/docker-radicale:latest

# Set up test data
export CALDAV_URL=http://localhost:5232/test-user/
export CALDAV_USERNAME=test-user
export CALDAV_PASSWORD=test-pass
export CALDAV_CALENDAR_ID=test-calendar
export TW_PROJECT=test
export TASKDATA=/tmp/taskwarrior-test

bash scripts/setup-radicale-test-data.sh

# Run integration tests
uv run python tests/integration/test_e2e.py

# Cleanup
docker stop radicale && docker rm radicale
```

## CI/CD Workflow

The workflow (`.github/workflows/ci.yml`) runs on:
- Push to `main`, `master`, or `develop` branches
- Pull requests to these branches

### Jobs

1. **lint** - Runs Ruff linter and formatter checks
2. **unit-tests** - Runs all unit tests with coverage reporting
3. **integration-tests** - Runs end-to-end tests with Docker services

### Environment Variables

Integration tests use these environment variables:

- `CALDAV_URL` - CalDAV server URL (default: `http://localhost:5232/test-user/`)
- `CALDAV_USERNAME` - Username for CalDAV (default: `test-user`)
- `CALDAV_PASSWORD` - Password for CalDAV (default: `test-pass`)
- `CALDAV_CALENDAR_ID` - Calendar ID to use (default: `test-calendar`)
- `TW_PROJECT` - TaskWarrior project name (default: `test`)
- `TASKDATA` - TaskWarrior data directory (optional)

## Test Structure

```
tests/
├── unit/                          # Unit tests (mocked)
│   ├── test_caldav_client.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_field_mapper.py
│   ├── test_logger.py
│   ├── test_sync_engine.py
│   └── test_taskwarrior.py
└── integration/                   # Integration tests (real services)
    ├── test_e2e.py               # End-to-end sync tests
    └── config.toml.ci            # CI configuration template
```

## Integration Test Phases

The `test_e2e.py` script runs 5 test phases:

1. **Initial State** - Verifies TaskWarrior and CalDAV are empty
2. **TW → CalDAV (Create)** - Creates tasks in TW, syncs to CalDAV
3. **CalDAV → TW (Create)** - Creates todos in CalDAV, syncs to TW
4. **TW → CalDAV (Modify)** - Modifies TW task, syncs changes to CalDAV
5. **Dry-Run Mode** - Verifies dry-run doesn't make changes

## Troubleshooting

### Integration tests fail locally

1. Check Docker is running: `docker ps`
2. Check Radicale is accessible: `curl http://localhost:5232`
3. View container logs: `docker-compose -f docker-compose.test.yml logs`
4. Ensure no port conflicts (5232 should be free)

### CI fails but local tests pass

1. Check GitHub Actions logs for specific error
2. Environment variables may differ - check `.github/workflows/ci.yml`
3. Radicale may not be ready - increase health check timeout

### Tests are flaky

- Radicale startup timing - adjust health check intervals in docker-compose
- TaskWarrior data persistence - ensure TASKDATA is properly set
- Network issues - check Docker network configuration

## Docker Images

### Radicale (CalDAV Server)
- Base: `python:3.13-slim`
- Installed: Radicale CalDAV server
- Port: 5232
- Config: `docker/radicale/config`
- Users: `docker/radicale/users` (test-user:test-pass)

### Test Runner (TaskWarrior + Python)
- Base: `ubuntu:22.04`
- Installed: TaskWarrior, Python, uv, twcaldav
- Data: `/taskdata` volume
- Runs: Integration test suite

## Adding New Tests

To add new integration tests:

1. Add test function to `tests/integration/test_e2e.py`
2. Follow naming convention: `test_<description>()`
3. Use helper functions: `create_tw_task()`, `create_caldav_todo()`, etc.
4. Add to test list in `main()`
5. Test locally with Docker Compose first

## Performance

- Unit tests: ~0.3 seconds (118 tests)
- Integration tests: ~30-60 seconds (depends on Docker startup)
- Total CI runtime: ~2-3 minutes

## Future Enhancements

- [ ] Matrix testing (multiple Python versions, TaskWarrior versions)
- [ ] Performance benchmarks (sync 100+ tasks)
- [ ] Mutation testing (network failures, interruptions)
- [ ] Test against other CalDAV servers (Baikal, etc.)
- [ ] Parallel test execution
- [ ] Coverage visualization

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Radicale Project](https://radicale.org/)
- [TaskWarrior](https://taskwarrior.org/)
