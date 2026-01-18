"""Tests for database operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from elogfetch.storage.database import Database


class TestDatabaseCreation:
    """Tests for database initialization."""

    def test_database_creation(self, tmp_path):
        """Verify tables and indexes are created correctly."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)

        # Verify tables exist
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "Detector",
            "Experiment",
            "Logbook",
            "Metadata",
            "Questionnaire",
            "Run",
            "RunDetector",
            "RunProductionData",
            "Workflow",
        }
        assert expected_tables.issubset(tables)

        # Verify indexes exist
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        expected_indexes = {
            "idx_questionnaire_experiment",
            "idx_questionnaire_category",
            "idx_questionnaire_proposal",
            "idx_run_experiment",
            "idx_logbook_experiment",
            "idx_logbook_run",
        }
        assert expected_indexes.issubset(indexes)

        db.close()

    def test_database_file_created(self, tmp_path):
        """Verify database file is created on disk."""
        db_path = tmp_path / "test.db"
        assert not db_path.exists()

        db = Database(db_path)
        assert db_path.exists()

        db.close()


class TestWALMode:
    """Tests for Write-Ahead Logging mode."""

    def test_wal_mode_enabled(self, tmp_path):
        """Verify WAL mode is activated."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.enable_wal_mode()

        cursor = db.conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

        db.close()

    def test_close_removes_wal_files(self, tmp_path, sample_experiment_data):
        """Verify WAL and SHM files are removed when database is closed.

        This is a critical test - WAL files left behind can cause issues
        with database copying and backup.
        """
        db_path = tmp_path / "test.db"
        wal_path = tmp_path / "test.db-wal"
        shm_path = tmp_path / "test.db-shm"

        db = Database(db_path)
        db.enable_wal_mode()

        # Do some writes to create WAL file
        db.insert_experiment(sample_experiment_data)
        db.commit()

        # Close should checkpoint and remove WAL files
        db.close()

        assert db_path.exists(), "Database file should exist"
        assert not wal_path.exists(), "WAL file should be removed after close"
        assert not shm_path.exists(), "SHM file should be removed after close"


class TestExperimentOperations:
    """Tests for experiment CRUD operations."""

    def test_insert_and_query_experiment(self, tmp_path, sample_experiment_data):
        """Test inserting and querying experiment data."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)

        db.insert_experiment(sample_experiment_data)

        cursor = db.conn.execute(
            "SELECT * FROM Experiment WHERE experiment_id = ?",
            (sample_experiment_data["experiment_id"],),
        )
        row = cursor.fetchone()

        assert row is not None
        assert row["experiment_id"] == sample_experiment_data["experiment_id"]
        assert row["name"] == sample_experiment_data["name"]
        assert row["instrument"] == sample_experiment_data["instrument"]
        assert row["pi"] == sample_experiment_data["pi"]

        db.close()

    def test_insert_experiment_batch(
        self,
        tmp_path,
        sample_experiment_data,
        sample_logbook_entries,
        sample_questionnaire_data,
        sample_workflow_data,
    ):
        """Test batch insert of experiment with related data."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)

        batch_data = {
            "info": sample_experiment_data,
            "logbook": sample_logbook_entries,
            "questionnaire": sample_questionnaire_data,
            "workflow": sample_workflow_data,
        }

        db.insert_experiment_batch(batch_data)
        db.commit()

        # Verify experiment
        cursor = db.conn.execute("SELECT COUNT(*) FROM Experiment")
        assert cursor.fetchone()[0] == 1

        # Verify logbook entries
        cursor = db.conn.execute("SELECT COUNT(*) FROM Logbook")
        assert cursor.fetchone()[0] == 3

        # Verify questionnaire fields
        cursor = db.conn.execute("SELECT COUNT(*) FROM Questionnaire")
        assert cursor.fetchone()[0] == 2

        # Verify workflows
        cursor = db.conn.execute("SELECT COUNT(*) FROM Workflow")
        assert cursor.fetchone()[0] == 1

        db.close()

    def test_delete_experiment_cascade(
        self,
        tmp_path,
        sample_experiment_data,
        sample_logbook_entries,
        sample_runtable_data,
    ):
        """Test cascade deletion of experiment and related data."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)

        # Insert experiment with related data
        db.insert_experiment(sample_experiment_data)
        db.insert_logbook(sample_logbook_entries)
        db.insert_runtable(sample_runtable_data)

        experiment_id = sample_experiment_data["experiment_id"]

        # Verify data exists before deletion
        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM Experiment WHERE experiment_id = ?",
            (experiment_id,),
        )
        assert cursor.fetchone()[0] == 1

        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM Run WHERE experiment_id = ?",
            (experiment_id,),
        )
        assert cursor.fetchone()[0] > 0

        # Delete experiment
        db.delete_experiment(experiment_id)

        # Verify cascade deletion
        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM Experiment WHERE experiment_id = ?",
            (experiment_id,),
        )
        assert cursor.fetchone()[0] == 0

        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM Run WHERE experiment_id = ?",
            (experiment_id,),
        )
        assert cursor.fetchone()[0] == 0

        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM Logbook WHERE experiment_id = ?",
            (experiment_id,),
        )
        assert cursor.fetchone()[0] == 0

        db.close()


