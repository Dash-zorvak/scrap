"""Tests para Bloque 9: simplificar aprobación de comentarios.

Cubre:
  - Esquema: subtema_especifico y relevancia_al_post eliminados de las 3 bases.
  - Tabla de valencia: postura se deriva correctamente de la emoción.
  - Importación JSON: campos emocion/tema_sugerido se reflejan en tema_aprobaciones.
  - Regresión: verificar que queries/report no dependen de columnas eliminadas.
"""

import json
import os
import sqlite3
import tempfile

import pytest


# ── Helpers ──────────────────────────────────────────────


def _crear_bd_vacia(schema_sql=None):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    if schema_sql:
        conn = sqlite3.connect(path)
        conn.executescript(schema_sql)
        conn.close()
    return path


_FB_TEMA_APROBACIONES_SCHEMA = """
CREATE TABLE IF NOT EXISTS tema_aprobaciones (
    comment_id TEXT PRIMARY KEY,
    tema TEXT NOT NULL,
    tema_sugerido TEXT,
    tono TEXT,
    postura TEXT DEFAULT 'neutral',
    confianza REAL,
    texto TEXT,
    estado TEXT DEFAULT 'aprobado',
    fecha TEXT,
    emocion TEXT DEFAULT 'calma'
);
"""


# ════════════════════════════════════════════════════════════
# Test 1: Esquema — columnas eliminadas de las 3 bases
# ════════════════════════════════════════════════════════════


class TestEsquemaColumnasEliminadas:
    """Verificar que subtema_especifico y relevancia_al_post no existen
    en las 3 bases de datos."""

    def _check_db(self, db_path):
        from dashboard.tema_aprobaciones import asegurar_tabla
        asegurar_tabla(db_path)
        conn = sqlite3.connect(db_path)
        cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(tema_aprobaciones)"
        ).fetchall()}
        conn.close()
        assert "subtema_especifico" not in cols, (
            f"subtema_especifico aún existe en {db_path}: {cols}"
        )
        assert "relevancia_al_post" not in cols, (
            f"relevancia_al_post aún existe en {db_path}: {cols}"
        )

    def test_facebook_no_tiene_columnas_obsoletas(self):
        db = _crear_bd_vacia()
        try:
            self._check_db(db)
        finally:
            os.unlink(db)

    def test_tiktok_no_tiene_columnas_obsoletas(self):
        from dashboard.tema_aprobaciones import asegurar_tabla_en_tiktok
        db = _crear_bd_vacia()
        try:
            asegurar_tabla_en_tiktok(db)
            conn = sqlite3.connect(db)
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(tema_aprobaciones)"
            ).fetchall()}
            conn.close()
            assert "subtema_especifico" not in cols
            assert "relevancia_al_post" not in cols
        finally:
            os.unlink(db)

    def test_externos_no_tiene_columnas_obsoletas(self):
        from dashboard.tema_aprobaciones import asegurar_tabla
        db = _crear_bd_vacia()
        try:
            asegurar_tabla(db)
            conn = sqlite3.connect(db)
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(tema_aprobaciones)"
            ).fetchall()}
            conn.close()
            assert "subtema_especifico" not in cols
            assert "relevancia_al_post" not in cols
        finally:
            os.unlink(db)

    def test_tabla_con_columnas_obsoletas_se_reconstruye(self):
        """Si la tabla vieja tenía las columnas, se eliminan via reconstrucción."""
        db = _crear_bd_vacia()
        try:
            conn = sqlite3.connect(db)
            conn.executescript("""
                CREATE TABLE tema_aprobaciones (
                    comment_id TEXT PRIMARY KEY,
                    tema TEXT NOT NULL,
                    tema_sugerido TEXT, tono TEXT,
                    postura TEXT DEFAULT 'neutral',
                    confianza REAL, texto TEXT,
                    estado TEXT DEFAULT 'aprobado', fecha TEXT,
                    emocion TEXT DEFAULT 'calma',
                    subtema_especifico TEXT,
                    intensidad_postura TEXT DEFAULT 'moderada',
                    emociones TEXT,
                    relevancia_al_post TEXT DEFAULT 'directo_al_post'
                );
                INSERT INTO tema_aprobaciones
                (comment_id, tema, texto, estado, fecha)
                VALUES ('old1', 'seguridad', 'test old', 'aprobado', '2026-01-01');
            """)
            conn.commit()
            conn.close()

            from dashboard.tema_aprobaciones import asegurar_tabla
            asegurar_tabla(db)

            conn = sqlite3.connect(db)
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(tema_aprobaciones)"
            ).fetchall()}
            row = conn.execute(
                "SELECT comment_id FROM tema_aprobaciones WHERE comment_id='old1'"
            ).fetchone()
            conn.close()
            assert "subtema_especifico" not in cols
            assert "relevancia_al_post" not in cols
            assert row is not None
        finally:
            os.unlink(db)


# ════════════════════════════════════════════════════════════
# Test 2: Tabla de valencia — postura derivada de emoción
# ════════════════════════════════════════════════════════════


