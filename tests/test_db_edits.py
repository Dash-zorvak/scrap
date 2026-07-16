"""Tests para TikTokStorage/ExternosStorage con audit_log (Punto 6)."""
import json
import os
import sqlite3
import tempfile

import pytest


def _crear_bd_temp(schema_sql):
    """Crea una BD temporal con el schema dado."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(schema_sql)
    conn.close()
    return path


_TIKTOK_SCHEMA = """
CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    account_id INTEGER,
    description TEXT,
    created_at TEXT,
    views INTEGER,
    likes INTEGER,
    shares INTEGER,
    favorites_count INTEGER,
    comments_count INTEGER,
    post_url TEXT
);
CREATE TABLE comments (
    id TEXT PRIMARY KEY,
    video_id TEXT,
    username TEXT,
    text TEXT,
    likes INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    created_at TEXT
);
"""

_EXTERNOS_SCHEMA = """
CREATE TABLE external_posts (
    post_id TEXT PRIMARY KEY,
    page_name TEXT,
    page_url TEXT,
    message TEXT,
    created_time DATETIME,
    total_reactions INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    post_url TEXT,
    source TEXT DEFAULT 'manual_externo'
);
CREATE TABLE external_comments (
    comment_id TEXT PRIMARY KEY,
    post_id TEXT,
    message TEXT,
    author_name TEXT DEFAULT 'Anonymous',
    created_time DATETIME
);
"""


class TestTikTokStorage:
    def test_update_video_creates_audit_log(self):
        from src.storage.db import TikTokStorage
        db = _crear_bd_temp(_TIKTOK_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO videos (id, description, views) VALUES ('v1', 'test', 100)")
        conn.commit()
        conn.close()

        store = TikTokStorage(db_path=db)
        try:
            ok = store.update_video("v1", {"description": "updated"})
            assert ok is True

            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT description FROM videos WHERE id = 'v1'").fetchone()
            assert row["description"] == "updated"

            audit = conn.execute("SELECT * FROM audit_log WHERE registro_id = 'v1'").fetchall()
            assert len(audit) == 1
            assert audit[0]["accion"] == "update"
            assert audit[0]["tabla"] == "videos"
            conn.close()
        finally:
            store.close()

    def test_delete_video_creates_audit_log(self):
        from src.storage.db import TikTokStorage
        db = _crear_bd_temp(_TIKTOK_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO videos (id, description) VALUES ('v2', 'test2')")
        conn.execute("INSERT INTO comments (id, video_id, text) VALUES ('c1', 'v2', 'comment')")
        conn.commit()
        conn.close()

        store = TikTokStorage(db_path=db)
        try:
            ok = store.delete_video("v2")
            assert ok is True

            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            vid = conn.execute("SELECT * FROM videos WHERE id = 'v2'").fetchone()
            assert vid is None
            com = conn.execute("SELECT * FROM comments WHERE video_id = 'v2'").fetchone()
            assert com is None

            audit = conn.execute("SELECT * FROM audit_log WHERE registro_id = 'v2'").fetchall()
            assert len(audit) == 1
            assert audit[0]["accion"] == "delete"
            conn.close()
        finally:
            store.close()

    def test_invalid_value_raises_value_error(self):
        from src.storage.db import TikTokStorage
        db = _crear_bd_temp(_TIKTOK_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO videos (id, views) VALUES ('v3', 100)")
        conn.commit()
        conn.close()

        store = TikTokStorage(db_path=db)
        try:
            with pytest.raises(ValueError, match="entero"):
                store.update_video("v3", {"views": "not_a_number"})
        finally:
            store.close()

    def test_negative_value_raises_value_error(self):
        from src.storage.db import TikTokStorage
        db = _crear_bd_temp(_TIKTOK_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO videos (id, views) VALUES ('v4', 100)")
        conn.commit()
        conn.close()

        store = TikTokStorage(db_path=db)
        try:
            with pytest.raises(ValueError, match="negativo"):
                store.update_video("v4", {"views": -5})
        finally:
            store.close()


class TestExternosStorage:
    def test_update_post_creates_audit_log(self):
        from src.storage.db import ExternosStorage
        db = _crear_bd_temp(_EXTERNOS_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO external_posts (post_id, message) VALUES ('p1', 'test')")
        conn.commit()
        conn.close()

        store = ExternosStorage(db_path=db)
        try:
            ok = store.update_post("p1", {"message": "updated"})
            assert ok is True

            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT message FROM external_posts WHERE post_id = 'p1'").fetchone()
            assert row["message"] == "updated"

            audit = conn.execute("SELECT * FROM audit_log WHERE registro_id = 'p1'").fetchall()
            assert len(audit) == 1
            assert audit[0]["accion"] == "update"
            assert audit[0]["tabla"] == "external_posts"
            conn.close()
        finally:
            store.close()

    def test_delete_post_creates_audit_log(self):
        from src.storage.db import ExternosStorage
        db = _crear_bd_temp(_EXTERNOS_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO external_posts (post_id, message) VALUES ('p2', 'test2')")
        conn.execute("INSERT INTO external_comments (comment_id, post_id, message) VALUES ('ec1', 'p2', 'comment')")
        conn.commit()
        conn.close()

        store = ExternosStorage(db_path=db)
        try:
            ok = store.delete_post("p2")
            assert ok is True

            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            post = conn.execute("SELECT * FROM external_posts WHERE post_id = 'p2'").fetchone()
            assert post is None
            com = conn.execute("SELECT * FROM external_comments WHERE post_id = 'p2'").fetchone()
            assert com is None

            audit = conn.execute("SELECT * FROM audit_log WHERE registro_id = 'p2'").fetchall()
            assert len(audit) == 1
            assert audit[0]["accion"] == "delete"
            conn.close()
        finally:
            store.close()

    def test_invalid_integer_raises_value_error(self):
        from src.storage.db import ExternosStorage
        db = _crear_bd_temp(_EXTERNOS_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO external_posts (post_id, total_reactions) VALUES ('p3', 10)")
        conn.commit()
        conn.close()

        store = ExternosStorage(db_path=db)
        try:
            with pytest.raises(ValueError, match="entero"):
                store.update_post("p3", {"total_reactions": "bad"})
        finally:
            store.close()


class TestDbEditsIntegration:
    def test_update_video_tiktok_uses_storage(self):
        from dashboard.db_edits import update_video_tiktok
        db = _crear_bd_temp(_TIKTOK_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO videos (id, description) VALUES ('vt1', 'original')")
        conn.commit()
        conn.close()

        ok = update_video_tiktok("vt1", {"description": "via_db_edits"}, db_path=db)
        assert ok is True

        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT description FROM videos WHERE id = 'vt1'").fetchone()
        assert row["description"] == "via_db_edits"

        audit = conn.execute("SELECT * FROM audit_log WHERE registro_id = 'vt1'").fetchall()
        assert len(audit) == 1
        conn.close()

    def test_delete_video_tiktok_uses_storage(self):
        from dashboard.db_edits import delete_video_tiktok
        db = _crear_bd_temp(_TIKTOK_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO videos (id, description) VALUES ('vt2', 'to_delete')")
        conn.commit()
        conn.close()

        ok = delete_video_tiktok("vt2", db_path=db)
        assert ok is True

        conn = sqlite3.connect(db)
        vid = conn.execute("SELECT * FROM videos WHERE id = 'vt2'").fetchone()
        assert vid is None
        conn.close()

    def test_update_post_externo_uses_storage(self):
        from dashboard.db_edits import update_post_externo
        db = _crear_bd_temp(_EXTERNOS_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO external_posts (post_id, message) VALUES ('ep1', 'original')")
        conn.commit()
        conn.close()

        ok = update_post_externo("ep1", {"message": "via_db_edits"}, db_path=db)
        assert ok is True

        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT message FROM external_posts WHERE post_id = 'ep1'").fetchone()
        assert row["message"] == "via_db_edits"
        conn.close()

    def test_delete_post_externo_uses_storage(self):
        from dashboard.db_edits import delete_post_externo
        db = _crear_bd_temp(_EXTERNOS_SCHEMA)
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO external_posts (post_id, message) VALUES ('ep2', 'to_delete')")
        conn.commit()
        conn.close()

        ok = delete_post_externo("ep2", db_path=db)
        assert ok is True

        conn = sqlite3.connect(db)
        post = conn.execute("SELECT * FROM external_posts WHERE post_id = 'ep2'").fetchone()
        assert post is None
        conn.close()
