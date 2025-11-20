# twcaldav

[![CI](https://github.com/pcaro90/twcaldav/actions/workflows/ci.yml/badge.svg)](https://github.com/pcaro90/twcaldav/actions/workflows/ci.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Bidirectional synchronization between TaskWarrior and CalDAV servers.

## Features

- 🔄 **Bidirectional Sync** - Changes propagate both ways (TaskWarrior ↔ CalDAV)
- 🖥️ **Multi-Client Support** - Sync the same CalDAV server from multiple computers
- 📅 **Full CalDAV Support** - Works with Radicale, Baikal, Nextcloud, and other CalDAV servers
- 🎯 **Project Mapping** - Map TaskWarrior projects to CalDAV calendars
- 🔍 **Smart Sync** - Timestamp-based conflict resolution
- 🧪 **Dry Run Mode** - Preview changes before syncing
- ✅ **Comprehensive Tests** - 118 unit tests + 5 integration tests
- 🐳 **CI/CD Ready** - Automated testing with Docker

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/pcaro90/twcaldav.git
cd twcaldav

# Install with uv
uv sync

# Run the tool
uv run twcaldav
```

### Using pip

```bash
pip install -e .
```

## Quick Start

### 1. Configure TaskWarrior UDA

**IMPORTANT**: Before first sync, configure TaskWarrior to recognize the CalDAV UID as a User Defined Attribute:

```bash
task config uda.caldav_uid.type string
task config uda.caldav_uid.label "CalDAV UID"
```

This allows twcaldav to store the CalDAV task identifier in your TaskWarrior database, enabling proper synchronization across multiple devices.

### 2. Create Configuration File

Create `~/.config/twcaldav/config.toml`:

```toml
[caldav]
url = "https://your-caldav-server.com/username"
username = "your-username"
password = "your-password"

[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "calendar-id-or-name"

[[mappings]]
taskwarrior_project = "personal"
caldav_calendar = "another-calendar-id"

[sync]
delete_tasks = false  # Set to true to sync deletions
```

### 3. Run Sync

```bash
# Sync everything
uv run twcaldav

# Dry run (preview changes)
uv run twcaldav --dry-run

# Verbose output
uv run twcaldav -v
```

## Configuration

### CalDAV Section

```toml
[caldav]
url = "https://caldav.example.com/user/"
username = "your-username"
password = "your-password"
```

### Project-Calendar Mappings

Map TaskWarrior projects to CalDAV calendars:

```toml
[[mappings]]
taskwarrior_project = "work"
caldav_calendar = "calendar-uuid-or-name"
```

Multiple mappings are supported. Each TaskWarrior project syncs to its mapped calendar.

### Sync Options

```toml
[sync]
delete_tasks = false  # Enable deletion sync (careful!)
```

### Security Best Practices

1. **Protect Configuration File**: Ensure config file has restricted permissions:
   ```bash
   chmod 600 ~/.config/twcaldav/config.toml
   ```

2. **Use App Passwords**: Many CalDAV servers (Nextcloud, etc.) support app-specific passwords. Use them instead of your main account password.

3. **HTTPS Only**: Always use HTTPS URLs for CalDAV servers to encrypt credentials in transit.

4. **Backup First**: Before first sync, backup your TaskWarrior data:
   ```bash
   cp -r ~/.task ~/.task.backup
   ```

5. **Test with Dry Run**: Always test with `--dry-run` first:
   ```bash
   uv run twcaldav --dry-run -v
   ```

### Automated Sync (Cron Job)

To sync automatically every hour:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path to uv and project):
0 * * * * cd /path/to/twcaldav && /path/to/uv run twcaldav >> /var/log/twcaldav.log 2>&1
```

Or use a systemd timer for more control:

```ini
# ~/.config/systemd/user/twcaldav.service
[Unit]
Description=TaskWarrior CalDAV Sync

[Service]
Type=oneshot
ExecStart=/usr/bin/uv run --directory /path/to/twcaldav twcaldav

# ~/.config/systemd/user/twcaldav.timer
[Unit]
Description=Run TaskWarrior CalDAV Sync hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with:
```bash
systemctl --user enable --now twcaldav.timer
```

## Field Mapping

| TaskWarrior | CalDAV |
|-------------|--------|
| description | SUMMARY |
| status | STATUS (pending→NEEDS-ACTION, completed→COMPLETED) |
| due | DUE |
| priority | PRIORITY (H→1, M→5, L→9) |
| project | CATEGORIES |
| tags | CATEGORIES |
| annotations | DESCRIPTION |
| caldav_uid (UDA) | UID (unique identifier) |

## Development

### Prerequisites

- Python 3.13+
- TaskWarrior
- uv package manager
- Docker (for integration tests)

### Setup

```bash
# Clone and install
git clone https://github.com/pcaro90/twcaldav.git
cd twcaldav
uv sync

# Run tests
uv run pytest tests/ -v

# Run integration tests
./scripts/run-integration-tests.sh

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Testing

The project has comprehensive test coverage:

- **Unit Tests**: 114 tests covering all modules (88% coverage)
- **Integration Tests**: 6 end-to-end test phases with real CalDAV server

```bash
# Run unit tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest --cov=src/twcaldav --cov-report=html tests/

# Run integration tests (requires Docker)
./scripts/run-integration-tests.sh
```

See [TESTING_QUICKSTART.md](TESTING_QUICKSTART.md) for more details.

## CI/CD

The project uses GitHub Actions for automated testing:

- **Lint**: Code quality checks with Ruff
- **Unit Tests**: Fast, mocked tests
- **Integration Tests**: Full end-to-end tests with Docker

Every push and pull request triggers the full test suite.

See [.github/workflows/README.md](.github/workflows/README.md) for CI/CD documentation.

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   TaskWarrior   │◄────►│   Sync Engine    │◄────►│  CalDAV Server  │
│   (local CLI)   │      │ (twcaldav core)  │      │   (Radicale,    │
│                 │      │                  │      │   Baikal, etc)  │
└─────────────────┘      └──────────────────┘      └─────────────────┘
        │                         │                          │
        ├─ Tasks (JSON)           ├─ Field Mapping         ├─ VTODOs
        ├─ Projects               ├─ Conflict Detection   ├─ Calendars
        └─ Status/Priority        └─ Sync Actions         └─ Collections
```

## Project Structure

```
twcaldav/
├── src/twcaldav/           # Main package
│   ├── caldav_client.py    # CalDAV API wrapper
│   ├── taskwarrior.py      # TaskWarrior interface
│   ├── sync_engine.py      # Sync logic
│   ├── field_mapper.py     # Data conversion
│   ├── config.py           # Configuration
│   ├── logger.py           # Logging setup
│   └── cli.py              # CLI interface
├── tests/                  # Test suite
│   ├── test_*.py           # Unit tests (114 tests)
│   └── integration/        # Integration tests (6 phases)
│       └── test_e2e.py     # End-to-end tests
├── scripts/                # Utility scripts
│   ├── run-integration-tests.sh
│   └── setup-radicale-test-data.sh
├── docker-compose.test.yml # Local integration testing
└── .github/workflows/      # CI/CD pipelines
    └── ci.yml
```

## Troubleshooting

### Sync not working

1. Check configuration: `cat ~/.config/twcaldav/config.toml`
2. Test CalDAV connection: `curl -u user:pass https://caldav-url/`
3. Run with verbose logging: `uv run twcaldav -v`
4. Try dry-run first: `uv run twcaldav --dry-run`

### Tasks not appearing

- Verify project mapping in config
- Check TaskWarrior has tasks: `task project:yourproject list`
- Ensure calendar exists in CalDAV server
- Check task status (only pending/completed sync, not deleted)

### Duplicates created

- Ensure UDA is configured correctly: `task _get rc.uda.caldav_uid.type`
- Check if tasks have CalDAV UID: `task list rc.report.list.columns=id,description,caldav_uid`
- Don't run multiple sync instances simultaneously
- Check for stale tasks: `task status:deleted list`

### UDA not configured error

If you see errors about missing `caldav_uid` UDA, configure it:

```bash
task config uda.caldav_uid.type string
task config uda.caldav_uid.label "CalDAV UID"
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests: `uv run pytest tests/ -v`
5. Run integration tests: `./scripts/run-integration-tests.sh`
6. Lint code: `uv run ruff check src/ tests/`
7. Format code: `uv run ruff format src/ tests/`
8. Submit a pull request

## Documentation

- [Testing Quick Start](TESTING_QUICKSTART.md) - Run tests locally
- [CI/CD Documentation](.github/workflows/README.md) - GitHub Actions setup
- [Integration Testing](INTEGRATION_TEST.md) - Manual testing guide
- [Development Guide](AGENTS.md) - Build/test commands

## License

MIT License - see LICENSE file for details

## Credits

- Built with [caldav](https://github.com/python-caldav/caldav) library
- Uses [TaskWarrior](https://taskwarrior.org/) CLI
- Tested with [Radicale](https://radicale.org/) CalDAV server
