"""File locking utilities for fetch-elog."""

from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, IO

from ..exceptions import LockError


@contextmanager
def acquire_lock(
    lock_path: Path,
    blocking: bool = False,
) -> Generator[IO, None, None]:
    """Acquire an exclusive lock on a file.

    Args:
        lock_path: Path to the lock file
        blocking: If True, wait for the lock; if False, fail immediately

    Yields:
        The lock file handle

    Raises:
        LockError: If the lock cannot be acquired
    """
    lock_file = open(lock_path, "w")
    try:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB

        try:
            fcntl.flock(lock_file, flags)
        except BlockingIOError:
            lock_file.close()
            raise LockError(
                f"Another instance is already running (lock: {lock_path})"
            )

        yield lock_file

    finally:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        except Exception:
            pass
        lock_file.close()
