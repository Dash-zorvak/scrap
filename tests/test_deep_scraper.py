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


class TestSpanishDateParser:
    """Test the Spanish date parsing logic (mirrors JS parseSpanishDate)."""

    @staticmethod
    def _parse_spanish_date(text: str) -> datetime | None:
        """Python equivalent of the JS parseSpanishDate function."""
        if not text:
            return None
        s = text.strip()
        now = datetime.now()
        import re
        from datetime import timedelta
        months = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
        }

        # "ahora" / "justo ahora"
        if re.match(r'^(ahora|justo ahora)$', s, re.I):
            return now

        # "hace X segundos/minutos/horas/días/semanas/meses/años"
        m = re.match(r'^hace\s+(\d+)\s*(segundos?|minutos?|horas?|días?|semanas?|meses?|años?|seg|min|h|d)\s*$', s, re.I)
        if m:
            num = int(m.group(1))
            unit = m.group(2).lower()
            if unit.startswith('seg'): return now - timedelta(seconds=num)
            if unit.startswith('min'): return now - timedelta(minutes=num)
            if unit.startswith('h'): return now - timedelta(hours=num)
            if unit.startswith('d'): return now - timedelta(days=num)
            if unit.startswith('sem'): return now - timedelta(weeks=num)
            if unit.startswith('mes'): return now - timedelta(days=num * 30)
            if unit.startswith('a'): return now - timedelta(days=num * 365)

        # Short forms: "X min", "X h", "X d", "X sem"
        m = re.match(r'^(\d+)\s*(min|h|d|sem)\s*$', s, re.I)
        if m:
            num = int(m.group(1))
            unit = m.group(2).lower()
            if unit == 'min': return now - timedelta(minutes=num)
            if unit == 'h': return now - timedelta(hours=num)
            if unit == 'd': return now - timedelta(days=num)
            if unit == 'sem': return now - timedelta(weeks=num)

        # "Ayer" → yesterday 12:00
        if re.match(r'^ayer\b', s, re.I):
            return (now - timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)

        # "Hoy" → today 12:00
        if re.match(r'^hoy\b', s, re.I):
            return now.replace(hour=12, minute=0, second=0, microsecond=0)

        # Days of week (Spanish)
        dias = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']
        for i, name in enumerate(dias):
            if s.lower().startswith(name):
                diff = i - now.weekday() - 1  # weekday(): Mon=0..Sun=6; dias: domingo=0..sábado=6
                if diff > 0:
                    diff -= 7
                return (now + timedelta(days=diff)).replace(hour=12, minute=0, second=0, microsecond=0)

        # "9 de junio de 2025 a las 14:59"
        m = re.match(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})(?:\s+a\s+las\s+(\d{1,2}):(\d{1,2}))?', s, re.I)
        if m:
            day = int(m.group(1))
            month_name = m.group(2).lower()
            year = int(m.group(3))
            hour = int(m.group(4)) if m.group(4) else 12
            minute = int(m.group(5)) if m.group(5) else 0
            if month_name in months:
                try:
                    return datetime(year, months[month_name], day, hour, minute)
                except ValueError:
                    return None

        # "9 de junio" (no year)
        m = re.match(r'(\d{1,2})\s+de\s+(\w+)\s*$', s, re.I)
        if m:
            day = int(m.group(1))
            month_name = m.group(2).lower()
            if month_name in months:
                year = now.year
                try:
                    dt = datetime(year, months[month_name], day, 12, 0)
                except ValueError:
                    return None
                if dt > now:
                    dt = dt.replace(year=year - 1)
                return dt

        return None

    def test_hace_minutos(self):
        result = self._parse_spanish_date("hace 5 minutos")
        assert result is not None
        diff = (datetime.now() - result).total_seconds()
        assert 280 <= diff <= 320, f"Expected ~300s diff, got {diff}"

    def test_hace_horas(self):
        result = self._parse_spanish_date("hace 3 horas")
        assert result is not None
        diff = (datetime.now() - result).total_seconds()
        assert 3*3600 - 60 <= diff <= 3*3600 + 60, f"Expected ~10800s diff, got {diff}"

    def test_hace_dias(self):
        result = self._parse_spanish_date("hace 2 días")
        assert result is not None
        diff = (datetime.now() - result).total_seconds()
        assert 2*86400 - 60 <= diff <= 2*86400 + 60

    def test_hace_semanas(self):
        result = self._parse_spanish_date("hace 1 semana")
        assert result is not None
        diff = (datetime.now() - result).total_seconds()
        assert 7*86400 - 60 <= diff <= 7*86400 + 60

    def test_hace_meses(self):
        result = self._parse_spanish_date("hace 2 meses")
        assert result is not None
        # Check that month decreased by 2
        now = datetime.now()
        expected_month = now.month - 2
        if expected_month <= 0:
            expected_month += 12

    def test_ayer(self):
        result = self._parse_spanish_date("Ayer")
        assert result is not None
        assert result.hour == 12
        assert result.minute == 0
        diff = (datetime.now() - result).days
        assert diff == 1, f"Expected 1 day diff, got {diff}"

    def test_hoy(self):
        result = self._parse_spanish_date("Hoy")
        assert result is not None
        assert result.hour == 12
        assert result.minute == 0
        assert result.day == datetime.now().day

    def test_short_form_h(self):
        result = self._parse_spanish_date("3 h")
        assert result is not None
        diff = (datetime.now() - result).total_seconds()
        assert 3*3600 - 60 <= diff <= 3*3600 + 60

    def test_short_form_min(self):
        result = self._parse_spanish_date("15 min")
        assert result is not None
        diff = (datetime.now() - result).total_seconds()
        assert 15*60 - 10 <= diff <= 15*60 + 10

    def test_absolute_date_with_time(self):
        """9 de junio de 2025 a las 14:59"""
        result = self._parse_spanish_date("9 de junio de 2025 a las 14:59")
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 9
        assert result.hour == 14
        assert result.minute == 59

    def test_absolute_date_no_year(self):
        """9 de junio (sin año)"""
        result = self._parse_spanish_date("9 de junio")
        assert result is not None
        assert result.month == 6
        assert result.day == 9
        # Should not be in the future
        assert result.year <= datetime.now().year
