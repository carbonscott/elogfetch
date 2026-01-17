"""Command-line interface for fetch-elog."""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import click

from .api import (
    ElogClient,
    fetch_updated_experiments,
    fetch_experiment_info,
    fetch_file_manager,
    fetch_logbook,
    fetch_runtable,
    fetch_questionnaire,
    fetch_workflow,
)
from .config import Config
from .exceptions import AuthenticationError, FetchElogError, LockError
from .storage import Database, find_latest_database, generate_db_name
from .utils import acquire_lock, get_logger, setup_logging


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Quiet mode (errors only)")
@click.pass_context
def cli(ctx, config, verbose, quiet):
    """fetch-elog: Fetch LCLS experiment data from the electronic logbook."""
    ctx.ensure_object(dict)

    # Setup logging
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    setup_logging(level=level, quiet=False)
    logger = get_logger()

    # Load configuration
    config_path = Path(config) if config else None
    ctx.obj["config"] = Config.load(config_file=config_path)
    ctx.obj["logger"] = logger


@cli.command()
@click.option("--hours", "-h", type=float, help="Hours to look back (default: from config)")
@click.option("--exclude", "-e", multiple=True, help="Patterns to exclude (e.g., -e 'txi*')")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory for database")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.option("--parallel", "-p", type=int, help="Number of parallel jobs")
@click.option("--incremental", "-i", is_flag=True,
              help="Update existing database incrementally (default: create fresh)")
@click.pass_context
def update(ctx, hours, exclude, output_dir, dry_run, parallel, incremental):
    """Update the local database with recent experiments."""
    logger = ctx.obj["logger"]
    config = ctx.obj["config"]

    # Apply CLI overrides
    cli_args = {}
    if hours is not None:
        cli_args["hours"] = hours
    if exclude:
        cli_args["exclude"] = list(exclude)
    if parallel is not None:
        cli_args["parallel_jobs"] = parallel
    if output_dir:
        cli_args["database_dir"] = output_dir

    config = Config.load(cli_args=cli_args)

    # Determine output directory
    db_dir = config.database_dir or Path.cwd()
    db_dir = Path(db_dir)

    if not db_dir.exists():
        db_dir.mkdir(parents=True)

    logger.info(f"Looking back {config.hours_lookback} hours")
    offset_secs = int(config.hours_lookback * 3600)

    try:
        # Create client and fetch experiments
        client = ElogClient(
            base_url=config.base_url,
            kerberos_principal=config.kerberos_principal,
        )
        experiments = fetch_updated_experiments(
            client,
            offset_secs,
            config.exclude_patterns,
        )

        if not experiments:
            logger.info("No experiments to update.")
            return

        if dry_run:
            click.echo(f"\nWould fetch data for {len(experiments)} experiments:")
            for exp in experiments[:20]:
                click.echo(f"  - {exp}")
            if len(experiments) > 20:
                click.echo(f"  ... and {len(experiments) - 20} more")
            return

        # Acquire lock
        lock_path = db_dir / ".fetch_elog.lock"
        try:
            with acquire_lock(lock_path):
                _do_update(client, experiments, db_dir, config, logger, incremental)
        except LockError as e:
            logger.error(str(e))
            sys.exit(1)

    except AuthenticationError as e:
        logger.error(str(e))
        logger.error("Please run 'kinit' to authenticate.")
        sys.exit(1)
    except FetchElogError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def _do_update(client, experiments, db_dir, config, logger, incremental=False):
    """Perform the actual update with lock held."""
    db_name = generate_db_name()
    db_path = db_dir / db_name

    if incremental:
        # Find existing database and copy it
        existing_db = find_latest_database(db_dir)
        if existing_db:
            logger.info(f"Incremental mode: copying {existing_db} -> {db_path}")
            shutil.copy2(existing_db, db_path)
        else:
            logger.info("No existing database found, creating fresh database")

    logger.info(f"Using database: {db_path}")
    db = Database(db_path)

    def fetch_experiment_data(exp_id):
        """Fetch all data for an experiment (thread-safe, no DB access)."""
        try:
            return {
                "experiment_id": exp_id,
                "info": fetch_experiment_info(client, exp_id),
                "logbook": fetch_logbook(client, exp_id),
                "runtable": fetch_runtable(client, exp_id),
                "file_manager": fetch_file_manager(client, exp_id),
                "questionnaire": fetch_questionnaire(client, exp_id),
                "workflow": fetch_workflow(client, exp_id),
            }
        except Exception as e:
            logger.warning(f"Error fetching {exp_id}: {e}")
            return {"experiment_id": exp_id, "error": str(e)}

    # Phase 1: Fetch data in parallel (network I/O bound)
    results = []
    if config.parallel_jobs > 1:
        with ThreadPoolExecutor(max_workers=config.parallel_jobs) as executor:
            futures = {executor.submit(fetch_experiment_data, exp): exp for exp in experiments}

            with click.progressbar(
                as_completed(futures),
                length=len(experiments),
                label="Fetching experiments",
            ) as completed:
                for future in completed:
                    results.append(future.result())
    else:
        with click.progressbar(experiments, label="Fetching experiments") as exps:
            for exp_id in exps:
                results.append(fetch_experiment_data(exp_id))

    # Phase 2: Write to database sequentially (fast, avoids thread safety issues)
    success_count = 0
    error_count = 0

    for data in results:
        exp_id = data["experiment_id"]
        if "error" in data:
            error_count += 1
            continue

        try:
            if incremental:
                db.delete_experiment(exp_id)

            if data["info"]:
                db.insert_experiment(data["info"])
            if data["logbook"]:
                db.insert_logbook(data["logbook"])
            if data["runtable"]:
                db.insert_runtable(data["runtable"])
            if data["file_manager"]:
                db.insert_file_manager(data["file_manager"])
            if data["questionnaire"]:
                db.insert_questionnaire(data["questionnaire"])
            if data["workflow"]:
                db.insert_workflow(data["workflow"])

            success_count += 1
        except Exception as e:
            logger.warning(f"Error writing {exp_id}: {e}")
            error_count += 1

    # Set metadata
    db.set_metadata("last_update", datetime.now().isoformat())
    db.set_metadata("hours_lookback", str(config.hours_lookback))

    db.close()

    logger.info(f"Update complete: {success_count} succeeded, {error_count} failed")
    logger.info(f"Database saved to: {db_path}")


