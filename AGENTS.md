# Agent Guidelines for twcaldav

## Build/Test Commands
- **IMPORTANT**: Always use `uv run ...` prefix for all commands during development
- **Run all tests**: `uv run pytest tests/`
- **Run single test**: `uv run pytest tests/test_config.py::test_config_from_dict_valid`
- **Run with coverage**: `uv run pytest --cov=src/twcaldav --cov-report=html tests/`
- **Lint/format**: `uv run ruff check src/ tests/` or `uv run ruff format src/ tests/`
- **Install deps**: `uv sync` (uses uv package manager)

## Code Style
- **Python version**: 3.13+ (see pyproject.toml:6)
- **Type hints**: Use modern union syntax (`str | None` not `Optional[str]`), fully annotate all functions
- **Imports**: Group stdlib, third-party, local; use absolute imports (`from twcaldav.config import Config`)
- **Formatting**: Follow PEP 8, use Ruff for linting/formatting
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Dataclasses**: Use `@dataclass` for data containers (see config.py, sync_engine.py)
- **Error handling**: Raise specific exceptions with descriptive messages, log errors before raising
- **Docstrings**: Google style with Args/Returns/Raises sections (see examples in config.py:42-54, sync_engine.py:81-88)
- **Testing**: One test per behavior, descriptive names (`test_config_missing_caldav_section`), use fixtures for reusable data

## Project Structure
- Source: `src/twcaldav/` - Main package code
- Tests: `tests/` - Mirror source structure, use fixtures in `tests/fixtures/`
- Entry point: CLI via `uv run twcaldav` or `uv run python main.py`
