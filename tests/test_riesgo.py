"""Tests del Bloque III (riesgo y autenticidad)."""

import pandas as pd

from dashboard.dash_riesgo import (
    calcular_autenticidad,
    calcular_nivel_alerta,
    calcular_propagacion_24_48,
    agrupar_fricciones,
)


class TestAutenticidad:
    def test_organico(self):
        msgs = [
            "buen trabajo alcalde", "gracias por las calles",
            "excelente obra publica", "muy buena gestion",
            "felicidades al equipo",
        ]
        r = calcular_autenticidad(msgs)
        assert r is not None
        assert r["nivel"] == "organico"
        assert r["pct_sospechoso"] == 0.0

    def test_coordinado(self):
        msgs = ["fuera el alcalde corrupto"] * 8 + ["gracias por todo", "buena obra publica"]
        r = calcular_autenticidad(msgs)
        assert r["nivel"] == "coordinado"
        assert r["n_sospechoso"] == 8
        assert r["pct_sospechoso"] == 80.0

    def test_mixto(self):
        msgs = [
            "mensaje unico uno", "mensaje unico dos", "mensaje unico tres",
            "mensaje unico cuatro", "mensaje unico cinco", "mensaje unico seis",
            "mensaje unico siete", "mensaje unico ocho",
            "texto repetido aqui", "texto repetido aqui",
        ]
        r = calcular_autenticidad(msgs)
        assert r["nivel"] == "mixto"
        assert r["n_sospechoso"] == 2

    def test_vacio(self):
        assert calcular_autenticidad([]) is None
        assert calcular_autenticidad(None) is None
        assert calcular_autenticidad(["a", "b"]) is None


class TestNivelAlerta:
    def test_verde(self):
        r = calcular_nivel_alerta(pct_negativo=5, indice_enojo=0.02, balance_confrontacion=0.1)
        assert r["color"] == "verde"

    def test_amarillo(self):
        r = calcular_nivel_alerta(pct_negativo=30, indice_enojo=0.1, balance_confrontacion=0.3, n_fricciones=1)
        assert r["color"] == "amarillo"

    def test_rojo(self):
        r = calcular_nivel_alerta(pct_negativo=60, indice_enojo=0.5, balance_confrontacion=0.8, n_fricciones=3)
        assert r["color"] == "rojo"
        assert r["riesgo"] > 45


class TestPropagacion:
    def test_acelerando(self):
        fechas = pd.date_range("2026-06-01", periods=5, freq="D")
        df = pd.DataFrame({
            "created_time": fechas,
            "engagement_total": [10, 20, 30, 40, 50],
        })
        r = calcular_propagacion_24_48(df)
        assert r is not None
        assert r["tendencia"] == "acelerando"
        assert r["proy_24h"] == 60.0
        assert r["n_dias"] == 5

    def test_insuficiente(self):
        fechas = pd.date_range("2026-06-01", periods=2, freq="D")
        df = pd.DataFrame({"created_time": fechas, "engagement_total": [10, 20]})
        assert calcular_propagacion_24_48(df) is None

    def test_vacio(self):
        assert calcular_propagacion_24_48(pd.DataFrame()) is None


class TestFricciones:
    def test_agrupa_por_tema(self):
        df = pd.DataFrame({
            "message": ["calles destruidas", "baches por todos lados", "peor calle", "poca luz", "buen parque"],
            "sentiment": ["negativo", "negativo", "negativo", "negativo", "positivo"],
            "sentiment_score": [-0.5, -0.6, -0.4, -0.3, 0.5],
            "topic_category": ["obras", "obras", "obras", "servicios", "recreacion"],
        })
        r = agrupar_fricciones(df)
        assert len(r) == 2
        assert r[0]["tema"] == "obras"
        assert r[0]["n"] == 3
        assert r[0]["cita"] == "baches por todos lados"

    def test_incluye_por_score(self):
        df = pd.DataFrame({
            "message": ["esto no sirve"],
            "sentiment": ["neutral"],
            "sentiment_score": [-0.4],
            "topic_category": ["general"],
        })
        r = agrupar_fricciones(df)
        assert len(r) == 1
        assert r[0]["n"] == 1

    def test_sin_friccion(self):
        df = pd.DataFrame({
            "message": ["todo bien"],
            "sentiment": ["positivo"],
            "sentiment_score": [0.6],
            "topic_category": ["general"],
        })
        assert agrupar_fricciones(df) == []

    def test_vacio(self):
        assert agrupar_fricciones(pd.DataFrame()) == []
        assert agrupar_fricciones(None) == []
