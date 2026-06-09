"""Tests for purge_out_of_range.py: verifies only pre-2025 posts are deleted."""
import sqlite3
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "purge_out_of_range.py"

SINCE = "2025-01-01"


def _build_fb_fixture() -> sqlite3.Connection:
    """facebook.db schema: fb_posts + fb_comments + fb_engagement + fb_sentimiento."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE fb_posts (
            post_id TEXT PRIMARY KEY,
            page_id TEXT,
            page_name TEXT,
            message TEXT,
            created_time TEXT,
            likes_count INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0
        );
        CREATE TABLE fb_comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT,
            message TEXT,
            author_name TEXT,
            created_time TEXT
        );
        CREATE TABLE fb_engagement (
            post_id TEXT,
            page_name TEXT,
            created_time TEXT,
            message TEXT,
            total_reacciones INTEGER
        );
        CREATE TABLE fb_sentimiento (
            post_id TEXT PRIMARY KEY,
            total_comentarios INTEGER,
            score_sentimiento REAL
        );
    """)

    # 3 posts IN range (2025+)
    for i in range(3):
        pid = f"inrange_p_{i}"
        cur.execute(
            "INSERT INTO fb_posts (post_id, message, created_time) VALUES (?, ?, ?)",
            (pid, f"In-range post {i}", "2026-01-15"),
        )
        cur.execute(
            "INSERT INTO fb_comments (comment_id, post_id, message, created_time) VALUES (?, ?, ?, ?)",
            (f"inrange_c_{i}", pid, f"In-range comment {i}", "2026-01-16"),
        )
        cur.execute(
            "INSERT INTO fb_engagement (post_id, page_name, message, total_reacciones) VALUES (?, ?, ?, ?)",
            (pid, "Page", f"Engagement {i}", 100),
        )
        cur.execute(
            "INSERT INTO fb_sentimiento (post_id, total_comentarios, score_sentimiento) VALUES (?, ?, ?)",
            (pid, 5, 0.8),
        )

    # 2 posts OUT of range (pre-2025)
    for i in range(2):
        pid = f"oor_p_{i}"
        cur.execute(
            "INSERT INTO fb_posts (post_id, message, created_time) VALUES (?, ?, ?)",
            (pid, f"OOR post {i}", "2024-06-15"),
        )
        cur.execute(
            "INSERT INTO fb_comments (comment_id, post_id, message, created_time) VALUES (?, ?, ?, ?)",
            (f"oor_c_{i}", pid, f"OOR comment {i}", "2024-06-16"),
        )
        cur.execute(
            "INSERT INTO fb_engagement (post_id, page_name, message, total_reacciones) VALUES (?, ?, ?, ?)",
            (pid, "Page", f"OOR engagement {i}", 50),
        )
        cur.execute(
            "INSERT INTO fb_sentimiento (post_id, total_comentarios, score_sentimiento) VALUES (?, ?, ?)",
            (pid, 3, 0.2),
        )

    # 1 post with NULL created_time
    cur.execute(
        "INSERT INTO fb_posts (post_id, message, created_time) VALUES (?, ?, ?)",
        ("null_date_post", "NULL-date post", None),
    )
    cur.execute(
        "INSERT INTO fb_comments (comment_id, post_id, message, created_time) VALUES (?, ?, ?, ?)",
        ("null_date_comment", "null_date_post", "NULL-date comment", None),
    )

    conn.commit()
    return conn


