"""Tests para la estabilizacion de cluster_id entre corridas de KMeans (D22)."""
import sqlite3

import numpy as np

from dashboard.modulo1_categorias import (
    _remapear_clusters_estables,
    categorizar_posts,
    guardar_nombres_clusters,
)


def test_remapear_sin_previos_usa_ids_de_kmeans_tal_cual():
    nuevos = {0: np.array([1.0, 0.0]), 1: np.array([0.0, 1.0])}
    mapeo = _remapear_clusters_estables(nuevos, {})
    assert mapeo == {0: 0, 1: 1}


def test_remapear_con_previos_reasigna_por_similitud():
    prev = {
        10: np.array([1.0, 0.0, 0.0]),
        20: np.array([0.0, 1.0, 0.0]),
    }
    nuevos = {
        0: np.array([0.0, 0.9, 0.1]),
        1: np.array([0.9, 0.0, 0.1]),
    }
    mapeo = _remapear_clusters_estables(nuevos, prev)
    assert mapeo[0] == 20
    assert mapeo[1] == 10


def test_remapear_cluster_nuevo_sin_match_recibe_id_nunca_usado():
    prev = {10: np.array([1.0, 0.0, 0.0]), 20: np.array([0.0, 1.0, 0.0])}
    nuevos = {
        0: np.array([0.0, 0.0, 1.0]),
        1: np.array([0.9, 0.1, 0.0]),
    }
    mapeo = _remapear_clusters_estables(nuevos, prev)
    assert mapeo[1] == 10
    assert mapeo[0] > 20


def test_categorizar_posts_preserva_nombre_categoria_entre_corridas(tmp_path):
    fb_db = str(tmp_path / "facebook.db")
    tk_db = str(tmp_path / "tiktok.db")

    conn_fb = sqlite3.connect(fb_db)
    conn_fb.execute("""
        CREATE TABLE fb_posts (
            post_id TEXT PRIMARY KEY,
            page_name TEXT,
            message TEXT,
            created_time TEXT
        )
    """)
    for pid, page, msg, fecha in [
        ("p1", "Alcaldía de Santa Ana", "Inician obras de pavimentacion en la colonia centro", "2026-06-01"),
        ("p2", "Alcaldía de Santa Ana", "Jornada de limpieza en el parque municipal este sabado", "2026-06-02"),
        ("p3", "Gustavo Acevedo", "Reunion con vecinos para tratar temas de seguridad", "2026-06-03"),
    ]:
        conn_fb.execute(
            "INSERT INTO fb_posts (post_id, page_name, message, created_time) VALUES (?, ?, ?, ?)",
            (pid, page, msg, fecha),
        )
    conn_fb.commit()
    conn_fb.close()

    conn_tk = sqlite3.connect(tk_db)
    conn_tk.execute("""
        CREATE TABLE videos (
            id TEXT PRIMARY KEY,
            description TEXT,
            created_at TEXT
        )
    """)
    conn_tk.commit()
    conn_tk.close()

    categorizar_posts(fb_db=fb_db, tk_db=tk_db)
    guardar_nombres_clusters(fb_db=fb_db)

    conn = sqlite3.connect(fb_db)
    primera = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT item_id, categoria_nombre FROM post_categorias"
        ).fetchall()
    }
    conn.close()

    assert len(primera) == 3
    for pid in ("p1", "p2", "p3"):
        assert primera[pid] is not None

    conn_fb = sqlite3.connect(fb_db)
    conn_fb.execute(
        "INSERT INTO fb_posts (post_id, page_name, message, created_time) VALUES (?, ?, ?, ?)",
        ("p4", "Alcaldía de Santa Ana", "Nuevo centro de salud abrira sus puertas la proxima semana", "2026-06-10"),
    )
    conn_fb.commit()
    conn_fb.close()

    categorizar_posts(fb_db=fb_db, tk_db=tk_db)
    guardar_nombres_clusters(fb_db=fb_db)

    conn = sqlite3.connect(fb_db)
    segunda = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT item_id, categoria_nombre FROM post_categorias"
        ).fetchall()
    }
    conn.close()

    for pid in ("p1", "p2", "p3"):
        assert segunda[pid] == primera[pid], (
            f"Nombre de {pid} cambio entre corridas: "
            f"'{primera[pid]}' -> '{segunda[pid]}'"
        )

    assert segunda.get("p4") is not None
