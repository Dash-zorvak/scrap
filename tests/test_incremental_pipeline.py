"""Regresion de incrementalidad del pipeline (poda + cache de embeddings).

Verifica la causa raiz de la lentitud al procesar un lote: antes el pipeline
recomputaba TODA la base en cada ejecucion (if_exists="replace") y regeneraba
TODOS los embeddings. Tras el rediseno:

  - sentimiento (FB/TikTok) y engagement (FB/TikTok) solo procesan items NUEVOS
    y hacen append, no replace.
  - modulo1 cachea embeddings por (item_id, plataforma) y solo invoca
    generar_embeddings sobre items nuevos o con texto cambiado.

El test corre el pipeline dos veces: la segunda corrida (con 1 post y 1 video
nuevos) NO debe recomputar lo ya procesado.
"""
import os
import sqlite3
import tempfile

import numpy as np
import pytest

from dashboard.procesar_lote import procesar_pipeline
import dashboard.procesar_lote as _pl


class _Rec:
    """Registra cuantos items pasan por embeddings y por clasificacion."""
    def __init__(self):
        self.embedding_calls = []   # listas de textos por llamada
        self.clasificar_calls = []  # listas de textos por llamada

    def reset(self):
        self.embedding_calls = []
        self.clasificar_calls = []

    @property
    def n_embeddings(self):
        return sum(len(c) for c in self.embedding_calls)

    @property
    def n_clasificados(self):
        return sum(len(c) for c in self.clasificar_calls)


class _MockKMeans:
    def __init__(self, **kwargs):
        self.n_clusters = kwargs.get("n_clusters", 1)
    def fit_predict(self, X):
        return np.zeros(len(X), dtype=int)
    @property
    def cluster_centers_(self):
        return np.zeros((8, 10))
    def transform(self, X):
        return np.zeros((len(X), 8))


