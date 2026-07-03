"""Tests de regresión para dash_bloque3 (Bloque III — Riesgo y Autenticidad).

Verifica la migración a dash_fuente.py: _detectar_fricciones ahora usa
tema_por_comentario (centralizado) en vez de _mapa_categoria_posts privado.
"""

import sqlite3
import pandas as pd
import sys
import os
import tempfile

# Setup path like other dashboard tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from dashboard.dash_bloque3 import _detectar_fricciones


class TestDetectarFriccionesMigration:
    """Test que _detectar_fricciones usa tema_por_comentario centralizado."""

    def _make_test_db(self):
        """Crea un archivo SQLite temporal con tabla post_categorias y devuelve su path."""
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        conn = sqlite3.connect(tmp.name)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE post_categorias (
                item_id TEXT PRIMARY KEY,
                categoria_nombre TEXT
            );
        """)
        conn.commit()
        conn.close()
        return tmp.name

    def test_fricciones_usa_tema_de_post_categorias(self):
        """Comentarios críticos se agrupan por categoría de su post (fb_comments no tiene topic_category)."""
        db_path = self._make_test_db()
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO post_categorias VALUES ('post_1', 'obras'), ('post_2', 'seguridad')")
        conn.commit()
        conn.close()

        # DataFrame de comentarios: post_id apuntando a posts categorizados
        # fb_comments no trae topic_category (queda NA)
        df = pd.DataFrame({
            "post_id": ["post_1", "post_1", "post_2", "post_2"],
            "message": ["calles rotas", "baches en todas partes", "poca policia", "inseguridad total"],
            "sentiment": ["negativo", "negativo", "negativo", "negativo"],
            "sentiment_score": [-0.6, -0.5, -0.7, -0.8],
            "topic_category": [pd.NA, pd.NA, pd.NA, pd.NA],  # como en la BD real
        })

        # Inyectar la DB path en el módulo dash_fuente para que use nuestra BD de test
        import dashboard.dash_fuente as dfuente
        old_db = dfuente.DASH_FACEBOOK_DB
        dfuente.DASH_FACEBOOK_DB = db_path

        try:
            fr = _detectar_fricciones(df)
        finally:
            dfuente.DASH_FACEBOOK_DB = old_db
            os.unlink(db_path)

        # Debe agrupar por categoría del post, no caer en "General"
        assert len(fr) == 2
        temas = {f["tema"] for f in fr}
        assert "obras" in temas
        assert "seguridad" in temas
        assert "General" not in temas

    def test_fricciones_fallback_a_general_si_no_hay_post_categorias(self):
        """Si post_categorias está vacía o el post no está, cae a topic_category del comentario; si tampoco, 'General'."""
        db_path = self._make_test_db()
        # tabla vacía

        df = pd.DataFrame({
            "post_id": ["post_x", "post_y"],
            "message": ["comentario sin cat", "otro sin cat"],
            "sentiment": ["negativo", "negativo"],
            "sentiment_score": [-0.5, -0.6],
            "topic_category": [pd.NA, pd.NA],  # tampoco hay topic_category
        })

        import dashboard.dash_fuente as dfuente
        old_db = dfuente.DASH_FACEBOOK_DB
        dfuente.DASH_FACEBOOK_DB = db_path

        try:
            fr = _detectar_fricciones(df)
        finally:
            dfuente.DASH_FACEBOOK_DB = old_db
            os.unlink(db_path)

        # Sin post_categorias ni topic_category -> todo cae en "General"
        assert len(fr) == 1
        assert fr[0]["tema"] == "General"
        assert fr[0]["n"] == 2

    def test_fricciones_fallback_topic_category_comentario(self):
        """Si post_categorias no tiene el post pero el comentario tiene topic_category, usa ese."""
        db_path = self._make_test_db()
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO post_categorias VALUES ('post_1', 'obras')")
        conn.commit()
        conn.close()

        df = pd.DataFrame({
            "post_id": ["post_1", "post_2"],
            "message": ["calles rotas", "basura en la plaza"],
            "sentiment": ["negativo", "negativo"],
            "sentiment_score": [-0.5, -0.6],
            "topic_category": [pd.NA, "limpieza"],  # post_2 tiene topic_category
        })

        import dashboard.dash_fuente as dfuente
        old_db = dfuente.DASH_FACEBOOK_DB
        dfuente.DASH_FACEBOOK_DB = db_path

        try:
            fr = _detectar_fricciones(df)
        finally:
            dfuente.DASH_FACEBOOK_DB = old_db
            os.unlink(db_path)

        assert len(fr) == 2
        temas = {f["tema"] for f in fr}
        assert "obras" in temas
        assert "limpieza" in temas
        assert "General" not in temas

    def test_fricciones_vacio_o_none(self):
        """DataFrame vacío o None devuelve lista vacía (no rompe)."""
        assert _detectar_fricciones(pd.DataFrame()) == []
        assert _detectar_fricciones(None) == []

    def test_fricciones_solo_neutrales_no_devuelve_nada(self):
        """Si no hay comentarios críticos, devuelve lista vacía."""
        df = pd.DataFrame({
            "post_id": ["post_1"],
            "message": ["todo bien"],
            "sentiment": ["positivo"],
            "sentiment_score": [0.5],
            "topic_category": ["obras"],
        })
        fr = _detectar_fricciones(df)
        assert fr == []