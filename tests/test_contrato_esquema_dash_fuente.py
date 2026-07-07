"""Tests: las columnas requeridas por dash_metrics/dash_emocional existen en el esquema real."""
import sqlite3

import pandas as pd
import pytest

from dashboard.dash_fuente import cargar_engagement_periodo
from dashboard.dash_metrics import COLUMNAS_REQUERIDAS_CONTAGIO
from dashboard.dash_emocional import COLUMNAS_REQUERIDAS_FACEBOOK, COLUMNAS_REQUERIDAS_TIKTOK


INI = "2026-01-10"
FIN = "2026-01-20"


def _crear_fb_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE fb_engagement ("
        "post_id TEXT, page_name TEXT, created_time TEXT, message TEXT, "
        "total_reacciones REAL, indice_amor REAL, indice_humor REAL, "
        "indice_asombro REAL, indice_tristeza REAL, indice_enojo REAL, "
        "engagement_total REAL, score_emocional REAL, plataforma TEXT)"
    )
    cur.executemany("INSERT INTO fb_engagement VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        ("fb1", "Page1", "2026-01-12", "post 1", 100, 0.3, 0.1, 0.05, 0.02, 0.1, 120, 0.2, "facebook"),
    ])
    cur.execute("CREATE TABLE post_categorias (item_id TEXT, categoria_nombre TEXT)")
    cur.executemany("INSERT INTO post_categorias VALUES (?, ?)", [("fb1", "Tema A")])
    cur.execute(
        "CREATE TABLE fb_sentimiento ("
        "post_id TEXT, score_sentimiento REAL, pct_positivo REAL, "
        "pct_negativo REAL, total_comentarios REAL)"
    )
    cur.executemany("INSERT INTO fb_sentimiento VALUES (?, ?, ?, ?, ?)",
                    [("fb1", 0.5, 70, 10, 20)])
    conn.commit()
    conn.close()


def _crear_tk_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE tiktok_engagement ("
        "id TEXT, account_id TEXT, page_name TEXT, description TEXT, created_at TEXT, "
        "views REAL, likes REAL, shares REAL, favorites_count REAL, comments_count REAL, "
        "engagement_total REAL, engagement_rate REAL, indice_viralidad REAL, "
        "score_engagement REAL, plataforma TEXT)"
    )
    cur.executemany(
        "INSERT INTO tiktok_engagement VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [("tk1", "1", "Page1", "video 1", "2026-01-11",
          1000, 100, 10, 5, 20, 135, 0.135, 0.01, 0.135, "tiktok")],
    )
    cur.execute(
        "CREATE TABLE tiktok_sentimiento ("
        "video_id TEXT, pct_positivo REAL, pct_negativo REAL, total_comentarios REAL)"
    )
    cur.executemany("INSERT INTO tiktok_sentimiento VALUES (?, ?, ?, ?)",
                    [("tk1", 75, 5, 20)])
    conn.commit()
    conn.close()


class TestColumnasRequeridasContagio:

    def test_contagio_es_subconjunto_de_columnas_fb(self, tmp_path):
        fb = str(tmp_path / "facebook.db")
        tk = str(tmp_path / "tiktok.db")
        _crear_fb_db(fb)
        _crear_tk_db(tk)
        df_fb, _ = cargar_engagement_periodo(None, None, "Facebook", fb_db=fb, tk_db=tk)
        assert COLUMNAS_REQUERIDAS_CONTAGIO == sorted(
            set(COLUMNAS_REQUERIDAS_CONTAGIO) & set(df_fb.columns),
            key=COLUMNAS_REQUERIDAS_CONTAGIO.index,
        )


class TestColumnasRequeridasFacebook:

    def test_facebook_es_subconjunto_de_columnas_fb(self, tmp_path):
        fb = str(tmp_path / "facebook.db")
        tk = str(tmp_path / "tiktok.db")
        _crear_fb_db(fb)
        _crear_tk_db(tk)
        df_fb, _ = cargar_engagement_periodo(None, None, "Facebook", fb_db=fb, tk_db=tk)
        assert COLUMNAS_REQUERIDAS_FACEBOOK == sorted(
            set(COLUMNAS_REQUERIDAS_FACEBOOK) & set(df_fb.columns),
            key=COLUMNAS_REQUERIDAS_FACEBOOK.index,
        )


class TestColumnasRequeridasTikTok:

    def test_tiktok_es_subconjunto_de_columnas_tk(self, tmp_path):
        fb = str(tmp_path / "facebook.db")
        tk = str(tmp_path / "tiktok.db")
        _crear_fb_db(fb)
        _crear_tk_db(tk)
        _, df_tk = cargar_engagement_periodo(None, None, "TikTok", fb_db=fb, tk_db=tk)
        assert COLUMNAS_REQUERIDAS_TIKTOK == sorted(
            set(COLUMNAS_REQUERIDAS_TIKTOK) & set(df_tk.columns),
            key=COLUMNAS_REQUERIDAS_TIKTOK.index,
        )
