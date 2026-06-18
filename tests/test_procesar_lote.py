"""Tests for Fase 5: procesar_pipeline orchestrator."""
import os
import sqlite3
import shutil

import pytest

from dashboard import config as _cfg
from dashboard.procesar_lote import procesar_pipeline


@pytest.fixture
def temp_dbs():
    """Create seed data in actual test DB paths (facebook_test.db / tiktok_test.db).

    These paths are what the modules read when modo_prueba=True.
    Conftest does NOT block *_test.db paths, only production *.db.
    """
    fb_db = os.path.join(_cfg.BASE_DIR, "data", "facebook_test.db")
    tk_db = os.path.join(_cfg.BASE_DIR, "data", "tiktok_test.db")

    # Remove any leftover from previous runs
    for p in [fb_db, tk_db]:
        if os.path.exists(p):
            os.remove(p)

    conn = sqlite3.connect(fb_db)
    conn.execute("""CREATE TABLE IF NOT EXISTS fb_posts (
        post_id TEXT PRIMARY KEY, page_name TEXT, created_time TEXT,
        message TEXT, likes_count INTEGER, loves_count INTEGER, cares_count INTEGER,
        hahas_count INTEGER, wows_count INTEGER, sads_count INTEGER,
        angrys_count INTEGER, comments_count INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS fb_comments (
        comment_id TEXT PRIMARY KEY, post_id TEXT, message TEXT
    )""")
    # Columnas: post_id, page_name, created_time, message, likes, loves, cares, hahas,
    #           wows, sads, angrys, comments
    conn.execute("INSERT INTO fb_posts VALUES "
                 "('fb_1', 'Alcaldía de Santa Ana', '2026-05-01T00:00:00', "
                 "'Texto del post', 50, 10, 0, 5, 3, 2, 4, 8)")
    conn.execute("INSERT INTO fb_posts VALUES "
                 "('fb_2', 'Jose Chicas', '2026-05-05T00:00:00', "
                 "'Otro post', 30, 5, 0, 2, 1, 1, 1, 3)")
    conn.execute("INSERT INTO fb_comments VALUES "
                 "('c1', 'fb_1', 'excelente trabajo gracias')")
    conn.execute("INSERT INTO fb_comments VALUES "
                 "('c2', 'fb_1', 'pesimo corrupto horrible')")
    conn.execute("INSERT INTO fb_comments VALUES "
                 "('c3', 'fb_2', 'buen contenido')")
    conn.commit()
    conn.close()

    conn = sqlite3.connect(tk_db)
    conn.execute("""CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY, account_id INTEGER, description TEXT,
        created_at TEXT, views INTEGER, likes INTEGER, shares INTEGER,
        favorites_count INTEGER, comments_count INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS comments (
        id TEXT PRIMARY KEY, video_id TEXT, text TEXT
    )""")
    conn.execute("INSERT INTO videos VALUES "
                 "('tk_1', 1, 'Video TikTok de prueba', '2026-05-02T00:00:00', "
                 "500, 100, 20, 10, 5)")
    conn.execute("INSERT INTO videos VALUES "
                 "('tk_2', 3, 'Otro video', '2026-05-06T00:00:00', "
                 "200, 50, 10, 5, 2)")
    conn.execute("INSERT INTO comments VALUES "
                 "('tc1', 'tk_1', 'me encanto este video')")
    conn.execute("INSERT INTO comments VALUES "
                 "('tc2', 'tk_1', 'que malo horrible')")
    conn.commit()
    conn.close()

    yield fb_db, tk_db

    for p in [fb_db, tk_db]:
        if os.path.exists(p):
            os.remove(p)
    # Also remove any aggregate tables written during test
    aux_tables = [
        "fb_sentimiento", "post_categorias", "fb_engagement", "series_facebook",
        "tiktok_sentimiento", "tiktok_engagement", "series_tiktok",
    ]
    for p in [fb_db, tk_db]:
        if os.path.exists(p):
            try:
                conn = sqlite3.connect(p)
                for tbl in aux_tables:
                    conn.execute(f"DROP TABLE IF EXISTS {tbl}")
                conn.commit()
                conn.close()
            except Exception:
                pass
        if os.path.exists(p):
            os.remove(p)


