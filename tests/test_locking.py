"""Tests for file locking utilities."""

from __future__ import annotations

import pytest

from elogfetch.utils.locking import acquire_lock
from elogfetch.exceptions import LockError


class TestAcquireLock:
    """Tests for the acquire_lock context manager."""

    def test_acquire_lock_success(self, tmp_path):
        """Test that lock is acquired successfully."""
        lock_path = tmp_path / ".test.lock"

        with acquire_lock(lock_path) as lock_file:
            assert lock_file is not None
            assert lock_path.exists()

    def test_lock_released_on_exit(self, tmp_path):
        """Test that lock is released after context manager exits."""
        lock_path = tmp_path / ".test.lock"

        with acquire_lock(lock_path):
            pass

        # Should be able to acquire lock again after release
        with acquire_lock(lock_path) as lock_file:
            assert lock_file is not None

    def test_lock_blocks_concurrent_access(self, tmp_path):
        """Test that second lock attempt fails when lock is held."""
        lock_path = tmp_path / ".test.lock"

        with acquire_lock(lock_path):
            # Try to acquire same lock again (non-blocking)
            with pytest.raises(LockError) as exc_info:
                with acquire_lock(lock_path, blocking=False):
                    pass

            assert "Another instance is already running" in str(exc_info.value)

    def test_lock_creates_file(self, tmp_path):
        """Test that lock file is created if it doesn't exist."""
        lock_path = tmp_path / ".new_lock.lock"
        assert not lock_path.exists()

        with acquire_lock(lock_path):
            assert lock_path.exists()

    def test_lock_file_handle_valid(self, tmp_path):
        """Test that the yielded file handle is valid and writable."""
        lock_path = tmp_path / ".test.lock"

        with acquire_lock(lock_path) as lock_file:
            # Should be able to write to lock file
            lock_file.write("test content")
            lock_file.flush()

        # Verify content was written
        assert lock_path.read_text() == "test content"

    def test_multiple_sequential_locks(self, tmp_path):
        """Test that lock can be acquired multiple times sequentially."""
        lock_path = tmp_path / ".test.lock"

        for i in range(3):
            with acquire_lock(lock_path) as lock_file:
                lock_file.write(f"iteration {i}")
                lock_file.flush()

        # Last write should persist
        assert lock_path.read_text() == "iteration 2"

    def test_lock_with_exception(self, tmp_path):
        """Test that lock is released even if exception occurs."""
        lock_path = tmp_path / ".test.lock"

        with pytest.raises(ValueError):
            with acquire_lock(lock_path):
                raise ValueError("Test exception")

        # Should be able to acquire lock again after exception
        with acquire_lock(lock_path) as lock_file:
            assert lock_file is not None

    def test_nested_locks_different_files(self, tmp_path):
        """Test that different lock files can be held simultaneously."""
        lock_path1 = tmp_path / ".lock1"
        lock_path2 = tmp_path / ".lock2"

        with acquire_lock(lock_path1) as lock1:
            with acquire_lock(lock_path2) as lock2:
                assert lock1 is not None
                assert lock2 is not None
                assert lock_path1.exists()
                assert lock_path2.exists()
