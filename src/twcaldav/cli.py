"""Command-line interface for twcaldav."""

import argparse
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Command-line arguments. If None, uses sys.argv.

    Returns:
        Parsed arguments.
    """
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="twcaldav",
        description="Bi-directional sync between TaskWarrior and CalDAV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (DEBUG level)",
    )

    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Perform a trial run with no changes made",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        metavar="PATH",
        help="Path to configuration file (default: ~/.config/twcaldav/config.toml)",
    )

    parser.add_argument(
        "--delete",
        action="store_true",
        help="Enable deletion of tasks (overrides config setting)",
    )

    parser.add_argument(
        "--no-delete",
        action="store_true",
        help="Disable deletion of tasks (overrides config setting)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)

    # Validate conflicting options
    if args.delete and args.no_delete:
        parser.error("--delete and --no-delete cannot be used together")

    return args


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the application.

    Args:
        argv: Command-line arguments. If None, uses sys.argv.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    from .config import Config
    from .logger import setup_logger

    args = parse_args(argv)

    # Setup logging
    logger = setup_logger(verbose=args.verbose)

    logger.info("Starting twcaldav sync")

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Load configuration
    try:
        config = Config.from_file(args.config)
        logger.debug(f"Loaded configuration from {args.config or 'default location'}")
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Handle deletion override
    delete_enabled = config.sync.delete_tasks
    if args.delete:
        delete_enabled = True
        logger.info("Deletion enabled via command-line flag")
    elif args.no_delete:
        delete_enabled = False
        logger.info("Deletion disabled via command-line flag")

    logger.debug(f"CalDAV URL: {config.caldav.url}")
    logger.debug(f"CalDAV Username: {config.caldav.username}")
    logger.debug(f"Mapped projects: {config.get_mapped_projects()}")
    logger.debug(f"Mapped calendars: {config.get_mapped_calendars()}")
    logger.debug(f"Delete tasks: {delete_enabled}")

    # TODO: Implement sync logic
    logger.warning("Sync logic not yet implemented")

    logger.info("Sync completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
