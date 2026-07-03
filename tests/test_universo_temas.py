"""Tests para el universo unico de calculo en Temas Emergentes (IA + manual).

Cubren:
- tema_clasificaciones_ia: asegurar_tabla, guardar/obtener clasificaciones
- tema_aprobaciones.agregar_por_tema_universo: prioridad manual sobre IA, exclusion no clasificados
- dash_inteligencia.sugerir_temas_pendientes_cacheado: persiste via guardar_clasificacion_ia
- dash_temas.render_temas_emergentes: usa cargar_temas_universo (no cargar_temas_aprobados)
"""
import os
import sys
import inspect
import tempfile
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

import pytest

from dashboard.tema_clasificaciones_ia import (
    asegurar_tabla as asegurar_tabla_ia,
    guardar_clasificacion_ia,
    obtener_clasificaciones_ia,
)
from dashboard.tema_aprobaciones import (
    agregar_por_tema_universo,
    resumen_cobertura_universo,
    guardar_aprobacion,
    obtener_aprobaciones,
)
from dashboard.dash_inteligencia import (
    sugerir_temas_pendientes_cacheado,
    cargar_temas_universo,
)
from dashboard.dash_temas import render_temas_emergentes


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestTemaClasificacionesIA:
    """Tests del nuevo modulo tema_clasificaciones_ia."""

    def test_asegurar_tabla_crea_tabla(self, db_path):
        asegurar_tabla_ia(db_path)
        conn = sqlite3.connect(db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tema_clasificaciones_ia'"
        ).fetchall()
        conn.close()
        assert len(tables) == 1

    def test_guardar_y_obtener_clasificacion(self, db_path):
        assert guardar_clasificacion_ia(
            db_path, "c1", "gobernanza", postura="critica",
            tono="sarcastico", confianza=0.8, texto="gran migajero"
        ) is True
        data = obtener_clasificaciones_ia(db_path)
        assert "c1" in data
        assert data["c1"]["tema"] == "gobernanza"
        assert data["c1"]["postura"] == "critica"
        assert data["c1"]["tono"] == "sarcastico"
        assert data["c1"]["confianza"] == 0.8
        assert data["c1"]["texto"] == "gran migajero"

    def test_guardar_descarta_si_falta_comment_id_o_tema(self, db_path):
        assert guardar_clasificacion_ia(db_path, "", "gobernanza") is False
        assert guardar_clasificacion_ia(db_path, "c1", "") is False
        assert guardar_clasificacion_ia(db_path, None, "gobernanza") is False
        assert guardar_clasificacion_ia(db_path, "c1", None) is False

    def test_obtener_vacio_si_no_hay_datos(self, db_path):
        data = obtener_clasificaciones_ia(db_path)
        assert data == {}


class TestAgregarPorTemaUniverso:
    """Tests de agregar_por_tema_universo: prioridad manual sobre IA, exclusion no clasificados."""

    def test_prioridad_manual_sobre_ia(self, db_path):
        # IA clasifica c1 como 'seguridad'
        guardar_clasificacion_ia(db_path, "c1", "seguridad", postura="neutral")
        # Manual aprueba c1 como 'gobernanza' (debe sobrescribir)
        guardar_aprobacion(db_path, "c1", "gobernanza", postura="critica", texto="reclamo")

        temas = agregar_por_tema_universo(db_path)
        por_cat = {t["categoria"]: t for t in temas}
        assert "gobernanza" in por_cat
        assert "seguridad" not in por_cat
        assert por_cat["gobernanza"]["critica"] == 1

    def test_excluye_comentarios_sin_clasificacion(self, db_path):
        # c1: solo IA
        guardar_clasificacion_ia(db_path, "c1", "salud")
        # c2: solo manual
        guardar_aprobacion(db_path, "c2", "educacion", postura="apoyo")
        # c3: sin nada (no debe aparecer en el conteo)

        temas = agregar_por_tema_universo(db_path)
        total = sum(t["doc_count"] for t in temas)
        assert total == 2  # solo c1 y c2

    def test_combinacion_ia_y_manual_diferentes_comentarios(self, db_path):
        # c1: solo IA -> seguridad
        guardar_clasificacion_ia(db_path, "c1", "seguridad", postura="critica")
        # c2: solo manual -> salud
        guardar_aprobacion(db_path, "c2", "salud", postura="apoyo", texto="buen hospital")

        temas = agregar_por_tema_universo(db_path)
        por_cat = {t["categoria"]: t for t in temas}
        assert por_cat["seguridad"]["doc_count"] == 1
        assert por_cat["seguridad"]["critica"] == 1
        assert por_cat["salud"]["doc_count"] == 1
        assert por_cat["salud"]["apoyo"] == 1

    def test_excluye_no_aplica(self, db_path):
        guardar_clasificacion_ia(db_path, "c1", "no_aplica")
        guardar_aprobacion(db_path, "c2", "no_aplica", postura="neutral")
        temas = agregar_por_tema_universo(db_path)
        assert len(temas) == 0

    def test_resumen_cobertura_universo(self, db_path):
        # 3 con IA (c0, c1, c2), 2 con manual (c0, c1 overlap), total 10 comentarios
        for i in range(3):
            guardar_clasificacion_ia(db_path, f"c{i}", "seguridad")
        for i in range(2):
            guardar_aprobacion(db_path, f"c{i}", "gobernanza", postura="critica")

        res = resumen_cobertura_universo(db_path, total_comentarios=10)
        # c0, c1 tienen ambos; c2 solo IA = 3 unicos
        assert res["clasificados"] == 3
        assert res["total_comentarios"] == 10
        assert res["sin_clasificar"] == 7