@cli.command()
@click.argument("experiment_id")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory for database")
@click.pass_context
def fetch(ctx, experiment_id, output_dir):
    """Fetch data for a specific experiment."""
    logger = ctx.obj["logger"]
    config = ctx.obj["config"]

    db_dir = Path(output_dir) if output_dir else config.database_dir or Path.cwd()

    # Create directory if it doesn't exist
    if not db_dir.exists():
        db_dir.mkdir(parents=True)

    try:
        client = ElogClient(
            base_url=config.base_url,
            kerberos_principal=config.kerberos_principal,
        )

        # Find or create database
        existing_db = find_latest_database(db_dir)
        if existing_db:
            db_path = existing_db
            logger.info(f"Using existing database: {db_path}")
        else:
            db_path = db_dir / generate_db_name()
            logger.info(f"Creating new database: {db_path}")

        db = Database(db_path)

        # Fetch all data types
        info = fetch_experiment_info(client, experiment_id)
        if info:
            db.insert_experiment(info)
            logger.info(f"Fetched experiment info")

        logbook = fetch_logbook(client, experiment_id)
        if logbook:
            db.insert_logbook(logbook)
            logger.info(f"Fetched {len(logbook)} logbook entries")

        runtable = fetch_runtable(client, experiment_id)
        if runtable:
            db.insert_runtable(runtable)
            logger.info(f"Fetched runtable data")

        file_manager = fetch_file_manager(client, experiment_id)
        if file_manager:
            db.insert_file_manager(file_manager)
            logger.info(f"Fetched file manager data ({len(file_manager.get('file_manager_records', []))} runs)")

        questionnaire = fetch_questionnaire(client, experiment_id)
        if questionnaire:
            db.insert_questionnaire(questionnaire)
            logger.info(f"Fetched questionnaire ({len(questionnaire.get('fields', []))} fields)")

        workflow = fetch_workflow(client, experiment_id)
        if workflow:
            db.insert_workflow(workflow)
            logger.info(f"Fetched {len(workflow.get('workflows', []))} workflows")

        db.close()
        logger.info(f"Data saved to: {db_path}")

    except AuthenticationError as e:
        logger.error(str(e))
        sys.exit(1)
    except FetchElogError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


@cli.command()
@click.option("--database-dir", "-d", type=click.Path(exists=True), help="Database directory")
@click.pass_context
def status(ctx, database_dir):
    """Show status of local database."""
    logger = ctx.obj["logger"]
    config = ctx.obj["config"]

    db_dir = Path(database_dir) if database_dir else config.database_dir or Path.cwd()

    db_path = find_latest_database(db_dir)

    if not db_path:
        click.echo("No database found.")
        click.echo(f"Run 'fetch-elog update' to create one.")
        return

    click.echo(f"Database: {db_path}")
    click.echo(f"Size: {db_path.stat().st_size / 1024:.1f} KB")
    click.echo(f"Modified: {datetime.fromtimestamp(db_path.stat().st_mtime)}")

    db = Database(db_path)

    # Get metadata
    last_update = db.get_metadata("last_update")
    hours_lookback = db.get_metadata("hours_lookback")

    if last_update:
        click.echo(f"Last update: {last_update}")
    if hours_lookback:
        click.echo(f"Hours lookback: {hours_lookback}")

    click.echo()
    click.echo("Statistics:")

    stats = db.get_stats()
    for table, count in stats.items():
        click.echo(f"  {table}: {count}")

    db.close()


@cli.command()
@click.option("--hours", "-h", type=float, default=168, help="Hours to look back (default: 168)")
@click.option("--exclude", "-e", multiple=True, help="Patterns to exclude")
@click.pass_context
def list_experiments(ctx, hours, exclude):
    """List recently updated experiments."""
    logger = ctx.obj["logger"]
    config = ctx.obj["config"]

    offset_secs = int(hours * 3600)

    try:
        client = ElogClient(
            base_url=config.base_url,
            kerberos_principal=config.kerberos_principal,
        )
        experiments = fetch_updated_experiments(
            client,
            offset_secs,
            list(exclude) if exclude else None,
        )

        if not experiments:
            click.echo("No experiments found.")
            return

        click.echo(f"Found {len(experiments)} experiments updated in last {hours} hours:")
        for exp in sorted(experiments):
            click.echo(f"  {exp}")

    except AuthenticationError as e:
        logger.error(str(e))
        sys.exit(1)
    except FetchElogError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
