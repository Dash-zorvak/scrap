"""Test isolation: redirect all DB paths to temp files & block real DB access.

All env vars are set in pytest_configure (before any test module is imported)
so that module-level path constants (e.g. EXTERNAL_DB_PATH in deep_scraper.py)
resolve to temp directories, not production data/.
"""
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Production DB paths that tests MUST NOT touch ──
_REAL_DB_PATHS = {
    str(_REPO_ROOT / "data" / "externos.db"),
    str(_REPO_ROOT / "data" / "facebook.db"),
    str(_REPO_ROOT / "data" / "tiktok.db"),
    str(_REPO_ROOT / "data" / "analytics_cache.db"),
    str(_REPO_ROOT / "data" / "backup.db"),
    str(_REPO_ROOT / "data" / "pipeline.db"),
}

# ── Env vars → module path constants ──
# Key = env var name, Value = filename for the temp file
_DB_ENV_VARS = {
    "EXTERNAL_DB_PATH": "externos.db",   # src/fb_scraper/deep_scraper.py
    "EXTERNAL_DB": "externos.db",        # scripts/clean_simulated.py, dedupe_existing.py
    "FACEBOOK_DB": "facebook.db",        # src/storage/db.py, scripts/purge_out_of_range.py
    "EXTERNOS_DB": "externos.db",        # dashboard/modulo5_externos.py
}

_temp_db_dir: str | None = None


def pytest_configure(config):
    """Run BEFORE any test module is imported — sets env vars to temp paths."""
    global _temp_db_dir
    _temp_db_dir = tempfile.mkdtemp(prefix="pytest_db_")
    for env_var, filename in _DB_ENV_VARS.items():
        os.environ[env_var] = os.path.join(_temp_db_dir, filename)


def pytest_unconfigure(config):
    """Cleanup after all tests."""
    global _temp_db_dir
    if _temp_db_dir:
        shutil.rmtree(_temp_db_dir, ignore_errors=True)
        for env_var in _DB_ENV_VARS:
            os.environ.pop(env_var, None)
        _temp_db_dir = None


@pytest.fixture(autouse=True)
def _guard_real_db(monkeypatch):
    """Block any test from opening a real production database via sqlite3.connect.

    Allows :memory: and any path NOT in _REAL_DB_PATHS.
    """
    original_connect = sqlite3.connect

    def guarded_connect(database, *args, **kwargs):
        if database and database != ":memory:":
            resolved = str(Path(database).resolve())
            if resolved in _REAL_DB_PATHS:
                raise RuntimeError(
                    f"BLOCKED: test tried to open real production DB:\n"
                    f"  {resolved}\n"
                    f"Use env vars ({', '.join(_DB_ENV_VARS)}) to redirect."
                )
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr("sqlite3.connect", guarded_connect)
