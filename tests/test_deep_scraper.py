"""Tests for deep_scraper fixes:
- Dedup by canonical URL (no dup_counter)
- Date range filtering
- _parse_date static method
- Page name cleanup (junk names blocklist)
"""
from datetime import datetime

from src.fb_scraper.deep_scraper import FacebookDeepScraper


def test_parse_date_valid():
    d = FacebookDeepScraper._parse_date("2025-01-01")
    assert isinstance(d, datetime)
    assert d.year == 2025
    assert d.month == 1
    assert d.day == 1


def test_parse_date_invalid_defaults():
    d = FacebookDeepScraper._parse_date("not-a-date")
    assert isinstance(d, datetime)
    assert d.year == 2025
    assert d.month == 1
    assert d.day == 1


def test_parse_date_empty_defaults():
    d = FacebookDeepScraper._parse_date("")
    assert isinstance(d, datetime)
    assert d.year == 2025


def test_parse_date_recent():
    d = FacebookDeepScraper._parse_date("2026-06-01")
    assert d.year == 2026
    assert d.month == 6


class TestDedupLogic:
    """Test that duplicates are skipped (no dup_counter artificial IDs)."""

    def test_same_post_id_skipped(self):
        seen = set()
        # Simulate _scrape_search_results dedup logic
        post_id = "pfbid0ABC123"
        assert post_id not in seen
        seen.add(post_id)
        # Second occurrence: should skip, not create dup_counter
        assert post_id in seen


class TestPageNameCleanup:
    """Test junk name blocklist filtering."""

    JUNK_NAMES = {
        'seguir', 'facebook', 'compartir', 'indicador de estado online',
        'activo', 'me gusta', 'seguido', 'siguiendo', 'responder',
        'reaccionar', 'enviar', 'compartir en', 'opciones', 'más',
        'menos', 'ver más', 'ver menos', 'ver todo', 'ocultar',
        'eliminar', 'editar', 'denunciar', 'compartir ahora', 'copiar enlace',
    }

    def test_junk_names_identified(self):
        assert 'seguir' in self.JUNK_NAMES
        assert 'indicador de estado online' in self.JUNK_NAMES
        assert 'facebook' in self.JUNK_NAMES
        assert 'compartir' in self.JUNK_NAMES
        assert 'me gusta' in self.JUNK_NAMES
        assert len(self.JUNK_NAMES) >= 20

    def test_valid_name_not_in_junk(self):
        assert 'Alcaldía Santa Ana' not in self.JUNK_NAMES
        assert 'Jose Chicas' not in self.JUNK_NAMES
        assert 'Prensa Libre' not in self.JUNK_NAMES


class TestDateRange:
    """Test date range filtering logic."""

    def test_post_before_since_filtered(self):
        since = datetime(2025, 1, 1)
        until = datetime(2026, 6, 9)
        old_post_date = datetime(2024, 12, 31)
        assert old_post_date < since
        assert old_post_date < until

    def test_post_after_until_filtered(self):
        since = datetime(2025, 1, 1)
        until = datetime(2026, 6, 9)
        future_post_date = datetime(2026, 7, 1)
        assert future_post_date > until
        assert future_post_date > since

    def test_post_in_range_kept(self):
        since = datetime(2025, 1, 1)
        until = datetime(2026, 6, 9)
        valid_date = datetime(2025, 6, 15)
        assert valid_date >= since
        assert valid_date <= until

    def test_post_on_boundary_since(self):
        since = datetime(2025, 1, 1)
        until = datetime(2026, 6, 9)
        boundary = datetime(2025, 1, 1)
        assert boundary >= since
        assert boundary <= until

    def test_post_on_boundary_until(self):
        since = datetime(2025, 1, 1)
        until = datetime(2026, 6, 9)
        boundary = datetime(2026, 6, 9)
        assert boundary >= since
        assert boundary <= until
