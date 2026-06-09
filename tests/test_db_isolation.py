"""Verify conftest isolation works — opening a real DB path MUST fail."""
import os
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_DB = str(REPO_ROOT / "data" / "facebook.db")


def test_guard_blocks_real_fb_db():
    """The conftest guard must prevent opening the real facebook.db."""
    with pytest.raises(Exception, match="BLOCKED"):
        sqlite3.connect(REAL_DB)


def test_guard_blocks_real_externos_db():
    """The conftest guard must prevent opening the real externos.db."""
    with pytest.raises(Exception, match="BLOCKED"):
        sqlite3.connect(str(REPO_ROOT / "data" / "externos.db"))


def test_guard_allows_memory():
    """In-memory databases must still work."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE t (x)")
    cur.execute("INSERT INTO t VALUES (1)")
    assert cur.execute("SELECT * FROM t").fetchone()[0] == 1
    conn.close()


def test_env_vars_redirect_to_temp():
    """Env vars set by conftest must point to temp, not production paths."""
    # These env vars are set in pytest_configure
    for var in ["EXTERNAL_DB_PATH", "EXTERNAL_DB", "FACEBOOK_DB", "EXTERNOS_DB"]:
        val = os.getenv(var)
        assert val is not None, f"{var} is not set"
        assert "pytest_db_" in val, f"{var}={val} does not look like a temp path"
        assert Path(val).parent.exists(), f"Parent dir of {var}={val} does not exist"
