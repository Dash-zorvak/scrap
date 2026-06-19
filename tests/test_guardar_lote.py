"""Tests for Fase 4: guardar_lote, ID generation, TikTok writer, FB writer."""
import os
import sqlite3
import tempfile

import pytest

from dashboard._generar_id import generar_id_post, generar_id_comentario, _base_para_hash
from dashboard.escritura_tiktok import (
    insertar_video,
    insertar_comentario_tiktok,
    obtener_ids_videos,
    _ensure_tiktok_schema,
)
from src.storage.db import LocalStorage


# ── Helpers ──

_FB_SAMPLE = {
    "plataforma": "facebook",
    "page_name": "Alcaldía de Santa Ana",
    "message": "Texto del post de prueba",
    "created_time": "2026-05-12T00:00:00",
    "likes_count": 10,
    "loves_count": 5,
    "cares_count": 0,
    "hahas_count": 1,
    "sads_count": 0,
    "wows_count": 2,
    "angrys_count": 0,
    "comments_count": 2,
    "shares_count": 3,
    "views_count": 100,
    "post_url": "https://facebook.com/testpost",
    "comentarios": [
        {"texto": "Primer comentario", "autor": "User1"},
        {"texto": "Segundo comentario", "autor": "User2"},
    ],
    "muestra_suficiente": True,
}

_TK_SAMPLE = {
    "plataforma": "tiktok",
    "account_id": 1,
    "description": "Video de prueba TikTok",
    "created_at": "2026-05-12T00:00:00",
    "views": 500,
    "likes": 50,
    "favorites_count": 10,
    "shares": 5,
    "comments_count": 2,
    "comentarios": [
        {"texto": "Comentario TK 1"},
        {"texto": "Comentario TK 2"},
    ],
    "muestra_suficiente": True,
}


# ── Tests: ID generation ──


class TestGenerarIdPost:
    def test_generates_man_format(self):
        pid = generar_id_post("https://example.com/post", set())
        assert pid.startswith("MAN_")
        assert len(pid) == len("MAN_0001_") + 10

    def test_reuses_existing_id_for_same_hash(self):
        pid = generar_id_post("https://example.com/post", set())
        ids = {pid}
        pid2 = generar_id_post("https://example.com/post", ids)
        assert pid2 == pid

    def test_increments_correlativo(self):
        ids = {"MAN_0001_aaaa", "MAN_0005_bbbb", "OTHER_xyz"}
        pid = generar_id_post("https://example.com/new", ids)
        assert pid.startswith("MAN_0006_")

    def test_different_content_different_id(self):
        pid1 = generar_id_post("url_a", set())
        pid2 = generar_id_post("url_b", set())
        assert pid1 != pid2

    def test_same_content_same_id(self):
        ids = set()
        pid1 = generar_id_post("same_url", ids)
        ids.add(pid1)
        pid2 = generar_id_post("same_url", ids)
        assert pid1 == pid2


class TestBaseParaHash:
    def test_uses_post_url_when_present(self):
        datos = {"post_url": "https://fb.com/123", "plataforma": "facebook"}
        assert _base_para_hash(datos) == "https://fb.com/123"

    def test_fallback_fb(self):
        datos = {
            "plataforma": "facebook",
            "page_name": "Pagina",
            "created_time": "2026-01-01",
            "message": "Mensaje largo " * 50,
        }
        base = _base_para_hash(datos)
        assert "Pagina|2026-01-01|" in base
        assert len(base) < 300

    def test_fallback_tiktok(self):
        datos = {
            "plataforma": "tiktok",
            "account_id": 1,
            "created_at": "2026-01-01",
            "description": "Descripción",
        }
        base = _base_para_hash(datos)
        assert "1|2026-01-01|Descripción" in base


class TestGenerarIdComentario:
    def test_format(self):
        cid = generar_id_comentario("MAN_0001_abc123def0", "Hola mundo", 0)
        assert cid.startswith("MAN_0001_abc123def0_c000_")
        assert len(cid.split("_")[-1]) == 8

    def test_different_text_different_id(self):
        cid1 = generar_id_comentario("MAN_0001_aaaa", "Hola", 0)
        cid2 = generar_id_comentario("MAN_0001_aaaa", "Mundo", 0)
        assert cid1 != cid2


# ── Tests: TikTok writer ──


