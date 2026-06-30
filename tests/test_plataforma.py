"""Tests del filtrado por plataforma (Facebook / TikTok / Ambas).

Verifican que:
  - Los comentarios se cargan por plataforma y nunca se mezclan cuando el filtro
    no lo indica.
  - La distribucion de sentimiento cambia segun el filtro y combina
    correctamente al seleccionar ambas plataformas.
  - El modelo emocional usa reacciones tipadas en Facebook y sentimiento de
    comentarios en TikTok, y los combina ponderando por volumen.

Se usan bases de datos temporales (tmp_path) y se pasan db_path / tk_db_path
explicitos, de modo que el guard de conftest sobre las DB reales no se activa.
"""

import sqlite3

from dashboard.dash_fuente import (
    cargar_comentarios_periodo,
    distribucion_sentimiento,
)
from dashboard.dash_emocional import (
    emocional_facebook,
    emocional_tiktok,
    metricas_emocionales,
)

INI = "2026-01-01"
FIN = "2026-01-31"


def _crear_fb_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE fb_posts (post_id TEXT, created_time TEXT)")
    cur.executemany("INSERT INTO fb_posts VALUES (?, ?)", [
        ("fb1", "2026-01-05"),
        ("fb2", "2026-01-10"),
    ])
    cur.execute(
        "CREATE TABLE fb_engagement (post_id TEXT, created_time TEXT, "
        "score_emocional REAL, indice_enojo REAL, total_reacciones REAL)"
    )
    cur.executemany("INSERT INTO fb_engagement VALUES (?, ?, ?, ?, ?)", [
        ("fb1", "2026-01-05", 0.5, 0.1, 100),
        ("fb2", "2026-01-10", -0.5, 0.5, 100),
    ])
    cur.execute(
        "CREATE TABLE fb_comments (comment_id TEXT, post_id TEXT, message TEXT, "
        "sentiment TEXT, sentiment_score REAL, topic_category TEXT, zona TEXT)"
    )
    cur.executemany(
        "INSERT INTO fb_comments VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("c1", "fb1", "buen trabajo", None, None, None, None),
            ("c2", "fb1", "excelente", None, None, None, None),
            ("c3", "fb2", "pesimo", None, None, None, None),
            ("c4", "fb2", "muy malo", None, None, None, None),
        ],
    )
    cur.execute(
        "CREATE TABLE fb_sentimiento (post_id TEXT, pct_positivo REAL, "
        "pct_negativo REAL, total_comentarios REAL)"
    )
    cur.executemany("INSERT INTO fb_sentimiento VALUES (?, ?, ?, ?)", [
        ("fb1", 100, 0, 2),
        ("fb2", 0, 100, 2),
    ])
    conn.commit()
    conn.close()


def _crear_tk_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE videos (id TEXT, created_at TEXT)")
    cur.executemany("INSERT INTO videos VALUES (?, ?)", [
        ("tk1", "2026-01-06"),
        ("tk2", "2026-01-12"),
    ])
    cur.execute(
        "CREATE TABLE comments (id TEXT, video_id TEXT, text TEXT, created_at TEXT)"
    )
    cur.executemany("INSERT INTO comments VALUES (?, ?, ?, ?)", [
        ("k1", "tk1", "me encanta", "2026-01-06"),
        ("k2", "tk1", "genial", "2026-01-06"),
        ("k3", "tk2", "no me gusta", "2026-01-12"),
        ("k4", "tk2", "terrible", "2026-01-12"),
    ])
    cur.execute(
        "CREATE TABLE tiktok_sentimiento (video_id TEXT, pct_positivo REAL, "
        "pct_negativo REAL, total_comentarios REAL)"
    )
    cur.executemany("INSERT INTO tiktok_sentimiento VALUES (?, ?, ?, ?)", [
        ("tk1", 80, 10, 2),
        ("tk2", 20, 60, 2),
    ])
    conn.commit()
    conn.close()


def _bases(tmp_path):
    fb = str(tmp_path / "facebook.db")
    tk = str(tmp_path / "tiktok.db")
    _crear_fb_db(fb)
    _crear_tk_db(tk)
    return fb, tk


