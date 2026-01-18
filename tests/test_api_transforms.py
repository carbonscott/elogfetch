"""Tests for API data transformation functions."""

from __future__ import annotations

import pytest

from elogfetch.api.experiments import _filter_experiments


class TestFilterExperiments:
    """Tests for experiment filtering functionality."""

    def test_filter_experiments_single_wildcard(self):
        """Test that single wildcard pattern excludes matching experiments."""
        experiments = ["test123", "test456", "cxic00123", "mfxc00456"]
        patterns = ["test*"]

        result = _filter_experiments(experiments, patterns)

        assert "test123" not in result
        assert "test456" not in result
        assert "cxic00123" in result
        assert "mfxc00456" in result

    def test_filter_experiments_multiple_patterns(self):
        """Test that multiple patterns work correctly together."""
        experiments = [
            "test123",
            "txi00456",
            "cxic00123",
            "mfxc00456",
            "debug789",
        ]
        patterns = ["txi*", "test*"]

        result = _filter_experiments(experiments, patterns)

        assert "test123" not in result
        assert "txi00456" not in result
        assert "cxic00123" in result
        assert "mfxc00456" in result
        assert "debug789" in result

    def test_filter_experiments_case_insensitive(self):
        """Test that pattern matching is case-insensitive."""
        experiments = ["TEST123", "Test456", "test789", "CXIc00123"]
        patterns = ["test*"]

        result = _filter_experiments(experiments, patterns)

        assert "TEST123" not in result
        assert "Test456" not in result
        assert "test789" not in result
        assert "CXIc00123" in result

    def test_filter_experiments_no_match(self):
        """Test that unmatched experiments are preserved."""
        experiments = ["cxic00123", "mfxc00456", "xppc00789"]
        patterns = ["test*", "debug*"]

        result = _filter_experiments(experiments, patterns)

        assert len(result) == 3
        assert result == experiments

    def test_filter_experiments_question_mark(self):
        """Test that ? wildcard matches single character."""
        experiments = ["cxi1", "cxi12", "cxi123", "mfx1"]
        patterns = ["cxi?"]

        result = _filter_experiments(experiments, patterns)

        assert "cxi1" not in result  # Matches cxi?
        assert "cxi12" in result  # Doesn't match (2 chars after cxi)
        assert "cxi123" in result  # Doesn't match (3 chars after cxi)
        assert "mfx1" in result  # Different prefix

    def test_filter_experiments_exact_match(self):
        """Test exact match pattern without wildcards."""
        experiments = ["test", "test123", "testing", "cxic00123"]
        patterns = ["test"]

        result = _filter_experiments(experiments, patterns)

        assert "test" not in result  # Exact match
        assert "test123" in result  # Not an exact match
        assert "testing" in result  # Not an exact match
        assert "cxic00123" in result

    def test_filter_experiments_empty_patterns(self):
        """Test that empty pattern list returns all experiments."""
        experiments = ["cxic00123", "mfxc00456", "test123"]
        patterns = []

        result = _filter_experiments(experiments, patterns)

        assert result == experiments

    def test_filter_experiments_empty_experiments(self):
        """Test that empty experiment list returns empty list."""
        experiments = []
        patterns = ["test*"]

        result = _filter_experiments(experiments, patterns)

        assert result == []

    def test_filter_experiments_all_filtered(self):
        """Test when all experiments match filter patterns."""
        experiments = ["test1", "test2", "test3"]
        patterns = ["test*"]

        result = _filter_experiments(experiments, patterns)

        assert result == []

    def test_filter_experiments_complex_pattern(self):
        """Test complex pattern with multiple wildcards."""
        experiments = [
            "cxic00123",
            "cxic00456",
            "cxi_test_123",
            "mfxc00789",
        ]
        patterns = ["cxi*123"]

        result = _filter_experiments(experiments, patterns)

        assert "cxic00123" not in result  # Matches cxi*123
        assert "cxi_test_123" not in result  # Matches cxi*123
        assert "cxic00456" in result  # Doesn't end in 123
        assert "mfxc00789" in result  # Different prefix

    def test_filter_experiments_preserves_order(self):
        """Test that filtering preserves the order of experiments."""
        experiments = ["z_exp", "a_exp", "m_exp", "test1", "b_exp"]
        patterns = ["test*"]

        result = _filter_experiments(experiments, patterns)

        assert result == ["z_exp", "a_exp", "m_exp", "b_exp"]
