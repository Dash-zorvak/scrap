"""Tests de la postura (apoyo/critica/neutral) por mencion de tema.

Cubren:
- normalizacion / etiqueta de postura en la taxonomia.
- el parseo de la respuesta del LLM incluye 'postura' y una critica sobre un
  asunto NO se manda a 'no_aplica' solo por ser critica.
- la persistencia guarda y devuelve la postura, con migracion de tablas viejas.
- agregar_por_tema divide cada tema en apoyo / critica / neutral.
"""
import json
import os
import sqlite3
import tempfile

import pytest

from dashboard.tema_taxonomia import (
    POSTURAS_VALIDAS,
    etiqueta_postura,
    normalizar_postura,
)
from dashboard.tema_aprobaciones import (
    asegurar_tabla,
    guardar_aprobacion,
    obtener_aprobaciones,
    agregar_por_tema,
    TABLA,
)
from dashboard.topic_llm import _parsear_respuesta


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestNormalizarPostura:
    def test_canonicas(self):
        assert normalizar_postura("apoyo") == "apoyo"
        assert normalizar_postura("critica") == "critica"
        assert normalizar_postura("neutral") == "neutral"

    def test_sinonimos(self):
        assert normalizar_postura("positivo") == "apoyo"
        assert normalizar_postura("negativo") == "critica"
        assert normalizar_postura("queja") == "critica"
        assert normalizar_postura("NEUTRO") == "neutral"

    def test_desconocido_y_vacio_caen_a_neutral(self):
        assert normalizar_postura(None) == "neutral"
        assert normalizar_postura("") == "neutral"
        assert normalizar_postura("loquesea") == "neutral"

    def test_etiqueta(self):
        assert etiqueta_postura("critica") == "Crítica"
        assert etiqueta_postura("xyz") == "Neutral"
        assert POSTURAS_VALIDAS == {"apoyo", "critica", "neutral"}


class TestParseoPostura:
    def test_parsea_postura(self):
        raw = json.dumps({"resultados": [
            {"categoria": "gobernanza", "tono": "sarcastico",
             "postura": "critica", "confianza": 0.8},
        ]})
        out = _parsear_respuesta(raw, ["x"])
        assert out[0]["categoria"] == "gobernanza"
        assert out[0]["postura"] == "critica"

    def test_postura_faltante_es_neutral(self):
        raw = json.dumps({"resultados": [
            {"categoria": "salud", "tono": "literal", "confianza": 0.7},
        ]})
        out = _parsear_respuesta(raw, ["x"])
        assert out[0]["postura"] == "neutral"

    def test_critica_conserva_tema(self):
        # Una critica sobre un asunto NO se degrada a no_aplica por ser critica.
        raw = json.dumps({"resultados": [
            {"categoria": "gobernanza", "tono": "literal",
             "postura": "critica", "confianza": 0.9},
        ]})
        out = _parsear_respuesta(raw, ["gran migajero"])
        assert out[0]["categoria"] == "gobernanza"
        assert out[0]["postura"] == "critica"


class TestPersistenciaPostura:
    def test_guarda_y_lee_postura(self, db_path):
        assert guardar_aprobacion(
            db_path, "c1", "gobernanza", texto="reclamo", postura="critica"
        ) is True
        ap = obtener_aprobaciones(db_path)
        assert ap["c1"]["postura"] == "critica"

    def test_postura_default_neutral(self, db_path):
        guardar_aprobacion(db_path, "c1", "salud", texto="hospital")
        ap = obtener_aprobaciones(db_path)
        assert ap["c1"]["postura"] == "neutral"

    def test_migracion_tabla_vieja(self, db_path):
        # Tabla SIN columna postura (version anterior): asegurar_tabla la migra.
        conn = sqlite3.connect(db_path)
        conn.execute(
            f"CREATE TABLE {TABLA} ("
            "comment_id TEXT PRIMARY KEY, tema TEXT NOT NULL, tema_sugerido TEXT, "
            "tono TEXT, confianza REAL, texto TEXT, "
            "estado TEXT DEFAULT 'aprobado', fecha TEXT)"
        )
        conn.execute(
            f"INSERT INTO {TABLA} (comment_id, tema, estado) "
            "VALUES ('c1', 'salud', 'aprobado')"
        )
        conn.commit()
        conn.close()

        asegurar_tabla(db_path)

        conn = sqlite3.connect(db_path)
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLA})").fetchall()]
        conn.close()
        assert "postura" in cols
        ap = obtener_aprobaciones(db_path)
        assert ap["c1"]["postura"] == "neutral"


class TestAgregacionPostura:
    def test_divide_apoyo_critica_neutral(self, db_path):
        guardar_aprobacion(db_path, "c1", "gobernanza", texto="muy buena gestion", postura="apoyo")
        guardar_aprobacion(db_path, "c2", "gobernanza", texto="gran migajero", postura="critica")
        guardar_aprobacion(db_path, "c3", "gobernanza", texto="cuando rinden cuentas", postura="neutral")
        guardar_aprobacion(db_path, "c4", "gobernanza", texto="otra critica mas", postura="critica")
        temas = agregar_por_tema(db_path)
        gob = {t["categoria"]: t for t in temas}["gobernanza"]
        assert gob["doc_count"] == 4
        assert gob["apoyo"] == 1
        assert gob["critica"] == 2
        assert gob["neutral"] == 1
        assert gob["saldo"] == -1
        assert round(gob["pct_critica"]) == 50

    def test_compat_doc_count_y_pct(self, db_path):
        guardar_aprobacion(db_path, "c1", "seguridad", texto="robos", postura="critica")
        guardar_aprobacion(db_path, "c2", "salud", texto="medicina", postura="apoyo")
        temas = agregar_por_tema(db_path)
        por = {t["categoria"]: t for t in temas}
        assert por["seguridad"]["doc_count"] == 1
        assert por["seguridad"]["critica"] == 1
        assert "pct" in por["seguridad"]