def _count(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except Exception:
        return None
    finally:
        conn.close()


def _crear_dbs():
    fb_fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fb_fd.close()
    tk_fd = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tk_fd.close()
    fb_db, tk_db = fb_fd.name, tk_fd.name

    conn = sqlite3.connect(fb_db)
    conn.execute("""CREATE TABLE fb_posts (
        post_id TEXT PRIMARY KEY, page_name TEXT, created_time TEXT,
        message TEXT, likes_count INTEGER, loves_count INTEGER, cares_count INTEGER,
        hahas_count INTEGER, wows_count INTEGER, sads_count INTEGER,
        angrys_count INTEGER, comments_count INTEGER
    )""")
    conn.execute("""CREATE TABLE fb_comments (
        comment_id TEXT PRIMARY KEY, post_id TEXT, message TEXT
    )""")
    conn.commit()
    conn.close()

    conn = sqlite3.connect(tk_db)
    conn.execute("""CREATE TABLE videos (
        id TEXT PRIMARY KEY, account_id INTEGER, description TEXT,
        created_at TEXT, views INTEGER, likes INTEGER, shares INTEGER,
        favorites_count INTEGER, comments_count INTEGER
    )""")
    conn.execute("""CREATE TABLE comments (
        id TEXT PRIMARY KEY, video_id TEXT, text TEXT
    )""")
    conn.commit()
    conn.close()
    return fb_db, tk_db


def _add_fb_post(fb_db, post_id, message, comentarios):
    conn = sqlite3.connect(fb_db)
    conn.execute(
        "INSERT INTO fb_posts VALUES (?, 'Alcaldía de Santa Ana', "
        "'2026-05-01T00:00:00', ?, 50, 10, 0, 5, 3, 2, 4, ?)",
        (post_id, message, len(comentarios)),
    )
    for cid, texto in comentarios:
        conn.execute(
            "INSERT INTO fb_comments VALUES (?, ?, ?)", (cid, post_id, texto)
        )
    conn.commit()
    conn.close()


def _add_tk_video(tk_db, video_id, description, comentarios):
    conn = sqlite3.connect(tk_db)
    conn.execute(
        "INSERT INTO videos VALUES (?, 1, ?, '2026-05-02T00:00:00', "
        "500, 100, 20, 10, ?)",
        (video_id, description, len(comentarios)),
    )
    for cid, texto in comentarios:
        conn.execute(
            "INSERT INTO comments VALUES (?, ?, ?)", (cid, video_id, texto)
        )
    conn.commit()
    conn.close()


def _instalar_mocks(monkeypatch, rec):
    """Mockea embeddings, KMeans, clasificador y carga de BERT/Groq."""
    import sys
    import modulo1_categorias as _m1
    import modulo2_sentimiento as _m2

    monkeypatch.setattr(_m1, "KMeans", _MockKMeans)

    def mock_embeddings(textos, batch_size=64):
        rec.embedding_calls.append(list(textos))
        return np.random.rand(len(textos), 10)

    monkeypatch.setattr(_m1, "generar_embeddings", mock_embeddings)

    def mock_clasificar_lote(textos, *args, **kwargs):
        rec.clasificar_calls.append(list(textos))
        return ([("NEU", 0.0)] * len(textos), "reglas")

    # clasificar_lote se importa en modulo2 desde sentimiento_engine.
    monkeypatch.setattr(_m2, "clasificar_lote", mock_clasificar_lote, raising=False)
    _sent_mod = sys.modules.get("sentimiento_engine")
    if _sent_mod is not None:
        monkeypatch.setattr(_sent_mod, "clasificar_lote", mock_clasificar_lote, raising=False)
        monkeypatch.setattr(
            _sent_mod, "_cargar_bert",
            lambda: (_ for _ in ()).throw(RuntimeError("BERT off")),
            raising=False,
        )
        monkeypatch.setattr(_sent_mod, "groq_disponible", lambda: False, raising=False)


@pytest.fixture
def dbs():
    fb_db, tk_db = _crear_dbs()
    yield fb_db, tk_db
    for p in (fb_db, tk_db):
        if os.path.exists(p):
            os.remove(p)


def test_pipeline_es_incremental(dbs, monkeypatch):
    fb_db, tk_db = dbs
    monkeypatch.setattr(_pl, "FACEBOOK_DB", fb_db)
    monkeypatch.setattr(_pl, "TIKTOK_DB", tk_db)

    rec = _Rec()
    _instalar_mocks(monkeypatch, rec)

    # --- Lote 1: 1 post FB + 1 video TikTok ---
    _add_fb_post(fb_db, "P1", "obras viales calles santa ana", [
        ("c1", "obras calles colonia excelente"),
        ("c2", "pesimo corrupto servicio horrible"),
    ])
    _add_tk_video(tk_db, "V1", "video deporte juvenil santa ana", [
        ("tc1", "me encanto este video"),
        ("tc2", "que malo horrible feo"),
    ])

    r1 = procesar_pipeline()
    assert r1["errores"] == [], r1["errores"]

    assert _count(fb_db, "fb_sentimiento") == 1
    assert _count(tk_db, "tiktok_sentimiento") == 1
    assert _count(fb_db, "fb_engagement") == 1
    assert _count(tk_db, "tiktok_engagement") == 1
    assert _count(fb_db, "post_categorias") == 2  # P1 + V1
    # Embeddings generados para los 2 items nuevos (P1, V1).
    assert rec.n_embeddings == 2, rec.embedding_calls

    # --- Lote 2: se agrega 1 post FB + 1 video TikTok NUEVOS ---
    rec.reset()
    _add_fb_post(fb_db, "P2", "gestion municipal proyecto urbano nuevo", [
        ("c3", "buen proyecto urbano gracias"),
        ("c4", "malo caro innecesario gasto"),
    ])
    _add_tk_video(tk_db, "V2", "evento cultural feria gastronomica", [
        ("tc3", "excelente feria cultural comida"),
        ("tc4", "horrible feria pesima organizacion"),
    ])

    r2 = procesar_pipeline()
    assert r2["errores"] == [], r2["errores"]

    # Solo los 2 items NUEVOS (P2, V2) generan embeddings; P1/V1 vienen de cache.
    assert rec.n_embeddings == 2, rec.embedding_calls

    # Las tablas crecen por APPEND (no se recomputa todo: 1 -> 2).
    assert _count(fb_db, "fb_sentimiento") == 2
    assert _count(tk_db, "tiktok_sentimiento") == 2
    assert _count(fb_db, "fb_engagement") == 2
    assert _count(tk_db, "tiktok_engagement") == 2
    assert _count(fb_db, "post_categorias") == 4  # P1, V1, P2, V2

    # El cache de embeddings retiene los 4 items.
    assert _count(fb_db, "item_embeddings") == 4