class TestMetadataOperations:
    """Tests for metadata storage."""

    def test_metadata_operations(self, tmp_path):
        """Test set_metadata and get_metadata work correctly."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)

        # Test setting and getting metadata
        db.set_metadata("last_update", "2024-01-15T10:00:00")
        db.set_metadata("version", "1.0.0")

        assert db.get_metadata("last_update") == "2024-01-15T10:00:00"
        assert db.get_metadata("version") == "1.0.0"
        assert db.get_metadata("nonexistent") is None

        # Test updating metadata
        db.set_metadata("last_update", "2024-01-16T12:00:00")
        assert db.get_metadata("last_update") == "2024-01-16T12:00:00"

        db.close()


class TestStatistics:
    """Tests for database statistics."""

    def test_get_stats(
        self,
        tmp_path,
        sample_experiment_data,
        sample_logbook_entries,
        sample_runtable_data,
    ):
        """Test statistics query returns correct counts."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)

        # Insert some data
        db.insert_experiment(sample_experiment_data)
        db.insert_logbook(sample_logbook_entries)
        db.insert_runtable(sample_runtable_data)

        stats = db.get_stats()

        assert stats["experiment"] == 1
        assert stats["logbook"] == 3
        assert stats["run"] >= 2  # From logbook and runtable

        db.close()

    def test_get_stats_empty_database(self, tmp_path):
        """Test statistics on empty database."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)

        stats = db.get_stats()

        assert stats["experiment"] == 0
        assert stats["run"] == 0
        assert stats["logbook"] == 0
        assert stats["questionnaire"] == 0
        assert stats["workflow"] == 0

        db.close()


class TestRunAndDetectorOperations:
    """Tests for run and detector data."""

    def test_runtable_insert(self, tmp_path, sample_experiment_data, sample_runtable_data):
        """Test inserting run table data."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)

        db.insert_experiment(sample_experiment_data)
        db.insert_runtable(sample_runtable_data)

        # Check runs were created
        cursor = db.conn.execute("SELECT COUNT(*) FROM Run")
        assert cursor.fetchone()[0] == 2

        # Check production data was inserted
        cursor = db.conn.execute("SELECT COUNT(*) FROM RunProductionData")
        assert cursor.fetchone()[0] == 2

        # Check detectors were created
        cursor = db.conn.execute("SELECT COUNT(*) FROM Detector")
        assert cursor.fetchone()[0] == 2  # cspad and epix

        db.close()

    def test_file_manager_insert(
        self, tmp_path, sample_experiment_data, sample_file_manager_data
    ):
        """Test inserting file manager data."""
        db_path = tmp_path / "test.db"
        db = Database(db_path)

        db.insert_experiment(sample_experiment_data)
        db.insert_file_manager(sample_file_manager_data)

        cursor = db.conn.execute(
            """
            SELECT number_of_files, total_size_bytes
            FROM RunProductionData rpd
            JOIN Run r ON rpd.run_id = r.run_id
            WHERE r.run_number = 1
            """
        )
        row = cursor.fetchone()
        assert row["number_of_files"] == 10
        assert row["total_size_bytes"] == 1073741824

        db.close()
