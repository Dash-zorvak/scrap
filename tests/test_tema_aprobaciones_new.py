"""Tests para tema_aprobaciones.py — schema, campos nuevos y agregación (Puntos 1-4)."""
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
    RELEVANCIAS_POST,
    RELEVANCIA_DEFAULT,
)


def _crear_bd_temp():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.close()
    return path


class TestSchemaMigration:
    def test_crea_tabla_con_nuevas_columnas(self):
        db = _crear_bd_temp()
        try:
            asegurar_tabla(db)
            conn = sqlite3.connect(db)
            cols = {r[1] for r in conn.execute("PRAGMA table_info(tema_aprobaciones)").fetchall()}
            conn.close()
            assert "subtema_especifico" in cols
            assert "intensidad_postura" in cols
            assert "emociones" in cols
            assert "relevancia_al_post" in cols
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

    def test_guarda_subtema_especifico(self):
        db = _crear_bd_temp()
        try:
            ok = guardar_aprobacion(
                db, "c3", "gobernanza", texto="test",
                subtema_especifico="Juan Carlos",
            )
            assert ok is True
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT subtema_especifico FROM tema_aprobaciones WHERE comment_id='c3'").fetchone()
            conn.close()
            assert row[0] == "Juan Carlos"
        finally:
            os.unlink(db)

    def test_guarda_intensidad_postura(self):
        db = _crear_bd_temp()
        try:
            ok = guardar_aprobacion(
                db, "c4", "seguridad", texto="test",
                postura="apoyo", intensidad_postura="fuerte",
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
                postura="neutral", intensidad_postura="fuerte",
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
                    postura="apoyo", intensidad_postura="extrema",
                )
        finally:
            os.unlink(db)

    def test_guarda_relevancia_al_post(self):
        db = _crear_bd_temp()
        try:
            ok = guardar_aprobacion(
                db, "c7", "seguridad", texto="test",
                relevancia_al_post="ruido_conversacional",
            )
            assert ok is True
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT relevancia_al_post FROM tema_aprobaciones WHERE comment_id='c7'").fetchone()
            conn.close()
            assert row[0] == "ruido_conversacional"
        finally:
            os.unlink(db)

    def test_relevancia_invalida_lanza_value_error(self):
        db = _crear_bd_temp()
        try:
            with pytest.raises(ValueError, match="Relevancia"):
                guardar_aprobacion(
                    db, "c8", "seguridad", texto="test",
                    relevancia_al_post="fuera_de_tema",
                )
        finally:
            os.unlink(db)

    def test_relevancia_default(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(db, "c9", "seguridad", texto="test")
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT relevancia_al_post FROM tema_aprobaciones WHERE comment_id='c9'").fetchone()
            conn.close()
            assert row[0] == RELEVANCIA_DEFAULT
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
                postura="apoyo",
                subtema_especifico="Alcaldía",
                intensidad_postura="fuerte",
                relevancia_al_post="tangencial_via_respuesta",
            )
            aps = obtener_aprobaciones(db)
            assert aps["o2"]["subtema_especifico"] == "Alcaldía"
            assert aps["o2"]["intensidad_postura"] == "fuerte"
            assert aps["o2"]["relevancia_al_post"] == "tangencial_via_respuesta"
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
    def test_excluye_ruido_conversacional(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "r1", "seguridad", texto="directo",
                relevancia_al_post="directo_al_post",
            )
            guardar_aprobacion(
                db, "r2", "seguridad", texto="ruido",
                relevancia_al_post="ruido_conversacional",
            )
            temas = agregar_por_tema(db)
            assert len(temas) == 1
            assert temas[0]["doc_count"] == 1
        finally:
            os.unlink(db)

    def test_saldo_ponderado(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "s1", "seguridad", texto="apoyo fuerte",
                postura="apoyo", intensidad_postura="fuerte",
            )
            guardar_aprobacion(
                db, "s2", "seguridad", texto="critica leve",
                postura="critica", intensidad_postura="leve",
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

    def test_entidades_en_agregacion(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "e1", "gobernanza", texto="test",
                subtema_especifico="Juan Carlos",
            )
            guardar_aprobacion(
                db, "e2", "gobernanza", texto="test2",
                subtema_especifico="Juan Carlos",
            )
            temas = agregar_por_tema(db)
            assert len(temas) == 1
            assert temas[0]["entidades"]["Juan Carlos"] == 2
        finally:
            os.unlink(db)

    def test_relevancia_excluida_no_aparece(self):
        db = _crear_bd_temp()
        try:
            guardar_aprobacion(
                db, "x1", "seguridad", texto="tangencial",
                relevancia_al_post="tangencial_via_respuesta",
            )
            temas = agregar_por_tema(db)
            # tangencial SÍ se cuenta (solo ruido se excluye)
            assert len(temas) == 1
            assert temas[0]["doc_count"] == 1
        finally:
            os.unlink(db)
