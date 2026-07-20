"""Tests para tema_aprobaciones.py — schema, campos y agregación."""
import json
import os
import sqlite3
import tempfile

import pytest

from dashboard.tema_aprobaciones import (
    asegurar_tabla,
    guardar_aprobacion,
    obtener_aprobaciones,
    agregar_por_tema,
    ids_aprobados,
    INTENSIDADES_POSTURA,
    INTENSIDAD_POSTURA_DEFAULT,
    derivar_postura,
)


def _crear_bd_temp():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.close()
    return path


class TestSchemaMigration:
    def test_crea_tabla_con_columnas(self):
        db = _crear_bd_temp()
        try:
            asegurar_tabla(db)
            conn = sqlite3.connect(db)
            cols = {r[1] for r in conn.execute("PRAGMA table_info(tema_aprobaciones)").fetchall()}
            conn.close()
            assert "intensidad_postura" in cols
            assert "emociones" in cols
            assert "subtema_especifico" not in cols
            assert "relevancia_al_post" not in cols
        finally:
            os.unlink(db)

    def test_migracion_idempotente(self):
        db = _crear_bd_temp()
        try:
            asegurar_tabla(db)
            asegurar_tabla(db)  # segunda llamada no debe fallar
            conn = sqlite3.connect(db)
            cols = {r[1] for r in conn.execute("PRAGMA table_info(tema_aprobaciones)").fetchall()}
            conn.close()
            assert "emociones" in cols
        finally:
            os.unlink(db)

    def test_elimina_columnas_obsoletas(self):
        """Si la tabla ya tiene subtema_especifico/relevancia_al_post, se eliminan."""
        db = _crear_bd_temp()
        try:
            conn = sqlite3.connect(db)
            conn.execute("""
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
                )
            """)
            conn.execute(
                "INSERT INTO tema_aprobaciones "
                "(comment_id, tema, texto, estado, fecha) "
                "VALUES ('old1', 'seguridad', 'test old', 'aprobado', '2026-01-01')"
            )
            conn.commit()
            conn.close()

            asegurar_tabla(db)

            conn = sqlite3.connect(db)
            cols = {r[1] for r in conn.execute("PRAGMA table_info(tema_aprobaciones)").fetchall()}
            assert "subtema_especifico" not in cols
            assert "relevancia_al_post" not in cols
            row = conn.execute("SELECT comment_id, tema FROM tema_aprobaciones WHERE comment_id='old1'").fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "old1"
        finally:
            os.unlink(db)


class TestDerivarPostura:
    def test_alegria_es_apoyo(self):
        assert derivar_postura("alegria") == "apoyo"

    def test_confianza_es_apoyo(self):
        assert derivar_postura("confianza") == "apoyo"

    def test_optimismo_es_neutral(self):
        """Optimismo es díada (anticipation+joy), familia 'diada' no está en
        la tabla VALENCIA_POSTURA directamente, se devuelve neutral."""
        assert derivar_postura("optimismo") == "neutral"

    def test_esperanza_es_apoyo(self):
        assert derivar_postura("esperanza") == "apoyo"

    def test_enojo_es_critica(self):
        assert derivar_postura("enojo") == "critica"

    def test_tristeza_es_critica(self):
        assert derivar_postura("tristeza") == "critica"

    def test_desprecio_es_critica(self):
        assert derivar_postura("desprecio") == "critica"

    def test_ansiedad_es_critica(self):
        assert derivar_postura("ansiedad") == "critica"

    def test_indignacion_es_critica(self):
        assert derivar_postura("indignacion") == "critica"

    def test_sorpresa_es_neutral(self):
        assert derivar_postura("sorpresa") == "neutral"

    def test_culpa_es_neutral(self):
        assert derivar_postura("culpa") == "neutral"

    def test_calma_es_neutral(self):
        assert derivar_postura("calma") == "neutral"

    def test_reclamo_es_neutral(self):
        assert derivar_postura("reclamo") == "neutral"

    def test_reconocimiento_es_neutral(self):
        assert derivar_postura("reconocimiento") == "neutral"

    def test_ironia_es_neutral(self):
        assert derivar_postura("ironia") == "neutral"

    def test_none_devuelve_neutral(self):
        assert derivar_postura(None) == "neutral"

    def test_string_vacio_devuelve_neutral(self):
        assert derivar_postura("") == "neutral"

    def test_panico_es_critica(self):
        """Panico pertenece a familia fear → critica."""
        assert derivar_postura("panico") == "critica"

    def test_euforia_es_apoyo(self):
        """Euforia pertenece a familia joy → apoyo."""
        assert derivar_postura("euforia") == "apoyo"


