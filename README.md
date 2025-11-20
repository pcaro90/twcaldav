# twcaldav

Bidirectional synchronization between TaskWarrior and CalDAV servers.

## Features

- Two-way sync between TaskWarrior tasks and CalDAV todos
- Project-to-calendar mapping
- Support for priorities, due dates, tags, and annotations
- Dry-run mode for testing
- Conflict resolution based on modification times

## Installation

```bash
pip install twcaldav
```

## Configuration

Create a `config.toml` file:

```toml
[caldav]
url = "https://example.com/caldav"
username = "your-username"
password = "your-password"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "Work Tasks"

[sync]
delete_tasks = false
```

## Usage

```bash
# Sync tasks and todos
twcaldav sync -c config.toml

# Test CalDAV connection
twcaldav test-caldav -c config.toml

# Unlink tasks from CalDAV
twcaldav unlink -c config.toml

# Use verbose mode
twcaldav sync -v -c config.toml

# Dry run (no changes)
twcaldav sync -n -c config.toml
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/

# Run integration tests
./scripts/run-integration-tests.sh
```

## License

MIT