def _mock_heavy_modules(monkeypatch):
    """Mock BERT, Gemini, sentence-transformers, and KMeans so CI stays fast."""
    import modulo1_categorias as _m1

    class MockKMeans:
        def __init__(self, **kwargs):
            pass
        def fit_predict(self, X):
            import numpy as np
            return np.zeros(len(X), dtype=int)
        @property
        def cluster_centers_(self):
            import numpy as np
            return np.zeros((8, 10))
        def transform(self, X):
            import numpy as np
            return np.zeros((len(X), 8))

    monkeypatch.setattr(_m1, "KMeans", MockKMeans)

    def mock_embeddings(textos, batch_size=64):
        import numpy as np
        return np.random.rand(len(textos), 10)

    monkeypatch.setattr(_m1, "generar_embeddings", mock_embeddings)

    # Prevent BERT load thread from importing pysentimiento/torch
    # Patch directly in sys.modules so the background thread's LOAD_GLOBAL
    # picks up the mock (the thread's globals = sentimiento_engine.__dict__).
    import sys
    _sent_mod = sys.modules.get("sentimiento_engine")
    assert _sent_mod is not None, (
        "sentimiento_engine not imported yet — "
        "call _mock_heavy_modules after modules are loaded"
    )

    def mock_cargar_bert():
        raise RuntimeError("BERT disabled in tests")

    monkeypatch.setattr(_sent_mod, "_cargar_bert", mock_cargar_bert)

    # Prevent Gemini from trying API calls
    monkeypatch.setattr(_sent_mod, "_configurar_gemini", lambda: False)


class TestProcesarPipeline:
    def test_pipeline_completes_all_steps(self, temp_dbs, monkeypatch):
        _mock_heavy_modules(monkeypatch)
        fb_db, tk_db = temp_dbs

        result = procesar_pipeline(modo_prueba=True)

        assert len(result["pasos_ok"]) == 6
        assert "sentimiento_facebook" in result["pasos_ok"]
        assert "sentimiento_tiktok" in result["pasos_ok"]
        assert "categorias" in result["pasos_ok"]
        assert "engagement_facebook" in result["pasos_ok"]
        assert "engagement_tiktok" in result["pasos_ok"]
        assert "series" in result["pasos_ok"]
        assert result["errores"] == []
        assert result["motor_sentimiento"] == "reglas"

        conn = sqlite3.connect(fb_db)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        for tbl in ["fb_sentimiento", "post_categorias", "fb_engagement", "series_facebook"]:
            assert tbl in tables, f"Missing table: {tbl}"

        conn = sqlite3.connect(tk_db)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        for tbl in ["tiktok_sentimiento", "tiktok_engagement", "series_tiktok"]:
            assert tbl in tables, f"Missing table: {tbl}"

    def test_modo_prueba_flag(self, temp_dbs, monkeypatch):
        _mock_heavy_modules(monkeypatch)
        result = procesar_pipeline(modo_prueba=True)
        assert result["motor_sentimiento"] == "reglas"

    def test_error_isolation(self, temp_dbs, monkeypatch):
        _mock_heavy_modules(monkeypatch)

        def broken_sentiment(*args, **kwargs):
            raise RuntimeError("Simulated crash")

        monkeypatch.setattr(
            "dashboard.procesar_lote.analizar_sentimiento_facebook", broken_sentiment
        )

        result = procesar_pipeline(modo_prueba=True)

        assert "sentimiento_facebook" not in result["pasos_ok"]
        assert len(result["errores"]) >= 1
        assert any("sentimiento_facebook" in e for e in result["errores"])
        assert len(result["pasos_ok"]) >= 5

    def test_progress_callback(self, temp_dbs, monkeypatch):
        _mock_heavy_modules(monkeypatch)
        steps = []

        def cb(paso, total, etiqueta):
            steps.append((paso, total, etiqueta))

        procesar_pipeline(modo_prueba=True, progreso_cb=cb)
        assert len(steps) == 7  # 6 steps + "Pipeline completado"
        assert steps[-1] == (6, 6, "Pipeline completado")
