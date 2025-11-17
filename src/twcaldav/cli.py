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
    from .caldav_client import CalDAVClient
    from .config import Config
    from .logger import setup_logger
    from .sync_engine import SyncEngine
    from .taskwarrior import TaskWarrior

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

    # Update config with deletion override
    config.sync.delete_tasks = delete_enabled

    logger.debug(f"CalDAV URL: {config.caldav.url}")
    logger.debug(f"CalDAV Username: {config.caldav.username}")
    logger.debug(f"Mapped projects: {config.get_mapped_projects()}")
    logger.debug(f"Mapped calendars: {config.get_mapped_calendars()}")
    logger.debug(f"Delete tasks: {delete_enabled}")

    # Initialize clients
    try:
        logger.debug("Initializing TaskWarrior client")
        tw = TaskWarrior()

        logger.debug("Connecting to CalDAV server")
        caldav_client = CalDAVClient(
            url=config.caldav.url,
            username=config.caldav.username,
            password=config.caldav.password,
        )
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        return 1

    # Initialize sync engine
    logger.debug("Initializing sync engine")
    sync_engine = SyncEngine(
        config=config,
        tw=tw,
        caldav_client=caldav_client,
        dry_run=args.dry_run,
    )

    # Perform synchronization
    try:
        logger.info("Starting synchronization")
        stats = sync_engine.sync()

        # Display results
        logger.info("Synchronization completed")
        print()
        print(stats)

        if stats.errors > 0:
            logger.warning(f"Sync completed with {stats.errors} error(s)")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Synchronization failed: {e}")
        logger.debug("Exception details:", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
