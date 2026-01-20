"""SQLite database operations for elogfetch."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import DB_PATTERN, DB_PREFIX
from ..utils import get_logger

logger = get_logger()


def generate_db_name() -> str:
    """Generate a database filename with current timestamp."""
    timestamp = datetime.now().strftime("%Y_%m%d_%H%M")
    return f"{DB_PREFIX}{timestamp}.db"


def find_latest_database(directory: Path) -> Path | None:
    """Find the most recent elog database in a directory.

    Args:
        directory: Directory to search

    Returns:
        Path to the latest database, or None if not found
    """
    if not directory.exists():
        return None

    candidates = []
    for path in directory.glob(f"{DB_PREFIX}*.db"):
        if DB_PATTERN.match(path.name):
            candidates.append(path)

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)


class Database:
    """SQLite database for storing elog data."""

    def __init__(self, db_path: Path):
        """Initialize database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._run_id_cache: dict[str, int] = {}
        self._detector_cache: dict[str, int] = {}
        self._create_tables()

    def enable_wal_mode(self) -> None:
        """Enable Write-Ahead Logging for better write performance.

        This allows reads to proceed concurrently with writes and
        improves write performance for batch operations.
        """
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

    def commit(self) -> None:
        """Explicit commit for batch operations."""
        self.conn.commit()

    def _create_tables(self):
        """Create all required tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS Experiment (
                experiment_id TEXT PRIMARY KEY,
                name TEXT,
                instrument TEXT,
                start_time DATETIME,
                end_time DATETIME,
                pi TEXT,
                pi_email TEXT,
                leader_account TEXT,
                description TEXT,
                slack_channels TEXT,
                analysis_queues TEXT,
                urawi_proposal TEXT
            );

            CREATE TABLE IF NOT EXISTS Questionnaire (
                questionnaire_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                proposal TEXT,
                category TEXT NOT NULL,
                field_id TEXT NOT NULL,
                field_name TEXT,
                field_value TEXT,
                modified_time DATETIME,
                modified_uid TEXT,
                created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(experiment_id, field_id),
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
            );

            CREATE TABLE IF NOT EXISTS Workflow (
                workflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                mongo_id TEXT,
                name TEXT NOT NULL,
                executable TEXT,
                trigger TEXT,
                location TEXT,
                parameters TEXT,
                run_param_name TEXT,
                run_param_value TEXT,
                run_as_user TEXT,
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
            );

            CREATE TABLE IF NOT EXISTS Run (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_number INTEGER NOT NULL,
                experiment_id TEXT NOT NULL,
                start_time DATETIME,
                end_time DATETIME,
                UNIQUE(run_number, experiment_id),
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id)
            );

            CREATE TABLE IF NOT EXISTS RunProductionData (
                run_data_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                n_events INTEGER,
                n_damaged INTEGER,
                n_dropped INTEGER,
                prod_start DATETIME,
                prod_end DATETIME,
                number_of_files INTEGER,
                total_size_bytes INTEGER,
                FOREIGN KEY (run_id) REFERENCES Run(run_id)
            );

            CREATE TABLE IF NOT EXISTS Detector (
                detector_id INTEGER PRIMARY KEY AUTOINCREMENT,
                detector_name TEXT NOT NULL,
                description TEXT,
                UNIQUE(detector_name)
            );

            CREATE TABLE IF NOT EXISTS RunDetector (
                run_detector_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                detector_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                UNIQUE(run_id, detector_id),
                FOREIGN KEY (run_id) REFERENCES Run(run_id),
                FOREIGN KEY (detector_id) REFERENCES Detector(detector_id)
            );

            CREATE TABLE IF NOT EXISTS Logbook (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                run_id INTEGER,
                timestamp DATETIME NOT NULL,
                content TEXT,
                tags TEXT,
                author TEXT,
                FOREIGN KEY (experiment_id) REFERENCES Experiment(experiment_id),
                FOREIGN KEY (run_id) REFERENCES Run(run_id)
            );

            CREATE TABLE IF NOT EXISTS Metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_questionnaire_experiment ON Questionnaire(experiment_id);
            CREATE INDEX IF NOT EXISTS idx_questionnaire_category ON Questionnaire(category);
            CREATE INDEX IF NOT EXISTS idx_questionnaire_proposal ON Questionnaire(proposal);
            CREATE INDEX IF NOT EXISTS idx_run_experiment ON Run(experiment_id);
            CREATE INDEX IF NOT EXISTS idx_logbook_experiment ON Logbook(experiment_id);
            CREATE INDEX IF NOT EXISTS idx_logbook_run ON Logbook(run_id);

            -- View for complete run information
            CREATE VIEW IF NOT EXISTS RunCompleteData AS
            SELECT
                r.run_id,
                r.run_number,
                r.experiment_id,
                r.start_time,
                r.end_time,
                rpd.n_events,
                rpd.n_damaged,
                rpd.n_dropped,
                rpd.prod_start,
                rpd.prod_end,
                rpd.number_of_files,
                rpd.total_size_bytes
            FROM Run r
            LEFT JOIN RunProductionData rpd ON r.run_id = rpd.run_id;
        """)
        self.conn.commit()

    def _get_or_create_run_id(self, experiment_id: str, run_number: int) -> int:
        """Get existing run_id or create new run entry."""
        cache_key = f"{experiment_id}_{run_number}"
        if cache_key in self._run_id_cache:
            return self._run_id_cache[cache_key]

        cursor = self.conn.execute(
            "SELECT run_id FROM Run WHERE experiment_id = ? AND run_number = ?",
            (experiment_id, run_number),
        )
        result = cursor.fetchone()

        if result:
            run_id = result[0]
        else:
            cursor = self.conn.execute(
                "INSERT INTO Run (experiment_id, run_number) VALUES (?, ?)",
                (experiment_id, run_number),
            )
            run_id = cursor.lastrowid

        self._run_id_cache[cache_key] = run_id
        return run_id

    def _get_or_create_detector_id(self, detector_name: str) -> int:
        """Get existing detector_id or create new detector entry."""
        if detector_name in self._detector_cache:
            return self._detector_cache[detector_name]

        cursor = self.conn.execute(
            "SELECT detector_id FROM Detector WHERE detector_name = ?",
            (detector_name,),
        )
        result = cursor.fetchone()

        if result:
            detector_id = result[0]
        else:
            cursor = self.conn.execute(
                "INSERT INTO Detector (detector_name) VALUES (?)",
                (detector_name,),
            )
            detector_id = cursor.lastrowid

        self._detector_cache[detector_name] = detector_id
        return detector_id

    def insert_experiment(self, data: dict[str, Any]) -> None:
        """Insert or update experiment data."""
        self._insert_experiment_no_commit(data)
        self.conn.commit()

    def _insert_experiment_no_commit(self, data: dict[str, Any]) -> None:
        """Insert experiment without committing (for batch operations)."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO Experiment
            (experiment_id, name, instrument, start_time, end_time, pi, pi_email,
             leader_account, description, slack_channels, analysis_queues, urawi_proposal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("experiment_id"),
                data.get("name"),
                data.get("instrument"),
                data.get("start_time"),
                data.get("end_time"),
                data.get("pi"),
                data.get("pi_email"),
                data.get("leader_account"),
                data.get("description"),
                data.get("slack_channels"),
                data.get("analysis_queues"),
                data.get("urawi_proposal"),
            ),
        )
        logger.debug(f"Inserted experiment: {data.get('experiment_id')}")

    def insert_questionnaire(self, data: dict[str, Any]) -> None:
        """Insert questionnaire data as individual field records."""
        self._insert_questionnaire_no_commit(data)
        self.conn.commit()

    def _insert_questionnaire_no_commit(self, data: dict[str, Any]) -> None:
        """Insert questionnaire without committing (for batch operations)."""
        experiment_id = data.get("experiment_id")
        proposal_number = data.get("proposal_number")
        fields = data.get("fields", [])

        # Delete existing questionnaire data for this experiment
        self.conn.execute(
            "DELETE FROM Questionnaire WHERE experiment_id = ?",
            (experiment_id,),
        )

        for field in fields:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO Questionnaire
                (experiment_id, proposal, category, field_id, field_name,
                 field_value, modified_time, modified_uid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    proposal_number,
                    field.get("category"),
                    field.get("field_id"),
                    field.get("field_name"),
                    field.get("field_value"),
                    field.get("modified_time"),
                    field.get("modified_uid"),
                ),
            )

        logger.debug(f"Inserted {len(fields)} questionnaire fields for: {experiment_id}")

    def insert_workflow(self, data: dict[str, Any]) -> None:
        """Insert workflow definitions."""
        self._insert_workflow_no_commit(data)
        self.conn.commit()

    def _insert_workflow_no_commit(self, data: dict[str, Any]) -> None:
        """Insert workflow without committing (for batch operations)."""
        experiment_id = data.get("experiment_id")

        # Delete existing workflows for this experiment
        self.conn.execute(
            "DELETE FROM Workflow WHERE experiment_id = ?",
            (experiment_id,),
        )

        for workflow in data.get("workflows", []):
            self.conn.execute(
                """
                INSERT INTO Workflow
                (experiment_id, mongo_id, name, executable, trigger, location,
                 parameters, run_param_name, run_param_value, run_as_user)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    workflow.get("mongo_id"),
                    workflow.get("name"),
                    workflow.get("executable"),
                    workflow.get("trigger"),
                    workflow.get("location"),
                    json.dumps(workflow.get("parameters")),
                    workflow.get("run_param_name"),
                    workflow.get("run_param_value"),
                    workflow.get("run_as_user"),
                ),
            )

        logger.debug(f"Inserted {len(data.get('workflows', []))} workflows for: {experiment_id}")

    def insert_logbook(self, entries: list[dict[str, Any]]) -> None:
        """Insert logbook entries."""
        self._insert_logbook_no_commit(entries)
        self.conn.commit()

    def _insert_logbook_no_commit(self, entries: list[dict[str, Any]]) -> None:
        """Insert logbook without committing (for batch operations)."""
        if not entries:
            return

        experiment_id = entries[0].get("experiment_id")

        # Delete existing logbook entries for this experiment
        self.conn.execute(
            "DELETE FROM Logbook WHERE experiment_id = ?",
            (experiment_id,),
        )

        for entry in entries:
            run_id = None
            run_number = entry.get("run_number")
            if run_number is not None:
                run_id = self._get_or_create_run_id(entry["experiment_id"], run_number)

            self.conn.execute(
                """
                INSERT INTO Logbook
                (experiment_id, run_id, timestamp, content, tags, author)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.get("experiment_id"),
                    run_id,
                    entry.get("timestamp"),
                    entry.get("content"),
                    entry.get("tags"),
                    entry.get("author"),
                ),
            )

        logger.debug(f"Inserted {len(entries)} logbook entries for: {experiment_id}")

    def insert_runtable(self, data: dict[str, Any]) -> None:
        """Insert run table data."""
        self._insert_runtable_no_commit(data)
        self.conn.commit()

    def _insert_runtable_no_commit(self, data: dict[str, Any]) -> None:
        """Insert runtable without committing (for batch operations)."""
        experiment_id = data.get("experiment_id")

        for run_data in data.get("data_production", []):
            run_number = run_data.get("run_number")
            if run_number is None:
                continue

            run_id = self._get_or_create_run_id(experiment_id, run_number)

            # Update run times
            self.conn.execute(
                """
                UPDATE Run SET start_time = ?, end_time = ?
                WHERE run_id = ?
                """,
                (run_data.get("start_time"), run_data.get("end_time"), run_id),
            )

            # Check if production data exists
            cursor = self.conn.execute(
                "SELECT run_data_id FROM RunProductionData WHERE run_id = ?",
                (run_id,),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing record
                self.conn.execute(
                    """
                    UPDATE RunProductionData
                    SET n_events = COALESCE(?, n_events),
                        n_damaged = COALESCE(?, n_damaged),
                        n_dropped = COALESCE(?, n_dropped),
                        prod_start = COALESCE(?, prod_start),
                        prod_end = COALESCE(?, prod_end)
                    WHERE run_id = ?
                    """,
                    (
                        run_data.get("n_events"),
                        run_data.get("n_damaged"),
                        run_data.get("n_dropped"),
                        run_data.get("prod_start"),
                        run_data.get("prod_end"),
                        run_id,
                    ),
                )
            else:
                # Insert new record
                self.conn.execute(
                    """
                    INSERT INTO RunProductionData
                    (run_id, n_events, n_damaged, n_dropped, prod_start, prod_end)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        run_data.get("n_events"),
                        run_data.get("n_damaged"),
                        run_data.get("n_dropped"),
                        run_data.get("prod_start"),
                        run_data.get("prod_end"),
                    ),
                )

        # Insert detector data
        for detector_data in data.get("detectors", []):
            run_number = detector_data.get("run_number")
            if run_number is None:
                continue

            run_id = self._get_or_create_run_id(experiment_id, run_number)

            for key, value in detector_data.items():
                if key == "run_number" or not key.strip():
                    continue

                detector_id = self._get_or_create_detector_id(key)
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO RunDetector
                    (run_id, detector_id, status)
                    VALUES (?, ?, ?)
                    """,
                    (run_id, detector_id, value),
                )

        logger.debug(f"Inserted runtable for: {experiment_id}")

    def insert_file_manager(self, data: dict[str, Any]) -> None:
        """Insert file manager data (number_of_files, total_size_bytes per run)."""
        self._insert_file_manager_no_commit(data)
        self.conn.commit()

    def _insert_file_manager_no_commit(self, data: dict[str, Any]) -> None:
        """Insert file manager without committing (for batch operations)."""
        experiment_id = data.get("experiment_id")
        records = data.get("file_manager_records", [])

        for record in records:
            run_number = record.get("run_number")
            if run_number is None:
                continue

            run_id = self._get_or_create_run_id(experiment_id, run_number)

            # Check if production data exists
            cursor = self.conn.execute(
                "SELECT run_data_id FROM RunProductionData WHERE run_id = ?",
                (run_id,),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing record
                self.conn.execute(
                    """
                    UPDATE RunProductionData
                    SET number_of_files = COALESCE(?, number_of_files),
                        total_size_bytes = COALESCE(?, total_size_bytes)
                    WHERE run_id = ?
                    """,
                    (
                        record.get("number_of_files"),
                        record.get("total_size_bytes"),
                        run_id,
                    ),
                )
            else:
                # Insert new record
                self.conn.execute(
                    """
                    INSERT INTO RunProductionData
                    (run_id, number_of_files, total_size_bytes)
                    VALUES (?, ?, ?)
                    """,
                    (
                        run_id,
                        record.get("number_of_files"),
                        record.get("total_size_bytes"),
                    ),
                )

        logger.debug(f"Inserted file manager data for: {experiment_id}")

    def insert_experiment_batch(self, data: dict[str, Any]) -> None:
        """Insert all data for an experiment without committing.

        This is used by the streaming pipeline for batch commits.
        Call commit() after inserting multiple experiments.

        Args:
            data: Dictionary containing experiment_id and all data types:
                  info, logbook, runtable, file_manager, questionnaire, workflow
        """
        if data.get("info"):
            self._insert_experiment_no_commit(data["info"])
        if data.get("logbook"):
            self._insert_logbook_no_commit(data["logbook"])
        if data.get("runtable"):
            self._insert_runtable_no_commit(data["runtable"])
        if data.get("file_manager"):
            self._insert_file_manager_no_commit(data["file_manager"])
        if data.get("questionnaire"):
            self._insert_questionnaire_no_commit(data["questionnaire"])
        if data.get("workflow"):
            self._insert_workflow_no_commit(data["workflow"])

    def set_metadata(self, key: str, value: str) -> None:
        """Set a metadata value."""
        self._set_metadata_no_commit(key, value)
        self.conn.commit()

    def _set_metadata_no_commit(self, key: str, value: str) -> None:
        """Set metadata without committing (for batch operations)."""
        self.conn.execute(
            "INSERT OR REPLACE INTO Metadata (key, value) VALUES (?, ?)",
            (key, value),
        )

    def get_metadata(self, key: str) -> str | None:
        """Get a metadata value."""
        cursor = self.conn.execute(
            "SELECT value FROM Metadata WHERE key = ?",
            (key,),
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def get_stats(self) -> dict[str, int]:
        """Get database statistics."""
        stats = {}
        for table in ["Experiment", "Run", "Logbook", "Questionnaire", "Workflow"]:
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table.lower()] = cursor.fetchone()[0]
        return stats

    def delete_experiment(self, experiment_id: str) -> None:
        """Delete all data for an experiment from all tables.

        Args:
            experiment_id: The experiment ID to delete
        """
        # Get run_ids for this experiment (needed for cascade delete)
        cursor = self.conn.execute(
            "SELECT run_id FROM Run WHERE experiment_id = ?",
            (experiment_id,),
        )
        run_ids = [row[0] for row in cursor.fetchall()]

        # Delete in order (respecting foreign keys)
        for run_id in run_ids:
            self.conn.execute("DELETE FROM RunDetector WHERE run_id = ?", (run_id,))
            self.conn.execute("DELETE FROM RunProductionData WHERE run_id = ?", (run_id,))

        self.conn.execute("DELETE FROM Logbook WHERE experiment_id = ?", (experiment_id,))
        self.conn.execute("DELETE FROM Run WHERE experiment_id = ?", (experiment_id,))
        self.conn.execute("DELETE FROM Questionnaire WHERE experiment_id = ?", (experiment_id,))
        self.conn.execute("DELETE FROM Workflow WHERE experiment_id = ?", (experiment_id,))
        self.conn.execute("DELETE FROM Experiment WHERE experiment_id = ?", (experiment_id,))

        self.conn.commit()

        # Clear caches for this experiment
        self._run_id_cache = {
            k: v for k, v in self._run_id_cache.items()
            if not k.startswith(f"{experiment_id}_")
        }

        logger.debug(f"Deleted all data for experiment: {experiment_id}")

    def checkpoint(self) -> None:
        """Force a WAL checkpoint to merge the -wal file into the main database."""
        self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def close(self) -> None:
        """Close the database connection.

        Converts from WAL mode to DELETE mode for portability, ensuring
        the database can be read by any SQLite client without requiring
        write access to create -shm/-wal files.
        """
        try:
            # Checkpoint WAL to merge -wal file into main database
            self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            # Convert to DELETE mode for portability
            self.conn.execute("PRAGMA journal_mode=DELETE")
        except Exception:
            pass  # Ignore if not in WAL mode or already closed
        self.conn.close()