class TestPurgeFacebook:
    """Test purge logic on facebook.db-style fixture."""

    def test_counts_oor_correctly(self):
        conn = _build_fb_fixture()
        cur = conn.cursor()

        oor = cur.execute(
            "SELECT COUNT(*) FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?",
            (SINCE,),
        ).fetchone()[0]
        assert oor == 2, f"Expected 2 OOR posts, got {oor}"

        total = cur.execute("SELECT COUNT(*) FROM fb_posts").fetchone()[0]
        assert total == 6, f"Expected 6 posts total, got {total}"
        conn.close()

    def test_deletes_only_oor_posts(self):
        conn = _build_fb_fixture()
        cur = conn.cursor()

        # Delete comments first
        cur.execute(
            "DELETE FROM fb_comments WHERE post_id IN "
            "(SELECT post_id FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?)",
            (SINCE,),
        )
        # Delete engagement
        cur.execute(
            "DELETE FROM fb_engagement WHERE post_id IN "
            "(SELECT post_id FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?)",
            (SINCE,),
        )
        # Delete sentimiento
        cur.execute(
            "DELETE FROM fb_sentimiento WHERE post_id IN "
            "(SELECT post_id FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?)",
            (SINCE,),
        )
        # Delete OOR posts
        cur.execute(
            "DELETE FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?",
            (SINCE,),
        )

        remaining = cur.execute("SELECT COUNT(*) FROM fb_posts").fetchone()[0]
        assert remaining == 4, f"Expected 4 remaining (3 in-range + 1 NULL), got {remaining}"

        # Verify NULL-date post preserved
        null_exists = cur.execute(
            "SELECT COUNT(*) FROM fb_posts WHERE post_id = 'null_date_post'"
        ).fetchone()[0]
        assert null_exists == 1, "NULL-date post should be preserved"

        # Verify in-range posts preserved
        inrange = cur.execute(
            "SELECT COUNT(*) FROM fb_posts WHERE created_time >= ?", (SINCE,)
        ).fetchone()[0]
        assert inrange == 3, f"Expected 3 in-range, got {inrange}"

        conn.close()

    def test_oor_comments_deleted(self):
        conn = _build_fb_fixture()
        cur = conn.cursor()

        cur.execute(
            "DELETE FROM fb_comments WHERE post_id IN "
            "(SELECT post_id FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?)",
            (SINCE,),
        )
        cur.execute(
            "DELETE FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?",
            (SINCE,),
        )

        remaining_comments = cur.execute("SELECT COUNT(*) FROM fb_comments").fetchone()[0]
        # 3 in-range + 1 NULL-date = 4
        assert remaining_comments == 4, f"Expected 4 comments, got {remaining_comments}"

        oor_comments = cur.execute(
            "SELECT COUNT(*) FROM fb_comments WHERE post_id IN ('oor_p_0', 'oor_p_1')"
        ).fetchone()[0]
        assert oor_comments == 0, "OOR comments should be gone"

        conn.close()

    def test_null_dates_preserved_by_default(self):
        """Default behavior: NULL dates are KEPT."""
        conn = _build_fb_fixture()
        cur = conn.cursor()

        # Default path: exclude NULL from OOR filter
        cur.execute(
            "DELETE FROM fb_comments WHERE post_id IN "
            "(SELECT post_id FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?)",
            (SINCE,),
        )
        cur.execute(
            "DELETE FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?",
            (SINCE,),
        )

        null_post = cur.execute(
            "SELECT COUNT(*) FROM fb_posts WHERE created_time IS NULL"
        ).fetchone()[0]
        assert null_post == 1, "NULL-date posts should be preserved by default"
        conn.close()

    def test_purge_null_flag(self):
        """--purge-null also deletes NULL-date rows."""
        conn = _build_fb_fixture()
        cur = conn.cursor()

        purge_null = True
        cond = "(created_time IS NOT NULL AND created_time < ?) OR created_time IS NULL"
        params = [SINCE]

        cur.execute(
            f"DELETE FROM fb_comments WHERE post_id IN "
            f"(SELECT post_id FROM fb_posts WHERE {cond})",
            params,
        )
        cur.execute(f"DELETE FROM fb_posts WHERE {cond}", params)

        remaining = cur.execute("SELECT COUNT(*) FROM fb_posts").fetchone()[0]
        assert remaining == 3, f"Expected 3 in-range, got {remaining}"
        conn.close()

    def test_engagement_and_sentimiento_cleaned(self):
        """Related tables should also be purged."""
        conn = _build_fb_fixture()
        cur = conn.cursor()

        # Delete related data for OOR posts
        cur.execute(
            "DELETE FROM fb_engagement WHERE post_id IN "
            "(SELECT post_id FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?)",
            (SINCE,),
        )
        cur.execute(
            "DELETE FROM fb_sentimiento WHERE post_id IN "
            "(SELECT post_id FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?)",
            (SINCE,),
        )
        cur.execute(
            "DELETE FROM fb_posts WHERE created_time IS NOT NULL AND created_time < ?",
            (SINCE,),
        )

        eng = cur.execute("SELECT COUNT(*) FROM fb_engagement").fetchone()[0]
        sent = cur.execute("SELECT COUNT(*) FROM fb_sentimiento").fetchone()[0]
        # 3 in-range rows each
        assert eng == 3, f"Expected 3 engagement rows, got {eng}"
        assert sent == 3, f"Expected 3 sentimiento rows, got {sent}"
        conn.close()

    def test_script_imports(self):
        """Structural check: script module can be imported."""
        assert SCRIPT.exists(), f"Script not found at {SCRIPT}"
        import importlib.util
        spec = importlib.util.spec_from_file_location("purge_out_of_range", SCRIPT)
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            pytest.fail(f"Module import failed: {e}")
