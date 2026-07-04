"""Regresión: cargar_engagement_periodo - unifica carga de FB/TK engagement + sentimiento.

Verifica que:
  - No mezcla plataformas salvo "Ambas"
  - El filtro de período excluye filas fuera de rango
  - ini=None, fin=None devuelve todo el histórico (solo filtrado por plataforma)
  - Un LEFT JOIN sin filas de sentimiento no rompe nada (columnas NaN)
  - Devuelve (df_fb, df_tk) con columnas esperadas
"""

import pandas as pd
import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from dashboard.dash_fuente import cargar_engagement_periodo

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
        ("fb2", "Page1", "2026-01-18", "post 2", 200, 0.4, 0.2, 0.1, 0.0, 0.05, 230, 0.5, "facebook"),
        ("fb3", "Page1", "2026-01-05", "post 3 (fuera)", 50, 0.1, 0.0, 0.0, 0.0, 0.0, 50, -0.1, "facebook"),
    ])
    cur.execute(
        "CREATE TABLE post_categorias (item_id TEXT, categoria_nombre TEXT)"
    )
    cur.executemany("INSERT INTO post_categorias VALUES (?, ?)", [
        ("fb1", "Tema A"),
        ("fb2", "Tema B"),
    ])
    cur.execute(
        "CREATE TABLE fb_sentimiento ("
        "post_id TEXT, score_sentimiento REAL, pct_positivo REAL, "
        "pct_negativo REAL, total_comentarios REAL)"
    )
    cur.executemany("INSERT INTO fb_sentimiento VALUES (?, ?, ?, ?, ?)", [
        ("fb1", 0.5, 70, 10, 20),
        ("fb2", 0.8, 80, 5, 15),
    ])
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
    cur.executemany("INSERT INTO tiktok_engagement VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        ("tk1", "1", "Page1", "video 1", "2026-01-11", 1000, 100, 10, 5, 20, 135, 0.135, 0.01, 0.135, "tiktok"),
        ("tk2", "1", "Page1", "video 2", "2026-01-19", 2000, 200, 20, 10, 40, 270, 0.135, 0.01, 0.135, "tiktok"),
        ("tk3", "1", "Page1", "video 3 (fuera)", "2026-01-02", 500, 50, 5, 2, 10, 67, 0.134, 0.01, 0.134, "tiktok"),
    ])
    cur.execute(
        "CREATE TABLE tiktok_sentimiento ("
        "video_id TEXT, pct_positivo REAL, pct_negativo REAL, total_comentarios REAL)"
    )
    cur.executemany("INSERT INTO tiktok_sentimiento VALUES (?, ?, ?, ?)", [
        ("tk1", 75, 5, 20),
        ("tk2", 85, 2, 40),
    ])
    conn.commit()
    conn.close()


def _bases(tmp_path):
    fb = str(tmp_path / "facebook.db")
    tk = str(tmp_path / "tiktok.db")
    _crear_fb_db(fb)
    _crear_tk_db(tk)
    return fb, tk


