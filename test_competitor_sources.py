"""Unit tests for competitor_sources.py crawler functionality."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from competitor_sources import (
    _extract_chunks,
    _hash_chunk,
    _load_state,
    _save_state,
    get_active_competitors,
    Competitor,
)


class TestCompetitorFiltering(unittest.TestCase):
    """Test competitor filtering by priority."""

    def test_get_active_competitors_priority_1(self):
        """Should return only priority 1 competitors (top 5)."""
        competitors = get_active_competitors(max_priority=1)
        names = [c.name for c in competitors]

        # Top 5: NetSuite, SAP, Workday, Rillet, DualEntry
        self.assertIn("NetSuite", names)
        self.assertIn("SAP", names)
        self.assertIn("Workday", names)
        self.assertIn("Rillet", names)
        self.assertIn("DualEntry", names)

        # Should not include priority 2 or 3
        self.assertNotIn("Oracle", names)
        self.assertNotIn("Acumatica", names)

    def test_get_active_competitors_priority_2(self):
        """Should return priority 1 and 2 competitors."""
        competitors = get_active_competitors(max_priority=2)
        names = [c.name for c in competitors]

        # Should include priority 1
        self.assertIn("NetSuite", names)

        # Should include priority 2
        self.assertIn("Oracle", names)
        self.assertIn("Digits", names)

        # Should not include priority 3
        self.assertNotIn("Acumatica", names)

    def test_get_active_competitors_all(self):
        """Should return all competitors when max_priority=3."""
        competitors = get_active_competitors(max_priority=3)
        names = [c.name for c in competitors]

        # Should include all priorities
        self.assertIn("NetSuite", names)
        self.assertIn("Oracle", names)
        self.assertIn("Acumatica", names)


class TestChunkExtraction(unittest.TestCase):
    """Test HTML content extraction and chunking."""

    def test_extract_chunks_with_headings(self):
        """Should split content by H2/H3 headings."""
        html = """
        <html><body>
            <main>
                <h2>New Feature: AI Assistant</h2>
                <p>We've launched an AI-powered assistant that helps you automate
                   your accounting workflows. This feature uses machine learning
                   to categorize transactions and detect anomalies in real-time.</p>

                <h3>Revenue Recognition Updates</h3>
                <p>Enhanced support for ASC 606 compliance with automated revenue
                   schedules. The system now handles multi-element arrangements
                   and subscription revenue recognition with ease.</p>
            </main>
        </body></html>
        """

        chunks = _extract_chunks(html)

        # Should extract 2 chunks
        self.assertEqual(len(chunks), 2)

        # Check first chunk
        heading1, text1 = chunks[0]
        self.assertEqual(heading1, "New Feature: AI Assistant")
        self.assertIn("AI-powered assistant", text1)
        self.assertIn("accounting workflows", text1)

        # Check second chunk
        heading2, text2 = chunks[1]
        self.assertEqual(heading2, "Revenue Recognition Updates")
        self.assertIn("ASC 606", text2)
        self.assertIn("subscription revenue", text2)

    def test_extract_chunks_removes_noise(self):
        """Should filter out navigation, footer, and sidebar content."""
        html = """
        <html><body>
            <nav><a href="#">Home</a><a href="#">About</a></nav>
            <main>
                <h2>Important Feature</h2>
                <p>This is the main content that should be extracted because
                   it contains substantial information about the product feature
                   and its capabilities.</p>
            </main>
            <footer>Copyright 2025</footer>
        </body></html>
        """

        chunks = _extract_chunks(html)

        # Should only extract main content
        self.assertEqual(len(chunks), 1)
        heading, text = chunks[0]
        self.assertEqual(heading, "Important Feature")

        # Should not contain navigation or footer text
        self.assertNotIn("Home", text)
        self.assertNotIn("Copyright", text)

    def test_extract_chunks_filters_short_content(self):
        """Should filter out chunks with less than 200 characters."""
        html = """
        <html><body>
            <main>
                <h2>Short</h2>
                <p>Too short.</p>

                <h2>Long Enough</h2>
                <p>This paragraph has enough content to be considered a substantial
                   chunk of text that provides meaningful information about a feature
                   or capability change in the product documentation or release notes
                   and therefore should be included in the extracted chunks.</p>
            </main>
        </body></html>
        """

        chunks = _extract_chunks(html)

        # Should only extract the long chunk
        self.assertEqual(len(chunks), 1)
        heading, text = chunks[0]
        self.assertEqual(heading, "Long Enough")


class TestChunkHashing(unittest.TestCase):
    """Test chunk hashing for change detection."""

    def test_hash_chunk_consistent(self):
        """Same content should produce the same hash."""
        heading = "New Feature"
        text = "This is the feature description."

        hash1 = _hash_chunk(heading, text)
        hash2 = _hash_chunk(heading, text)

        self.assertEqual(hash1, hash2)

    def test_hash_chunk_different_text(self):
        """Different text should produce different hashes."""
        heading = "Feature"
        text1 = "Original description."
        text2 = "Updated description."

        hash1 = _hash_chunk(heading, text1)
        hash2 = _hash_chunk(heading, text2)

        self.assertNotEqual(hash1, hash2)

    def test_hash_chunk_different_heading(self):
        """Different headings should produce different hashes."""
        text = "Same content."
        heading1 = "Feature A"
        heading2 = "Feature B"

        hash1 = _hash_chunk(heading1, text)
        hash2 = _hash_chunk(heading2, text)

        self.assertNotEqual(hash1, hash2)


class TestStateManagement(unittest.TestCase):
    """Test state persistence for crawl tracking."""

    def test_load_state_empty(self):
        """Should return empty dict when no state exists."""
        mock_db = Mock()
        mock_db.get.return_value = None

        state = _load_state(mock_db)

        self.assertEqual(state, {})

    def test_load_state_with_data(self):
        """Should load existing state from database."""
        mock_row = Mock()
        mock_row.value = {
            "https://example.com": {
                "Feature A": "hash123",
                "Feature B": "hash456",
            }
        }

        mock_db = Mock()
        mock_db.get.return_value = mock_row

        state = _load_state(mock_db)

        self.assertIn("https://example.com", state)
        self.assertEqual(state["https://example.com"]["Feature A"], "hash123")

    def test_save_state_creates_new(self):
        """Should create new SyncState row if none exists."""
        mock_db = Mock()
        mock_db.get.return_value = None

        state = {"https://example.com": {"Feature": "hash"}}
        _save_state(mock_db, state)

        # Should add new row and commit
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_save_state_updates_existing(self):
        """Should update existing SyncState row."""
        mock_row = Mock()
        mock_row.value = {}

        mock_db = Mock()
        mock_db.get.return_value = mock_row

        state = {"https://example.com": {"Feature": "hash"}}
        _save_state(mock_db, state)

        # Should update row value and commit
        self.assertEqual(mock_row.value, state)
        mock_db.commit.assert_called_once()


class TestChangeDetection(unittest.TestCase):
    """Test detection of content changes."""

    def test_detects_new_chunk(self):
        """Should detect a chunk that doesn't exist in state."""
        old_state = {}
        heading = "New Feature"
        text = "This feature is brand new."
        chunk_hash = _hash_chunk(heading, text)

        # Simulate checking if chunk is new
        key = heading[:120]
        is_new = old_state.get(key) != chunk_hash

        self.assertTrue(is_new)

    def test_detects_changed_chunk(self):
        """Should detect when a chunk's content has changed."""
        old_state = {"Feature": "old_hash_123"}
        heading = "Feature"
        text = "Updated content for the feature."
        chunk_hash = _hash_chunk(heading, text)

        # Simulate checking if chunk changed
        key = heading[:120]
        has_changed = old_state.get(key) != chunk_hash

        self.assertTrue(has_changed)

    def test_unchanged_chunk(self):
        """Should not flag unchanged chunks."""
        heading = "Feature"
        text = "Same content."
        chunk_hash = _hash_chunk(heading, text)
        old_state = {"Feature": chunk_hash}

        # Simulate checking if chunk changed
        key = heading[:120]
        has_changed = old_state.get(key) != chunk_hash

        self.assertFalse(has_changed)


if __name__ == "__main__":
    unittest.main()