class TestEscrituraTikTok:
    @pytest.fixture(autouse=True)
    def _temp_db(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = tmp.name
        tmp.close()
        yield
        os.unlink(self.db_path)

    def conn(self):
        return sqlite3.connect(self.db_path)

    def test_insertar_video_creates_tabla(self):
        conn = self.conn()
        insertar_video(conn, _TK_SAMPLE, "MAN_0001_abc123def0")
        rows = conn.execute("SELECT id, account_id, description FROM videos").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "MAN_0001_abc123def0"
        assert rows[0][1] == 1
        assert rows[0][2] == "Video de prueba TikTok"
        conn.close()

    def test_insertar_comentario(self):
        conn = self.conn()
        insertar_video(conn, _TK_SAMPLE, "VID01")
        insertar_comentario_tiktok(conn, "VID01_c000_hash", "VID01", "Comentario")
        rows = conn.execute("SELECT id, video_id, text FROM comments").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "VID01_c000_hash"
        conn.close()

    def test_obtener_ids_videos(self):
        conn = self.conn()
        insertar_video(conn, _TK_SAMPLE, "VID01")
        insertar_video(conn, _TK_SAMPLE, "VID02")
        ids = obtener_ids_videos(conn)
        assert ids == {"VID01", "VID02"}
        conn.close()

    def test_idempotencia_video(self):
        conn = self.conn()
        insertar_video(conn, _TK_SAMPLE, "VID01")
        insertar_video(conn, _TK_SAMPLE, "VID01")
        rows = conn.execute("SELECT COUNT(*) FROM videos").fetchall()
        assert rows[0][0] == 1
        conn.close()

    def test_ensure_schema_no_error_existing(self):
        conn = self.conn()
        conn.execute("CREATE TABLE videos (id TEXT PRIMARY KEY)")
        _ensure_tiktok_schema(conn)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(videos)").fetchall()]
        assert cols == ["id"]
        conn.close()


# ── Tests: Facebook writer via LocalStorage ──


class TestEscrituraFacebook:
    @pytest.fixture(autouse=True)
    def _temp_store(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = tmp.name
        tmp.close()
        self.store = LocalStorage(db_path=self.db_path)
        yield
        os.unlink(self.db_path)

    def _insert_post(self, post_id: str, datos: dict | None = None):
        d = dict(datos or _FB_SAMPLE)
        from dashboard.guardar_lote import _fb_post_insert_dict
        p = _fb_post_insert_dict(d, post_id)
        self.store.insert_fb_post(p)

    def test_insert_fb_post(self):
        self._insert_post("MAN_0001_abc123def0")
        ids = self.store.get_all_ids("fb_posts", "post_id")
        assert "MAN_0001_abc123def0" in ids

    def test_insert_fb_comment(self):
        from dashboard.guardar_lote import _fb_comment_insert_dict
        c = _fb_comment_insert_dict(
            {"texto": "Hola", "autor": "User1"},
            "MAN_0001_abc123def0_c000_hash",
            "MAN_0001_abc123def0",
        )
        self.store.insert_fb_comment(c)
        ids = self.store.get_all_ids("fb_comments", "comment_id")
        assert "MAN_0001_abc123def0_c000_hash" in ids

    def test_source_is_manual(self):
        self._insert_post("MAN_0002_hash")
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT source FROM fb_posts WHERE post_id=?",
                           ("MAN_0002_hash",)).fetchone()
        assert row[0] == "manual"
        conn.close()

    def test_idempotencia_fb(self):
        self._insert_post("MAN_0003_hash")
        self._insert_post("MAN_0003_hash")
        conn = sqlite3.connect(self.db_path)
        cnt = conn.execute("SELECT COUNT(*) FROM fb_posts WHERE post_id=?",
                           ("MAN_0003_hash",)).fetchone()[0]
        assert cnt == 1
        conn.close()


# ── Tests: guardar_lote integration ──


class TestGuardarLote:
    @pytest.fixture(autouse=True)
    def _temp_dbs(self, monkeypatch):
        self.fb_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.fb_tmp.close()
        self.tk_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tk_tmp.close()
        self.ext_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.ext_tmp.close()
        import dashboard.config as cfg
        monkeypatch.setattr(cfg, "FACEBOOK_DB", self.fb_tmp.name)
        monkeypatch.setattr(cfg, "TIKTOK_DB", self.tk_tmp.name)
        monkeypatch.setattr(cfg, "EXTERNOS_DB", self.ext_tmp.name)
        yield
        os.unlink(self.fb_tmp.name)
        os.unlink(self.tk_tmp.name)
        os.unlink(self.ext_tmp.name)

    def _item_revisado(self, datos: dict) -> dict:
        return {
            "id_temporal": "test-001",
            "estado": "revisado",
            "datos_revisados": datos,
        }

    def test_guardar_lote_facebook(self):
        from dashboard.guardar_lote import guardar_lote
        lote = [self._item_revisado(_FB_SAMPLE)]
        res = guardar_lote(lote)
        assert res["fb_posts"] == 1
        assert res["fb_comments"] == 2
        assert res["tk_videos"] == 0
        assert res["errores"] == []

        conn = sqlite3.connect(self.fb_tmp.name)
        row = conn.execute("SELECT source FROM fb_posts").fetchone()
        assert row[0] == "manual"
        cnt = conn.execute("SELECT COUNT(*) FROM fb_comments").fetchone()[0]
        assert cnt == 2
        conn.close()

    def test_guardar_lote_tiktok(self):
        from dashboard.guardar_lote import guardar_lote
        lote = [self._item_revisado(_TK_SAMPLE)]
        res = guardar_lote(lote)
        assert res["tk_videos"] == 1
        assert res["tk_comments"] == 2
        assert res["fb_posts"] == 0
        assert res["errores"] == []

        conn = sqlite3.connect(self.tk_tmp.name)
        row = conn.execute("SELECT account_id FROM videos").fetchone()
        assert row[0] == 1
        cnt = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        assert cnt == 2
        conn.close()

    def test_guardar_lote_mixto(self):
        from dashboard.guardar_lote import guardar_lote
        lote = [
            self._item_revisado(_FB_SAMPLE),
            self._item_revisado(_TK_SAMPLE),
        ]
        res = guardar_lote(lote)
        assert res["fb_posts"] == 1
        assert res["fb_comments"] == 2
        assert res["tk_videos"] == 1
        assert res["tk_comments"] == 2
        assert res["errores"] == []

    def test_idempotencia(self):
        from dashboard.guardar_lote import guardar_lote
        lote1 = [self._item_revisado(_FB_SAMPLE)]
        guardar_lote(lote1)
        # second pass with fresh item: same content, same ID → upsert
        lote2 = [self._item_revisado(_FB_SAMPLE)]
        res = guardar_lote(lote2)
        assert res["fb_posts"] == 1
        conn = sqlite3.connect(self.fb_tmp.name)
        cnt = conn.execute("SELECT COUNT(*) FROM fb_posts").fetchone()[0]
        assert cnt == 1
        conn.close()

    def test_id_estable(self):
        from dashboard.guardar_lote import guardar_lote
        fb1 = dict(_FB_SAMPLE, post_url="https://fb.com/stable")
        fb2 = dict(_FB_SAMPLE, post_url="https://fb.com/stable")
        lote = [self._item_revisado(fb1), self._item_revisado(fb2)]
        for item in lote:
            item["id_temporal"] = "id-" + str(id(item))
        res = guardar_lote(lote)
        # dos items con mismo contenido → mismo post_id, upsert → 1 fila
        conn = sqlite3.connect(self.fb_tmp.name)
        cnt = conn.execute("SELECT COUNT(*) FROM fb_posts").fetchone()[0]
        assert cnt == 1
        conn.close()

    def test_un_error_no_aborta(self):
        from dashboard.guardar_lote import guardar_lote
        item_bueno = self._item_revisado(_FB_SAMPLE)
        item_malo = {
            "id_temporal": "bad",
            "estado": "revisado",
            "datos_revisados": {"plataforma": "unknown"},
        }
        res = guardar_lote([item_bueno, item_malo])
        assert res["fb_posts"] == 1
        assert len(res["errores"]) >= 1

    def test_no_procesa_no_revisados(self):
        from dashboard.guardar_lote import guardar_lote
        lote = [{"id_temporal": "x", "estado": "pendiente"}]
        res = guardar_lote(lote)
        assert res["fb_posts"] == 0
        assert res["tk_videos"] == 0

    def test_comments_count_fallback(self):
        from dashboard.guardar_lote import guardar_lote
        datos = dict(_FB_SAMPLE)
        datos["comments_count"] = 0
        lote = [self._item_revisado(datos)]
        res = guardar_lote(lote)
        assert res["fb_comments"] == 2

    def test_nones_coalesced_to_zero(self):
        from dashboard.guardar_lote import guardar_lote
        datos = dict(_FB_SAMPLE)
        datos["likes_count"] = None
        datos["shares_count"] = None
        lote = [self._item_revisado(datos)]
        res = guardar_lote(lote)
        assert res["fb_posts"] == 1
        conn = sqlite3.connect(self.fb_tmp.name)
        row = conn.execute("SELECT likes_count, shares_count FROM fb_posts").fetchone()
        assert row[0] == 0
        assert row[1] == 0
        conn.close()