class TestSugerirTemasPersisteClasificacionIA:
    """Tests de que sugerir_temas_pendientes_cacheado persiste via guardar_clasificacion_ia."""

    def test_sugerir_persiste_en_tabla_ia(self, db_path, monkeypatch):
        # Mockear la BD para tener comentarios pendientes
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE fb_comments (comment_id TEXT PRIMARY KEY, message TEXT, created_time TEXT)")
        # c2 tiene fecha mas reciente, sale primero en ORDER BY created_time DESC
        conn.execute("INSERT INTO fb_comments VALUES ('c1', 'bache en la calle', '2024-01-01')")
        conn.execute("INSERT INTO fb_comments VALUES ('c2', 'inseguridad en el barrio', '2024-01-02')")
        conn.commit()
        conn.close()

        # Mockear clasificar_temas_lote para no llamar a la IA real
        from dashboard import topic_llm
        def mock_clasificar(textos, lote=None, ejemplos=None):
            # textos[0] es c2 (mas reciente), textos[1] es c1
            return [
                {"categoria": "seguridad", "tono": "literal", "postura": "critica", "confianza": 0.8},
                {"categoria": "obras_servicios", "tono": "literal", "postura": "critica", "confianza": 0.9},
            ][:len(textos)]
        monkeypatch.setattr(topic_llm, "clasificar_temas_lote", mock_clasificar)

        # Llamar a sugerir (usa cache vacio)
        pendientes = sugerir_temas_pendientes_cacheado(db_path, cache={}, limite=10)

        # Verificar que se guardaron en tabla IA
        data_ia = obtener_clasificaciones_ia(db_path)
        assert len(data_ia) == 2
        assert "c1" in data_ia and "c2" in data_ia
        # c2 (mas reciente) clasificado como seguridad, c1 como obras
        assert data_ia["c2"]["tema"] == "seguridad"
        assert data_ia["c1"]["tema"] == "obras_servicios"

        # Verificar que devuelve sugerencias correctas
        assert len(pendientes) == 2


class TestRenderTemasEmergentesUsaUniverso:
    """Test que render_temas_emergentes usa cargar_temas_universo (no cargar_temas_aprobados)."""

    def test_render_temas_emergentes_llama_cargar_temas_universo(self):
        source = inspect.getsource(render_temas_emergentes)
        assert "cargar_temas_universo" in source, (
            "render_temas_emergentes debe llamar a cargar_temas_universo"
        )
        assert "cargar_temas_aprobados" not in source, (
            "render_temas_emergentes NO debe llamar a cargar_temas_aprobados"
        )

    def test_render_temas_emergentes_texto_aclaracion_actualizado(self):
        source = inspect.getsource(render_temas_emergentes)
        # Debe mencionar IA + revision manual, NO solo "revisados a mano"
        assert "IA" in source or "clasificaci" in source.lower(), (
            "El texto de aclaracion debe reflejar que incluye clasificacion IA"
        )
        assert "revisados a mano" not in source.lower(), (
            "No debe decir solo 'revisados a mano' ahora que incluye IA"
        )

    def test_render_temas_emergentes_muestra_cobertura(self):
        source = inspect.getsource(render_temas_emergentes)
        assert "clasificados" in source.lower() or "cobertura" in source.lower(), (
            "Debe mostrar la cifra de cobertura (X de Y comentarios ya clasificados)"
        )