class TestGuardarAprobacion:
    def test_guarda_emociones_lista(self):
        db = _crear_bd_temp()
        try:
            ok = guardar_aprobacion(
                db, "c1", "seguridad", texto="test",
                emociones=["enojo", "indignacion"],
            )
            assert ok is True
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT emociones FROM tema_aprobaciones WHERE comment_id='c1'").fetchone()
            conn.close()
            assert row is not None
            parsed = json.loads(row[0])
            assert "enojo" in parsed
            assert "indignacion" in parsed
        finally:
            os.unlink(db)

    def test_guarda_emocion_legacy_envuelta_en_lista(self):
        db = _crear_bd_temp()
        try:
            ok = guardar_aprobacion(
                db, "c2", "seguridad", texto="test",
                emocion="alegria",
            )
            assert ok is True
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT emociones FROM tema_aprobaciones WHERE comment_id='c2'").fetchone()
            conn.close()
            parsed = json.loads(row[0])
            assert parsed == ["alegria"]
        finally:
            os.unlink(db)

    def test_postura_se_deriva_de_emocion(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "c3a", "seguridad", texto="test",
                emociones=["alegria"],
            )
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT postura FROM tema_aprobaciones WHERE comment_id='c3a'").fetchone()
            conn.close()
            assert row[0] == "apoyo"
        finally:
            os.unlink(db)

    def test_postura_critica_de_enojo(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "c3b", "seguridad", texto="test",
                emociones=["enojo"],
            )
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT postura FROM tema_aprobaciones WHERE comment_id='c3b'").fetchone()
            conn.close()
            assert row[0] == "critica"
        finally:
            os.unlink(db)

    def test_postura_parametro_se_ignora(self):
        """El parámetro postura se ignora siempre; se deriva de la emoción."""
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "c3c", "seguridad", texto="test",
                emociones=["alegria"],
                postura="critica",
            )
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT postura FROM tema_aprobaciones WHERE comment_id='c3c'").fetchone()
            conn.close()
            assert row[0] == "apoyo"
        finally:
            os.unlink(db)

    def test_guarda_intensidad_postura(self):
        db = _crear_bd_temp()
        try:
            ok = guardar_aprobacion(
                db, "c4", "seguridad", texto="test",
                emociones=["enojo"],
                intensidad_postura="fuerte",
            )
            assert ok is True
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT intensidad_postura FROM tema_aprobaciones WHERE comment_id='c4'").fetchone()
            conn.close()
            assert row[0] == "fuerte"
        finally:
            os.unlink(db)

    def test_neutral_fuerza_moderada(self):
        db = _crear_bd_temp()
        try:
            ok = guardar_aprobacion(
                db, "c5", "seguridad", texto="test",
                emociones=["calma"],
                intensidad_postura="fuerte",
            )
            assert ok is True
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT intensidad_postura FROM tema_aprobaciones WHERE comment_id='c5'").fetchone()
            conn.close()
            assert row[0] == "moderada"
        finally:
            os.unlink(db)

    def test_intensidad_invalida_lanza_value_error(self):
        db = _crear_bd_temp()
        try:
            with pytest.raises(ValueError, match="Intensidad"):
                guardar_aprobacion(
                    db, "c6", "seguridad", texto="test",
                    emociones=["enojo"],
                    intensidad_postura="extrema",
                )
        finally:
            os.unlink(db)


class TestObtenerAprobaciones:
    def test_devuelve_emociones_lista(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "o1", "seguridad", texto="test",
                emociones=["enojo", "indignacion"],
            )
            aps = obtener_aprobaciones(db)
            assert "o1" in aps
            assert aps["o1"]["emociones"] == ["enojo", "indignacion"]
        finally:
            os.unlink(db)

    def test_devuelve_campos_nuevos(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "o2", "seguridad", texto="test",
                emociones=["enojo"],
                intensidad_postura="fuerte",
            )
            aps = obtener_aprobaciones(db)
            assert aps["o2"]["intensidad_postura"] == "fuerte"
            assert aps["o2"]["postura"] == "critica"
        finally:
            os.unlink(db)

    def test_fila_legacy_emocion_singular(self):
        """Simula una fila legacy sin campo 'emociones' (JSON)."""
        db = _crear_bd_temp()
        try:
            asegurar_tabla(db)
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT INTO tema_aprobaciones "
                "(comment_id, tema, postura, emocion, texto, estado, fecha) "
                "VALUES ('legacy1', 'seguridad', 'apoyo', 'alegria', 'test', 'aprobado', '2026-01-01')"
            )
            conn.commit()
            conn.close()
            aps = obtener_aprobaciones(db)
            assert aps["legacy1"]["emociones"] == ["alegria"]
            assert aps["legacy1"]["emocion"] == "alegria"
        finally:
            os.unlink(db)


class TestAgregarPorTema:
    def test_saldo_ponderado(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "s1", "seguridad", texto="apoyo fuerte",
                emociones=["alegria"],
                intensidad_postura="fuerte",
            )
            guardar_aprobacion(
                db, "s2", "seguridad", texto="critica leve",
                emociones=["tristeza"],
                intensidad_postura="leve",
            )
            temas = agregar_por_tema(db)
            assert len(temas) == 1
            t = temas[0]
            assert t["saldo"] == 0  # 1 apoyo - 1 critica
            assert t["saldo_ponderado"] == 2.0  # 3 (fuerte) - 1 (leve)
        finally:
            os.unlink(db)

    def test_emociones_multi_conteo(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "m1", "seguridad", texto="test",
                emociones=["enojo", "indignacion"],
            )
            temas = agregar_por_tema(db)
            assert len(temas) == 1
            emo = temas[0]["emociones"]
            assert emo["enojo"]["count"] == 1
            assert emo["indignacion"]["count"] == 1
        finally:
            os.unlink(db)

    def test_no_contiene_entidades(self):
        """La agregación ya no incluye campo entidades."""
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "e1", "gobernanza", texto="test",
                emociones=["alegria"],
            )
            temas = agregar_por_tema(db)
            assert len(temas) == 1
            assert "entidades" not in temas[0]
        finally:
            os.unlink(db)