class TestCargaPorPlataforma:
    def test_solo_facebook(self, tmp_path):
        fb, tk = _bases(tmp_path)
        df = cargar_comentarios_periodo(INI, FIN, "Facebook", db_path=fb, tk_db_path=tk)
        assert len(df) == 4
        assert set(df["plataforma"].unique()) == {"facebook"}

    def test_solo_tiktok(self, tmp_path):
        fb, tk = _bases(tmp_path)
        df = cargar_comentarios_periodo(INI, FIN, "TikTok", db_path=fb, tk_db_path=tk)
        assert len(df) == 4
        assert set(df["plataforma"].unique()) == {"tiktok"}

    def test_ambas_no_mezcla(self, tmp_path):
        fb, tk = _bases(tmp_path)
        df = cargar_comentarios_periodo(INI, FIN, "Ambas", db_path=fb, tk_db_path=tk)
        assert len(df) == 8
        assert set(df["plataforma"].unique()) == {"facebook", "tiktok"}
        fb_rows = df[df["plataforma"] == "facebook"]
        tk_rows = df[df["plataforma"] == "tiktok"]
        assert fb_rows["post_id"].astype(str).str.startswith("fb").all()
        assert tk_rows["post_id"].astype(str).str.startswith("tk").all()


class TestDistribucionPorPlataforma:
    def _dist(self, fb, tk, plat):
        df = cargar_comentarios_periodo(INI, FIN, plat, db_path=fb, tk_db_path=tk)
        return distribucion_sentimiento(df, plat, db_path=fb, tk_db_path=tk)

    def test_facebook(self, tmp_path):
        fb, tk = _bases(tmp_path)
        d = self._dist(fb, tk, "Facebook")
        assert d["pct_favorable"] == 50.0
        assert d["pct_critico"] == 50.0
        assert d["pct_neutral"] == 0.0

    def test_tiktok(self, tmp_path):
        fb, tk = _bases(tmp_path)
        d = self._dist(fb, tk, "TikTok")
        assert d["pct_favorable"] == 50.0
        assert d["pct_critico"] == 35.0
        assert d["pct_neutral"] == 15.0

    def test_ambas_combina(self, tmp_path):
        fb, tk = _bases(tmp_path)
        d = self._dist(fb, tk, "Ambas")
        assert d["pct_favorable"] == 50.0
        assert d["pct_neutral"] == 7.5
        assert d["pct_critico"] == 42.5

    def test_cambia_con_filtro(self, tmp_path):
        fb, tk = _bases(tmp_path)
        fb_d = self._dist(fb, tk, "Facebook")
        tk_d = self._dist(fb, tk, "TikTok")
        amb = self._dist(fb, tk, "Ambas")
        assert fb_d["pct_neutral"] != tk_d["pct_neutral"]
        assert fb_d["pct_critico"] != amb["pct_critico"]


class TestModeloEmocional:
    def test_facebook_usa_reacciones(self, tmp_path):
        fb, tk = _bases(tmp_path)
        r = emocional_facebook(INI, FIN, db_path=fb)
        assert r is not None
        assert round(r["score_emocional"], 3) == 0.0
        assert round(r["indice_enojo"], 3) == 0.3
        assert r["fuente"] == "facebook_reacciones_tipadas"

    def test_tiktok_usa_sentimiento(self, tmp_path):
        fb, tk = _bases(tmp_path)
        r = emocional_tiktok(INI, FIN, tk_db_path=tk)
        assert r is not None
        assert round(r["indice_enojo"], 3) == 0.35
        assert round(r["score_emocional"], 3) == 0.15
        assert r["fuente"] == "tiktok_sentimiento_comentarios"

    def test_ambas_combina_por_volumen(self, tmp_path):
        fb, tk = _bases(tmp_path)
        r = metricas_emocionales("Ambas", INI, FIN, fb_db=fb, tk_db=tk)
        assert r["n_plataformas"] == 2
        assert r["fuente"] == "combinado_ponderado_por_volumen"
        assert 0.30 <= r["indice_enojo"] <= 0.35

    def test_solo_tiktok_no_usa_facebook(self, tmp_path):
        fb, tk = _bases(tmp_path)
        r = metricas_emocionales("TikTok", INI, FIN, fb_db=fb, tk_db=tk)
        assert r["n_plataformas"] == 1
        assert r["fuente"] == "tiktok_sentimiento_comentarios"
        assert round(r["indice_enojo"], 3) == 0.35
