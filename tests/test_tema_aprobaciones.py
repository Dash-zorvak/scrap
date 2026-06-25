import os
import sqlite3
import tempfile

import pytest

from dashboard.tema_aprobaciones import (
    asegurar_tabla,
    guardar_aprobacion,
    ids_aprobados,
    obtener_aprobaciones,
    agregar_por_tema,
    resumen_revision,
    ejemplos_few_shot,
    TABLA,
)


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestPersistencia:
    def test_asegurar_tabla_crea(self, db_path):
        asegurar_tabla(db_path)
        conn = sqlite3.connect(db_path)
        tablas = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        assert TABLA in tablas

    def test_guardar_y_leer(self, db_path):
        assert guardar_aprobacion(db_path, "c1", "seguridad", texto="hay robos") is True
        assert "c1" in ids_aprobados(db_path)
        ap = obtener_aprobaciones(db_path)
        assert ap["c1"]["tema"] == "seguridad"

    def test_remap_al_guardar(self, db_path):
        guardar_aprobacion(db_path, "c1", "obras_publicas", texto="baches")
        ap = obtener_aprobaciones(db_path)
        assert ap["c1"]["tema"] == "obras_servicios"

    def test_upsert_actualiza(self, db_path):
        guardar_aprobacion(db_path, "c1", "seguridad", texto="x")
        guardar_aprobacion(db_path, "c1", "salud", texto="y")
        ap = obtener_aprobaciones(db_path)
        assert len(ap) == 1
        assert ap["c1"]["tema"] == "salud"

    def test_invalidos(self, db_path):
        assert guardar_aprobacion(db_path, "", "salud") is False
        assert guardar_aprobacion(db_path, "c1", "") is False
        assert guardar_aprobacion(db_path, "c1", "tema_que_no_existe") is False


class TestAgregacion:
    def test_vacio(self, db_path):
        assert agregar_por_tema(db_path) == []

    def test_conteo_y_pct(self, db_path):
        guardar_aprobacion(db_path, "c1", "seguridad", texto="robos en la colonia")
        guardar_aprobacion(db_path, "c2", "seguridad", texto="mucha delincuencia")
        guardar_aprobacion(db_path, "c3", "salud", texto="falta medicina")
        guardar_aprobacion(db_path, "c4", "no_aplica", texto="jajaja")
        temas = agregar_por_tema(db_path)
        por = {t["categoria"]: t for t in temas}
        assert "no_aplica" not in por
        assert por["seguridad"]["doc_count"] == 2
        assert por["salud"]["doc_count"] == 1
        assert round(por["seguridad"]["pct"]) == 67
        assert temas[0]["categoria"] == "seguridad"


class TestResumen:
    def test_resumen(self, db_path):
        guardar_aprobacion(db_path, "c1", "seguridad", texto="a")
        guardar_aprobacion(db_path, "c2", "no_aplica", texto="b")
        r = resumen_revision(db_path, total_comentarios=10)
        assert r["aprobados"] == 1
        assert r["sin_tema"] == 1
        assert r["total_aprobaciones"] == 2
        assert r["pendientes"] == 8


class TestFewShot:
    def test_balanceado_y_formato(self, db_path):
        for i in range(5):
            guardar_aprobacion(db_path, f"s{i}", "seguridad", texto=f"robo numero {i}")
        for i in range(2):
            guardar_aprobacion(db_path, f"h{i}", "salud", texto=f"hospital {i}")
        ej = ejemplos_few_shot(db_path, por_tema=3, max_total=24)
        assert all(set(e.keys()) >= {"texto", "tema"} for e in ej)
        seg = [e for e in ej if e["tema"] == "seguridad"]
        sal = [e for e in ej if e["tema"] == "salud"]
        assert len(seg) == 3
        assert len(sal) == 2
