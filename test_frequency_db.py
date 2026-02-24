"""
test_frequency_db.py – Unit tests for the frequency tracking database layer.
"""

import os
import tempfile
import pytest
import frequency_db


@pytest.fixture
def db_path(tmp_path):
    """Provide a fresh temporary database for each test."""
    path = str(tmp_path / "test_frequency.db")
    frequency_db.init_db(path)
    return path


class TestIsTrackable:
    """Tests for the is_trackable filter."""

    def test_short_words_rejected(self):
        assert not frequency_db.is_trackable("the")
        assert not frequency_db.is_trackable("a")
        assert not frequency_db.is_trackable("hi")

    def test_stop_words_rejected(self):
        assert not frequency_db.is_trackable("would")
        assert not frequency_db.is_trackable("should")
        assert not frequency_db.is_trackable("about")
        assert not frequency_db.is_trackable("every")

    def test_pure_numbers_rejected(self):
        assert not frequency_db.is_trackable("1234")
        assert not frequency_db.is_trackable("9999")

    def test_valid_words_accepted(self):
        assert frequency_db.is_trackable("hello")
        assert frequency_db.is_trackable("jsharpe")
        assert frequency_db.is_trackable("BuildOps")
        assert frequency_db.is_trackable("email")

    def test_mixed_alphanumeric_accepted(self):
        assert frequency_db.is_trackable("test123")
        assert frequency_db.is_trackable("v2beta")


class TestRecordPhrase:
    """Tests for inserting and incrementing phrases."""

    def test_single_insert(self, db_path):
        frequency_db.record_phrase("hello", db_path)
        results = frequency_db.get_top_phrases(min_count=1, db_path=db_path)
        assert len(results) == 1
        assert results[0]["phrase"] == "hello"
        assert results[0]["count"] == 1

    def test_increment_count(self, db_path):
        for _ in range(5):
            frequency_db.record_phrase("hello", db_path)
        results = frequency_db.get_top_phrases(min_count=1, db_path=db_path)
        assert results[0]["count"] == 5

    def test_case_normalization(self, db_path):
        frequency_db.record_phrase("Hello", db_path)
        frequency_db.record_phrase("HELLO", db_path)
        frequency_db.record_phrase("hello", db_path)
        results = frequency_db.get_top_phrases(min_count=1, db_path=db_path)
        assert len(results) == 1
        assert results[0]["phrase"] == "hello"
        assert results[0]["count"] == 3

    def test_stop_words_not_recorded(self, db_path):
        frequency_db.record_phrase("the", db_path)
        frequency_db.record_phrase("and", db_path)
        results = frequency_db.get_top_phrases(min_count=1, db_path=db_path)
        assert len(results) == 0

    def test_short_words_not_recorded(self, db_path):
        frequency_db.record_phrase("hi", db_path)
        frequency_db.record_phrase("ok", db_path)
        results = frequency_db.get_top_phrases(min_count=1, db_path=db_path)
        assert len(results) == 0


class TestBatchRecord:
    """Tests for batch recording."""

    def test_batch_insert(self, db_path):
        words = ["hello", "world", "hello", "python", "hello"]
        frequency_db.record_phrases_batch(words, db_path)
        results = frequency_db.get_top_phrases(min_count=1, db_path=db_path)
        phrases = {r["phrase"]: r["count"] for r in results}
        assert phrases["hello"] == 3
        assert phrases["world"] == 1
        assert phrases["python"] == 1

    def test_batch_filters_stop_words(self, db_path):
        words = ["the", "hello", "and", "world", "is"]
        frequency_db.record_phrases_batch(words, db_path)
        results = frequency_db.get_top_phrases(min_count=1, db_path=db_path)
        phrases = [r["phrase"] for r in results]
        assert "the" not in phrases
        assert "and" not in phrases
        assert "hello" in phrases
        assert "world" in phrases


class TestGetTopPhrases:
    """Tests for retrieving top phrases."""

    def test_min_count_filter(self, db_path):
        for _ in range(5):
            frequency_db.record_phrase("frequent", db_path)
        frequency_db.record_phrase("rare", db_path)
        results = frequency_db.get_top_phrases(min_count=3, db_path=db_path)
        assert len(results) == 1
        assert results[0]["phrase"] == "frequent"

    def test_limit(self, db_path):
        for i in range(10):
            word = f"word{i:04d}"
            for _ in range(10 - i):
                frequency_db.record_phrase(word, db_path)
        results = frequency_db.get_top_phrases(min_count=1, limit=3, db_path=db_path)
        assert len(results) == 3

    def test_exclude_filter(self, db_path):
        for _ in range(5):
            frequency_db.record_phrase("hello", db_path)
            frequency_db.record_phrase("world", db_path)
        results = frequency_db.get_top_phrases(
            min_count=1, exclude={"hello"}, db_path=db_path
        )
        phrases = [r["phrase"] for r in results]
        assert "hello" not in phrases
        assert "world" in phrases

    def test_ordered_by_count_desc(self, db_path):
        for _ in range(10):
            frequency_db.record_phrase("alpha", db_path)
        for _ in range(5):
            frequency_db.record_phrase("bravo", db_path)
        for _ in range(8):
            frequency_db.record_phrase("charlie", db_path)
        results = frequency_db.get_top_phrases(min_count=1, db_path=db_path)
        counts = [r["count"] for r in results]
        assert counts == sorted(counts, reverse=True)


class TestDismissPhrase:
    """Tests for dismissing/removing a phrase."""

    def test_dismiss_removes_phrase(self, db_path):
        for _ in range(5):
            frequency_db.record_phrase("hello", db_path)
        frequency_db.dismiss_phrase("hello", db_path)
        results = frequency_db.get_top_phrases(min_count=1, db_path=db_path)
        assert len(results) == 0

    def test_dismiss_nonexistent_no_error(self, db_path):
        # Should not raise
        frequency_db.dismiss_phrase("nonexistent", db_path)


class TestGetPhraseStats:
    """Tests for summary statistics."""

    def test_empty_db(self, db_path):
        stats = frequency_db.get_phrase_stats(db_path)
        assert stats["total_phrases"] == 0
        assert stats["total_counts"] == 0

    def test_with_data(self, db_path):
        for _ in range(3):
            frequency_db.record_phrase("hello", db_path)
        for _ in range(2):
            frequency_db.record_phrase("world", db_path)
        stats = frequency_db.get_phrase_stats(db_path)
        assert stats["total_phrases"] == 2
        assert stats["total_counts"] == 5
