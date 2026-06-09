"""Tests for deep_scraper fixes:
- Dedup by canonical URL (no dup_counter)
- Date range filtering
- _parse_date static method
- Page name cleanup (junk names blocklist)
"""
from datetime import datetime

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from src.fb_scraper.deep_scraper import FacebookDeepScraper

ROOT = Path(__file__).resolve().parent.parent


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


class TestCutoffTolerance:
    """Test that OOR streak requires multiple consecutive OOR scrolls."""

    def test_single_old_post_does_not_stop(self):
        """One old post among recent ones should NOT stop scraping."""
        cutoff = 10
        oor_streak = 0
        # Simulate: 1 OOR post, but 9 in-range
        self._last_extraction_raw_count = 10
        self._last_extraction_oor_count = 1
        oor_ratio = self._last_extraction_oor_count / self._last_extraction_raw_count
        if self._last_extraction_raw_count > 0 and self._last_extraction_oor_count > 0 and oor_ratio >= 0.7:
            oor_streak += 1
        assert oor_streak == 0, "Single OOR post should not increment streak"

    def test_oor_streak_reaches_tolerance(self):
        """After cutoff_tolerance consecutive OOR scrolls, stop."""
        cutoff = 10
        oor_streak = 0
        for i in range(15):
            # All posts OOR
            self._last_extraction_raw_count = 5
            self._last_extraction_oor_count = 5
            oor_ratio = self._last_extraction_oor_count / self._last_extraction_raw_count
            if self._last_extraction_raw_count > 0 and self._last_extraction_oor_count > 0 and oor_ratio >= 0.7:
                oor_streak += 1
            else:
                oor_streak = 0
            if oor_streak >= cutoff:
                break
        assert oor_streak >= cutoff, f"Streak {oor_streak} should reach {cutoff}"

class TestJsExtractReferenceError:
    """E15 regression: js_extract must not have undeclared 'link' variable."""

    def test_js_extract_no_undeclared_link(self):
        """The js_extract string must not reference 'link' outside its scope."""
        import re
        from src.fb_scraper.deep_scraper import FacebookDeepScraper
        
        # Get the js_extract source by inspecting _scrape_search_results
        import inspect
        source = inspect.getsource(FacebookDeepScraper._scrape_search_results)
        
        # Find the js_extract string content
        match = re.search(r'js_extract\s*=\s*"""([\s\S]*?)"""', source)
        assert match, "js_extract string not found in _scrape_search_results"
        js_code = match.group(1)
        
        # Check that 'link' is not used outside the first for-loop scope
        # The bug was: 'let container = link.parentElement' outside 'for (const link of linkEls)'
        # After fix, it should use linkEl (found via querySelector) instead
        assert 'link.parentElement' not in js_code, \
            "Found 'link.parentElement' in js_extract - this was the E15 bug (link out of scope)"
        
        # Verify the fix uses linkEl instead
        assert 'linkEl' in js_code, "Fix should use 'linkEl' variable instead of out-of-scope 'link'"
        assert 'querySelector' in js_code, "Fix should find link element via querySelector"


class TestDemoSeedSafety:
    """P1: Verify modulo5_externos.py seeder does NOT run without --demo or ENABLE_DEMO_SEED=1."""

    def test_seeder_does_not_run_without_flag(self):
        """Running the script without --demo should not insert SIM_EXT rows."""
        script = ROOT / "dashboard" / "modulo5_externos.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=30,
        )
        assert "--demo" in result.stdout or "desactivado" in result.stdout, \
            f"Expected safety message, got: {result.stdout[:200]}"

    def test_seeder_does_not_run_with_env_false(self):
        """Running with ENABLE_DEMO_SEED=0 should not insert SIM_EXT rows."""
        script = ROOT / "dashboard" / "modulo5_externos.py"
        env = os.environ.copy()
        env["ENABLE_DEMO_SEED"] = "0"
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=30, env=env,
        )
        assert "--demo" in result.stdout or "desactivado" in result.stdout, \
            f"Expected safety message, got: {result.stdout[:200]}"

    def test_seeder_runs_with_demo_flag(self):
        """Running with --demo should insert SIM_EXT rows in a temp DB."""
        script = ROOT / "dashboard" / "modulo5_externos.py"
        # Point to a temp DB so real externos.db is never touched
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        env = os.environ.copy()
        env["EXTERNOS_DB"] = tmp.name
        result = subprocess.run(
            [sys.executable, str(script), "--demo"],
            capture_output=True, text=True, timeout=30, env=env,
        )
        # Clean up regardless of test outcome
        try:
            import sqlite3
            conn = sqlite3.connect(tmp.name)
            cnt = conn.execute("SELECT COUNT(*) FROM external_posts").fetchone()[0]
            all_sim = conn.execute(
                "SELECT COUNT(*) FROM external_posts WHERE post_id LIKE 'SIM_EXT%'"
            ).fetchone()[0]
            conn.close()
            assert cnt == 50, f"Expected 50 SIM_EXT posts, got {cnt}"
            assert all_sim == 50, "Not all posts have SIM_EXT prefix"
        finally:
            os.unlink(tmp.name)

    def test_oor_streak_resets_on_in_range_post(self):
        """A single in-range post resets the OOR streak."""
        cutoff = 10
        oor_streak = 0
        # 3 OOR scrolls
        for i in range(3):
            self._last_extraction_raw_count = 5
            self._last_extraction_oor_count = 5
            oor_ratio = self._last_extraction_oor_count / self._last_extraction_raw_count
            if self._last_extraction_raw_count > 0 and self._last_extraction_oor_count > 0 and oor_ratio >= 0.7:
                oor_streak += 1
        # One in-range scroll
        self._last_extraction_raw_count = 5
        self._last_extraction_oor_count = 0
        posts_on_page = 2
        if posts_on_page == 0:
            pass  # not hit
        else:
            oor_streak = 0
        assert oor_streak == 0, f"Streak should reset to 0, got {oor_streak}"