class TestCargarEngagementPeriodo:
    def test_solo_facebook(self, tmp_path):
        fb, tk = _bases(tmp_path)
        df_fb, df_tk = cargar_engagement_periodo(INI, FIN, "Facebook", fb_db=fb, tk_db=tk)
        assert len(df_fb) == 2  # solo fb1 y fb2 en el período
        assert len(df_tk) == 0
        assert set(df_fb["plataforma"].unique()) == {"facebook"}

    def test_solo_tiktok(self, tmp_path):
        fb, tk = _bases(tmp_path)
        df_fb, df_tk = cargar_engagement_periodo(INI, FIN, "TikTok", fb_db=fb, tk_db=tk)
        assert len(df_fb) == 0
        assert len(df_tk) == 2  # solo tk1 y tk2 en el período
        assert set(df_tk["plataforma"].unique()) == {"tiktok"}

    def test_ambas_no_mezcla(self, tmp_path):
        fb, tk = _bases(tmp_path)
        df_fb, df_tk = cargar_engagement_periodo(INI, FIN, "Ambas", fb_db=fb, tk_db=tk)
        assert len(df_fb) == 2
        assert len(df_tk) == 2
        assert set(df_fb["plataforma"].unique()) == {"facebook"}
        assert set(df_tk["plataforma"].unique()) == {"tiktok"}

    def test_filtro_periodo_excluye_fuera_rango(self, tmp_path):
        fb, tk = _bases(tmp_path)
        df_fb, df_tk = cargar_engagement_periodo(INI, FIN, "Ambas", fb_db=fb, tk_db=tk)
        # fb3 (2026-01-05) y tk3 (2026-01-02) están fuera del rango 10-20 ene
        assert all(pd.to_datetime(df_fb["created_time"]) >= pd.Timestamp(INI))
        assert all(pd.to_datetime(df_fb["created_time"]) <= pd.Timestamp(FIN))
        assert all(pd.to_datetime(df_tk["created_at"]) >= pd.Timestamp(INI))
        assert all(pd.to_datetime(df_tk["created_at"]) <= pd.Timestamp(FIN))

    def test_ini_none_fin_none_devuelve_historico(self, tmp_path):
        fb, tk = _bases(tmp_path)
        df_fb, df_tk = cargar_engagement_periodo(None, None, "Ambas", fb_db=fb, tk_db=tk)
        assert len(df_fb) == 3  # todos los 3 posts FB
        assert len(df_tk) == 3  # todos los 3 videos TK

    def test_left_join_sin_sentimiento_no_rompe(self, tmp_path):
        """fb3 no tiene fila en fb_sentimiento; tk3 no tiene en tiktok_sentimiento."""
        fb, tk = _bases(tmp_path)
        df_fb, df_tk = cargar_engagement_periodo(None, None, "Ambas", fb_db=fb, tk_db=tk)
        # fb3 debe tener columnas de sentimiento como NaN, no romper
        fb3 = df_fb[df_fb["post_id"] == "fb3"]
        assert len(fb3) == 1
        assert pd.isna(fb3["score_sentimiento"].iloc[0])
        assert pd.isna(fb3["pct_positivo"].iloc[0])
        assert pd.isna(fb3["pct_negativo"].iloc[0])
        assert pd.isna(fb3["sent_total_comentarios"].iloc[0])

        tk3 = df_tk[df_tk["id"] == "tk3"]
        assert len(tk3) == 1
        assert pd.isna(tk3["pct_positivo"].iloc[0])
        assert pd.isna(tk3["pct_negativo"].iloc[0])
        assert pd.isna(tk3["total_comentarios"].iloc[0])

    def test_columnas_esperadas_presentes(self, tmp_path):
        fb, tk = _bases(tmp_path)
        df_fb, df_tk = cargar_engagement_periodo(INI, FIN, "Ambas", fb_db=fb, tk_db=tk)
        # Facebook
        fb_cols = {
            "post_id", "page_name", "created_time", "message", "total_reacciones",
            "indice_amor", "indice_humor", "indice_asombro", "indice_tristeza",
            "indice_enojo", "engagement_total", "score_emocional", "plataforma",
            "categoria_nombre", "score_sentimiento", "pct_positivo", "pct_negativo",
            "sent_total_comentarios"
        }
        assert fb_cols.issubset(set(df_fb.columns))
        # TikTok
        tk_cols = {
            "id", "account_id", "page_name", "description", "created_at",
            "views", "likes", "shares", "favorites_count", "comments_count",
            "engagement_total", "engagement_rate", "indice_viralidad",
            "score_engagement", "plataforma", "categoria_nombre",
            "pct_positivo", "pct_negativo", "total_comentarios"
        }
        assert tk_cols.issubset(set(df_tk.columns))