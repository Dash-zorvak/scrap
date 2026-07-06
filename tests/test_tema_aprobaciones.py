import os
import sqlite3
import tempfile

import pandas as pd
import pytest

from dashboard.tema_aprobaciones import (
    _ids_comentarios_en_periodo,
    asegurar_tabla,
    guardar_aprobacion,
    ids_aprobados,
    obtener_aprobaciones,
    agregar_por_tema,
    agregar_por_tema_universo,
    resumen_revision,
    resumen_cobertura_universo,
    ejemplos_few_shot,
    TABLA,
)
from dashboard.tema_clasificaciones_ia import guardar_clasificacion_ia


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


@pytest.fixture
def db_con_datos_periodo():
    """Crea DB con fb_comments, fb_posts, fb_engagement para tests de período.

    - Comentario c1 -> post p1 (fb_posts: 2024-01-15)  → dentro de [2024-01-01, 2024-01-31]
    - Comentario c2 -> post p2 (fb_posts: 2024-03-10)  → fuera
    - Comentario c3 -> post p3 (sin fb_posts, pero fb_engagement: 2024-01-20) → dentro (fallback)
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE fb_comments (comment_id TEXT, post_id TEXT, message TEXT)")
    conn.execute("CREATE TABLE fb_posts (post_id TEXT, created_time TEXT)")
    conn.execute("CREATE TABLE fb_engagement (post_id TEXT, created_time TEXT)")
    conn.execute("INSERT INTO fb_comments VALUES ('c1', 'p1', 'msg 1')")
    conn.execute("INSERT INTO fb_comments VALUES ('c2', 'p2', 'msg 2')")
    conn.execute("INSERT INTO fb_comments VALUES ('c3', 'p3', 'msg 3')")
    conn.execute("INSERT INTO fb_posts VALUES ('p1', '2024-01-15')")
    conn.execute("INSERT INTO fb_posts VALUES ('p2', '2024-03-10')")
    conn.execute("INSERT INTO fb_engagement VALUES ('p3', '2024-01-20')")
    conn.commit()
    conn.close()
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestIdsComentariosEnPeriodo:
    def test_filtra_dentro_y_fuera(self, db_con_datos_periodo):
        ids = _ids_comentarios_en_periodo(
            db_con_datos_periodo, "2024-01-01", "2024-01-31"
        )
        assert "c1" in ids, "c1 (post p1, 2024-01-15) deberia estar dentro"
        assert "c2" not in ids, "c2 (post p2, 2024-03-10) deberia estar fuera"
        assert "c3" in ids, "c3 (post p3, fb_engagement 2024-01-20) deberia estar dentro por fallback"

    def test_fallback_fb_engagement(self, db_con_datos_periodo):
        """c3 no tiene fb_posts pero si fb_engagement: la fecha debe resolverse."""
        ids = _ids_comentarios_en_periodo(
            db_con_datos_periodo, "2024-01-01", "2024-01-31"
        )
        assert "c3" in ids, "c3 debe resolverse desde fb_engagement"

    def test_sin_fb_posts_usa_fb_engagement(self):
        """fb_posts no existe, solo fb_engagement debe bastar."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE fb_comments (comment_id TEXT, post_id TEXT)")
        conn.execute("CREATE TABLE fb_engagement (post_id TEXT, created_time TEXT)")
        conn.execute("INSERT INTO fb_comments VALUES ('c1', 'p1')")
        conn.execute("INSERT INTO fb_engagement VALUES ('p1', '2024-01-15')")
        conn.commit()
        conn.close()
        try:
            ids = _ids_comentarios_en_periodo(path, "2024-01-01", "2024-01-31")
            assert "c1" in ids
        finally:
            os.unlink(path)

    def test_tablas_vacias_devuelve_vacio(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE fb_comments (comment_id TEXT, post_id TEXT)")
        conn.commit()
        conn.close()
        try:
            ids = _ids_comentarios_en_periodo(path, "2024-01-01", "2024-01-31")
            assert ids == set()
        finally:
            os.unlink(path)


@pytest.fixture
def db_con_clasificaciones_periodo():
    """Crea DB con clasificaciones IA y aprobaciones ligadas a posts dentro/fuera.

    - IA clasifica c1 (p1, dentro) y c2 (p2, fuera).
    - Aprobacion manual sobrescribe c1 con otro tema.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE fb_comments (comment_id TEXT, post_id TEXT, message TEXT)")
    conn.execute("CREATE TABLE fb_posts (post_id TEXT, created_time TEXT)")
    conn.execute("INSERT INTO fb_comments VALUES ('c1', 'p1', 'msg1')")
    conn.execute("INSERT INTO fb_comments VALUES ('c2', 'p2', 'msg2')")
    conn.execute("INSERT INTO fb_posts VALUES ('p1', '2024-01-15')")
    conn.execute("INSERT INTO fb_posts VALUES ('p2', '2024-03-10')")
    conn.commit()
    conn.close()
    guardar_clasificacion_ia(path, "c1", "seguridad", postura="apoyo", texto="msg1")
    guardar_clasificacion_ia(path, "c2", "salud", postura="critica", texto="msg2")
    guardar_aprobacion(path, "c1", "obras_servicios", texto="msg1 override", postura="neutral")
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestAgregarPorTemaUniversoPeriodo:
    def test_solo_dentro_del_periodo(self, db_con_clasificaciones_periodo):
        temas = agregar_por_tema_universo(
            db_con_clasificaciones_periodo, ini="2024-01-01", fin="2024-01-31"
        )
        cats = {t["categoria"] for t in temas}
        assert "obras_servicios" in cats, "c1 aprobado dentro del periodo"
        assert "salud" not in cats, "c2 fuera del periodo no debe aparecer"

    def test_sin_ini_fin_devuelve_completo(self, db_con_clasificaciones_periodo):
        temas = agregar_por_tema_universo(db_con_clasificaciones_periodo)
        cats = {t["categoria"] for t in temas}
        assert "obras_servicios" in cats, "c1 debe aparecer"
        assert "salud" in cats, "c2 debe aparecer sin filtro"


class TestResumenCoberturaPeriodo:
    def test_clasificados_solo_dentro(self, db_con_clasificaciones_periodo):
        cov = resumen_cobertura_universo(
            db_con_clasificaciones_periodo, total_comentarios=10,
            ini="2024-01-01", fin="2024-01-31"
        )
        # c1 esta dentro, c2 fuera => 1 clasificado
        assert cov["clasificados"] == 1

    def test_sin_ini_fin_cuenta_todos(self, db_con_clasificaciones_periodo):
        cov = resumen_cobertura_universo(
            db_con_clasificaciones_periodo, total_comentarios=10
        )
        assert cov["clasificados"] == 2


class TestResumenRevisionPeriodo:
    def test_solo_dentro_del_periodo(self, db_con_clasificaciones_periodo):
        res = resumen_revision(
            db_con_clasificaciones_periodo, total_comentarios=10,
            ini="2024-01-01", fin="2024-01-31"
        )
        # Solo c1 aprobado dentro del periodo
        assert res["aprobados"] == 1
        assert res["total_aprobaciones"] == 1

    def test_sin_ini_fin_cuenta_todos(self, db_con_clasificaciones_periodo):
        guardar_aprobacion(db_con_clasificaciones_periodo, "c2", "no_aplica", texto="fuera")
        res = resumen_revision(
            db_con_clasificaciones_periodo, total_comentarios=10
        )
        assert res["aprobados"] == 1  # c1 = obras_servicios
        assert res["sin_tema"] == 1  # c2 = no_aplica
        assert res["total_aprobaciones"] == 2  # c1 + c2


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
