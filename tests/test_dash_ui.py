"""Tests de regresión para dash_ui.py helpers de referencias.

Verifica que _post_ids_por_tema_comentarios resuelve el tema vía
tema_por_comentario (post_categorias con fallback a topic_category)
en vez de consultar directamente fb_comments.topic_category.
"""

import sqlite3
import sys
import os
import tempfile

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from dashboard.dash_ui import _post_ids_por_tema_comentarios


class TestPostIdsPorTemaComentarios:
    """_post_ids_por_tema_comentarios usa tema_por_comentario centralizado."""

    def _make_db(self, rows):
        """Crea un archivo SQLite temporal con tablas fb_comments y post_categorias.

        rows: lista de dicts con claves 'post_id', 'topic_category', 'categoria_nombre'.
        topic_category puede ser None/'' (simula columna no poblada en producción).
        categoria_nombre es el valor en post_categorias (puede ser None si no existe).
        """
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        conn = sqlite3.connect(tmp.name)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE fb_comments (
                post_id TEXT,
                topic_category TEXT
            );
            CREATE TABLE post_categorias (
                item_id TEXT PRIMARY KEY,
                categoria_nombre TEXT
            );
        """)
        for r in rows:
            cur.execute(
                "INSERT INTO fb_comments (post_id, topic_category) VALUES (?, ?)",
                (r["post_id"], r.get("topic_category")),
            )
            cat = r.get("categoria_nombre")
            if cat is not None:
                cur.execute(
                    "INSERT OR REPLACE INTO post_categorias (item_id, categoria_nombre) VALUES (?, ?)",
                    (r["post_id"], cat),
                )
        conn.commit()
        conn.close()
        return tmp.name

    def test_devuelve_ids_cuando_topic_category_vacio_pero_post_categorias_tiene_tema(self):
        """Caso real: fb_comments.topic_category NULL, categoría solo en post_categorias."""
        db_path = self._make_db([
            {"post_id": "p1", "topic_category": None, "categoria_nombre": "obras"},
            {"post_id": "p2", "topic_category": None, "categoria_nombre": "obras"},
            {"post_id": "p3", "topic_category": None, "categoria_nombre": "seguridad"},
            {"post_id": "p4", "topic_category": "",     "categoria_nombre": "obras"},
        ])

        import dashboard.dash_ui as dui
        old_db = dui.FACEBOOK_DB
        dui.FACEBOOK_DB = db_path

        try:
            ids = _post_ids_por_tema_comentarios("obras")
        finally:
            dui.FACEBOOK_DB = old_db
            os.unlink(db_path)

        assert sorted(ids) == ["p1", "p2", "p4"], (
            f"Esperaba ['p1', 'p2', 'p4'] con tema 'obras', obtuvo {ids}"
        )

    def test_devuelve_ids_cuando_topic_category_esta_poblado(self):
        """Fallback a topic_category si post_categorias no tiene el post."""
        db_path = self._make_db([
            {"post_id": "p1", "topic_category": "limpieza", "categoria_nombre": "obras"},
            {"post_id": "p2", "topic_category": "limpieza", "categoria_nombre": None},
        ])

        import dashboard.dash_ui as dui
        old_db = dui.FACEBOOK_DB
        dui.FACEBOOK_DB = db_path

        try:
            ids_limpieza = _post_ids_por_tema_comentarios("limpieza")
            ids_obras = _post_ids_por_tema_comentarios("obras")
        finally:
            dui.FACEBOOK_DB = old_db
            os.unlink(db_path)

        # p1: post_categorias dice "obras" -> tema "obras", NO "limpieza"
        # p2: post_categorias no tiene entry, topic_category="limpieza" -> tema "limpieza"
        assert ids_limpieza == ["p2"], f"Esperaba ['p2'], obtuvo {ids_limpieza}"
        assert ids_obras == ["p1"], f"Esperaba ['p1'], obtuvo {ids_obras}"

    def test_devuelve_vacio_si_no_hay_match(self):
        """Tema que no está ni en post_categorias ni en topic_category -> lista vacía."""
        db_path = self._make_db([
            {"post_id": "p1", "topic_category": None, "categoria_nombre": "obras"},
        ])

        import dashboard.dash_ui as dui
        old_db = dui.FACEBOOK_DB
        dui.FACEBOOK_DB = db_path

        try:
            ids = _post_ids_por_tema_comentarios("seguridad")
        finally:
            dui.FACEBOOK_DB = old_db
            os.unlink(db_path)

        assert ids == [], f"Esperaba [], obtuvo {ids}"

    def test_db_vacia_retorna_vacio(self):
        """fb_comments vacía -> lista vacía."""
        db_path = self._make_db([])

        import dashboard.dash_ui as dui
        old_db = dui.FACEBOOK_DB
        dui.FACEBOOK_DB = db_path

        try:
            ids = _post_ids_por_tema_comentarios("obras")
        finally:
            dui.FACEBOOK_DB = old_db
            os.unlink(db_path)

        assert ids == []