class TestValenciaPostura:
    """Para al menos una emoción de cada familia + una díada + una cívica,
    guardar_aprobacion() asigna la postura correcta."""

    def test_alegria_familia_joy_apoyo(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v1", "seguridad", texto="happy",
                              emociones=["alegria"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v1'"
            ).fetchone()[0]
            conn.close()
            assert post == "apoyo"
        finally:
            os.unlink(db)

    def test_confianza_familia_trust_apoyo(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v2", "seguridad", texto="trust",
                              emociones=["confianza"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v2'"
            ).fetchone()[0]
            conn.close()
            assert post == "apoyo"
        finally:
            os.unlink(db)

    def test_optimismo_familia_diada_neutral(self):
        """Optimismo es anticipation+joy → familia 'diada'. No está en la tabla
        directamente, devuelve neutral."""
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v3", "seguridad", texto="opt",
                              emociones=["optimismo"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v3'"
            ).fetchone()[0]
            conn.close()
            assert post == "neutral"
        finally:
            os.unlink(db)

    def test_preocupacion_familia_fear_critica(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v4", "seguridad", texto="worry",
                              emociones=["preocupacion"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v4'"
            ).fetchone()[0]
            conn.close()
            assert post == "critica"
        finally:
            os.unlink(db)

    def test_tristeza_familia_sadness_critica(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v5", "seguridad", texto="sad",
                              emociones=["tristeza"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v5'"
            ).fetchone()[0]
            conn.close()
            assert post == "critica"
        finally:
            os.unlink(db)

    def test_desagrado_familia_disgust_critica(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v6", "seguridad", texto="disgust",
                              emociones=["desagrado"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v6'"
            ).fetchone()[0]
            conn.close()
            assert post == "critica"
        finally:
            os.unlink(db)

    def test_enojo_familia_anger_critica(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v7", "seguridad", texto="angry",
                              emociones=["enojo"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v7'"
            ).fetchone()[0]
            conn.close()
            assert post == "critica"
        finally:
            os.unlink(db)

    def test_sorpresa_familia_surprise_neutral(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v8", "seguridad", texto="wow",
                              emociones=["sorpresa"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v8'"
            ).fetchone()[0]
            conn.close()
            assert post == "neutral"
        finally:
            os.unlink(db)

    def test_desprecio_diada_critica(self):
        """Desprecio es díada disgust+anger → familia diada. Mapea a
        la familia de su componente dominante (disgust→critica)."""
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v9", "seguridad", texto="disdain",
                              emociones=["desprecio"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v9'"
            ).fetchone()[0]
            conn.close()
            assert post == "critica"
        finally:
            os.unlink(db)

    def test_reclamo_civica_neutral(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v10", "seguridad", texto="claim",
                              emociones=["reclamo"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v10'"
            ).fetchone()[0]
            conn.close()
            assert post == "neutral"
        finally:
            os.unlink(db)

    def test_reconocimiento_civica_neutral(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v11", "seguridad", texto="thanks",
                              emociones=["reconocimiento"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v11'"
            ).fetchone()[0]
            conn.close()
            assert post == "neutral"
        finally:
            os.unlink(db)

    def test_ironia_civica_neutral(self):
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v12", "seguridad", texto="irony",
                              emociones=["ironia"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v12'"
            ).fetchone()[0]
            conn.close()
            assert post == "neutral"
        finally:
            os.unlink(db)

    def test_esperanza_diada_apoyo(self):
        """Esperanza es anticipation+trust → familia anticipation → apoyo."""
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v13", "seguridad", texto="hope",
                              emociones=["esperanza"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v13'"
            ).fetchone()[0]
            conn.close()
            assert post == "apoyo"
        finally:
            os.unlink(db)

    def test_ansiedad_diada_critica(self):
        """Ansiedad es anticipation+fear → mapeada directamente en la tabla
        VALENCIA_POSTURA como critica."""
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(db, "v14", "seguridad", texto="anxious",
                              emociones=["ansiedad"])
            conn = sqlite3.connect(db)
            post = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='v14'"
            ).fetchone()[0]
            conn.close()
            assert post == "critica"
        finally:
            os.unlink(db)


# ════════════════════════════════════════════════════════════
# Test 3: Importación JSON — campos por comentario
# ════════════════════════════════════════════════════════════


class TestImportacionJSON:
    """Un JSON con emocion/tema_sugerido por comentario se refleja
    correctamente en tema_aprobaciones tras importar."""

    def test_guarda_emocion_desde_json(self):
        """Simula importación JSON: guardar_aprobacion recibe emociones
        que provienen del JSON importado."""
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion

            comentarios_json = [
                {"texto": "Excelente trabajo", "emocion": "alegria"},
                {"texto": "Muy mal servicio", "emocion": "enojo"},
                {"texto": "No entiendo", "emocion": "sorpresa"},
            ]

            for i, c in enumerate(comentarios_json):
                ok = guardar_aprobacion(
                    db, f"imp_{i}", "seguridad",
                    texto=c["texto"],
                    emociones=[c["emocion"]],
                )
                assert ok

            conn = sqlite3.connect(db)
            rows = conn.execute(
                "SELECT comment_id, emocion, postura FROM tema_aprobaciones "
                "ORDER BY comment_id"
            ).fetchall()
            conn.close()

            assert len(rows) == 3
            posturas = {r[0]: (r[1], r[2]) for r in rows}
            assert posturas["imp_0"] == ("alegria", "apoyo")
            assert posturas["imp_1"] == ("enojo", "critica")
            assert posturas["imp_2"] == ("sorpresa", "neutral")
        finally:
            os.unlink(db)

    def test_tema_sugerido_se_guarda(self):
        """El tema_sugerido del JSON se guarda en tema_aprobaciones."""
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(
                db, "ts1", "seguridad",
                texto="baches en la calle",
                tema_sugerido="obras_servicios",
                emociones=["tristeza"],
            )
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT tema_sugerido FROM tema_aprobaciones WHERE comment_id='ts1'"
            ).fetchone()
            conn.close()
            assert row[0] == "obras_servicios"
        finally:
            os.unlink(db)

    def test_confianza_emocion_baja_no_guarda_emocion(self):
        """Un comentario con confianza_emocion baja se puede guardar con
        la emoción por defecto (calma)."""
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            ok = guardar_aprobacion(
                db, "ce1", "seguridad",
                texto="comentario dudoso",
                emociones=[],
            )
            assert ok
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT emocion, postura FROM tema_aprobaciones WHERE comment_id='ce1'"
            ).fetchone()
            conn.close()
            assert row[0] == "calma"
            assert row[1] == "neutral"
        finally:
            os.unlink(db)

    def test_postura_json_ignorada_se_deriva(self):
        """Si el JSON traía un campo postura, se ignora — se deriva de la emoción."""
        db = _crear_bd_vacia()
        try:
            from dashboard.tema_aprobaciones import guardar_aprobacion
            guardar_aprobacion(
                db, "pj1", "seguridad",
                texto="test",
                postura="apoyo",
                emociones=["tristeza"],
            )
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT postura FROM tema_aprobaciones WHERE comment_id='pj1'"
            ).fetchone()
            conn.close()
            assert row[0] == "critica"
        finally:
            os.unlink(db)


# ════════════════════════════════════════════════════════════
# Test 4: Regresión — queries y report no dependen de columnas eliminadas
# ════════════════════════════════════════════════════════════


class TestRegresion:
    def test_agregar_por_tema_no_requiere_columnas_eliminadas(self):
        """agregar_por_tema() funciona correctamente sin subtema_especifico
        ni relevancia_al_post."""
        from dashboard.tema_aprobaciones import (
            guardar_aprobacion, agregar_por_tema
        )
        db = _crear_bd_vacia()
        try:
            guardar_aprobacion(db, "r1", "seguridad", texto="test1",
                              emociones=["alegria"])
            guardar_aprobacion(db, "r2", "seguridad", texto="test2",
                              emociones=["enojo"])
            temas = agregar_por_tema(db)
            assert len(temas) == 1
            assert temas[0]["doc_count"] == 2
            assert temas[0]["apoyo"] == 1
            assert temas[0]["critica"] == 1
        finally:
            os.unlink(db)

    def test_obtener_aprobaciones_no_requiere_columnas_eliminadas(self):
        """obtener_aprobaciones() funciona correctamente sin las columnas."""
        from dashboard.tema_aprobaciones import (
            guardar_aprobacion, obtener_aprobaciones
        )
        db = _crear_bd_vacia()
        try:
            guardar_aprobacion(db, "r3", "seguridad", texto="test",
                              emociones=["calma"])
            aps = obtener_aprobaciones(db)
            assert "r3" in aps
            assert "subtema_especifico" not in aps["r3"]
            assert "relevancia_al_post" not in aps["r3"]
        finally:
            os.unlink(db)

    def test_cargar_temas_aprobados_no_rompe(self):
        """cargar_temas_aprobados() en queries.py no falla con el esquema nuevo."""
        from dashboard.tema_aprobaciones import (
            guardar_aprobacion, asegurar_tabla
        )
        db = _crear_bd_vacia()
        try:
            guardar_aprobacion(db, "r4", "seguridad", texto="test",
                              emociones=["alegria"])
            import src.config as cfg_mod
            _cfg_orig = cfg_mod.Config.FACEBOOK_DB.__get__ if hasattr(cfg_mod.Config.FACEBOOK_DB, '__get__') else None

            import sys
            mod_path = os.path.join(os.path.dirname(__file__), "..", "analytics", "queries.py")
            if os.path.exists(mod_path):
                import importlib
                mod = importlib.import_module("analytics.queries")
                if hasattr(mod, "cargar_temas_aprobados"):
                    result = mod.cargar_temas_aprobados()
                    assert isinstance(result, list)
        finally:
            os.unlink(db)
