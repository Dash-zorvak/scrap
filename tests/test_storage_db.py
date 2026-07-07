"""Tests for src/storage/db.py — LocalStorage inserts with None message."""
import os
import sqlite3
import tempfile

import pytest

from src.storage.db import LocalStorage


class TestLocalStorageMessageNone:
    @pytest.fixture(autouse=True)
    def _temp_store(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = tmp.name
        tmp.close()
        self.store = LocalStorage(db_path=self.db_path)
        yield
        os.unlink(self.db_path)

    def test_insert_fb_post_message_none(self):
        post = {
            "post_id": "none_msg_post_001",
            "page_id": "test",
            "page_name": "Test",
            "message": None,
            "created_time": None,
        }
        result = self.store.insert_fb_post(post)
        assert result is True

        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT message FROM fb_posts WHERE post_id = ?",
            ("none_msg_post_001",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == ""

    def test_insert_fb_comment_message_none(self):
        comment = {
            "comment_id": "none_msg_comment_001",
            "post_id": "none_msg_post_001",
            "message": None,
            "author_name": "User",
            "created_time": None,
        }
        result = self.store.insert_fb_comment(comment)
        assert result is True

        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT message FROM fb_comments WHERE comment_id = ?",
            ("none_msg_comment_001",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == ""

    def test_insert_fb_post_message_normal(self):
        post = {
            "post_id": "normal_msg_post_001",
            "page_id": "test",
            "page_name": "Test",
            "message": "Texto normal de prueba",
            "created_time": None,
        }
        result = self.store.insert_fb_post(post)
        assert result is True

        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT message FROM fb_posts WHERE post_id = ?",
            ("normal_msg_post_001",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "Texto normal de prueba"

    def test_insert_fb_comment_message_truncated(self):
        long_msg = "x" * 10000
        comment = {
            "comment_id": "trunc_comment_001",
            "post_id": "trunc_post_001",
            "message": long_msg,
            "author_name": "User",
            "created_time": None,
        }
        result = self.store.insert_fb_comment(comment)
        assert result is True

        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT message FROM fb_comments WHERE comment_id = ?",
            ("trunc_comment_001",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert len(row[0]) == 5000
