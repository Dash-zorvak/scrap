"""Tests para analytics/freshness.py (T8.1)."""
import json
import os
import pytest
from datetime import datetime, timezone, timedelta
from analytics.freshness import verificar_freshness


def test_fresco_reciente(tmp_path):
    f = tmp_path / "analysis.json"
    ahora = datetime.now(timezone.utc).isoformat()
    f.write_text(json.dumps({"meta": {"generado_en": ahora}}))
    r = verificar_freshness(str(f), max_dias=7)
    assert r["fresco"] is True
    assert r["dias_desde_generacion"] == 0


def test_obsoleto(tmp_path):
    f = tmp_path / "analysis.json"
    viejo = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    f.write_text(json.dumps({"meta": {"generado_en": viejo}}))
    r = verificar_freshness(str(f), max_dias=7)
    assert r["fresco"] is False
    assert r["dias_desde_generacion"] == 10


def test_no_existe():
    r = verificar_freshness("/no/existe.json")
    assert r["fresco"] is False
    assert r["mensaje"] == "No existe archivo de analisis."


def test_sin_generado_en(tmp_path):
    f = tmp_path / "analysis.json"
    f.write_text(json.dumps({"meta": {}}))
    r = verificar_freshness(str(f))
    assert r["fresco"] is False


def test_fecha_invalida(tmp_path):
    f = tmp_path / "analysis.json"
    f.write_text(json.dumps({"meta": {"generado_en": "no-es-fecha"}}))
    r = verificar_freshness(str(f))
    assert r["fresco"] is False
    assert "invalido" in r["mensaje"]


def test_archivo_corrupto(tmp_path):
    f = tmp_path / "analysis.json"
    f.write_text("no es json {{{")
    r = verificar_freshness(str(f))
    assert r["fresco"] is False
    assert "Error" in r["mensaje"]


def test_en_limite(tmp_path):
    f = tmp_path / "analysis.json"
    hace_7 = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    f.write_text(json.dumps({"meta": {"generado_en": hace_7}}))
    r = verificar_freshness(str(f), max_dias=7)
    assert r["fresco"] is True


def test_un_dia_despues_del_limite(tmp_path):
    f = tmp_path / "analysis.json"
    hace_8 = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    f.write_text(json.dumps({"meta": {"generado_en": hace_8}}))
    r = verificar_freshness(str(f), max_dias=7)
    assert r["fresco"] is False
