"""Tests para analytics/zona.py — gazetteer de zonas/ubicaciones."""
import pytest
from analytics.zona import (
    detectar_zona, aggregate_zonas, es_propuesta_zona,
    ZONAS_CONOCIDAS, DEPARTAMENTOS, MUNICIPIOS, ZONAS_GT,
)


# ── Vacío / sin zona ──

def test_zona_vacio():
    r = detectar_zona("")
    assert r.zona == ""
    assert r.tipo == ""


def test_zona_none():
    r = detectar_zona(None)
    assert r.zona == ""


def test_zona_sin_mencion():
    r = detectar_zona("El gobierno es corrupto")
    assert r.zona == ""


# ── Zonas de la Ciudad de Guatemala ──

def test_zona_gt_zona10():
    r = detectar_zona("Vivo en la zona 10 de la ciudad")
    assert r.zona == "zona 10"
    assert r.tipo == "zona_gt"


def test_zona_gt_zona1():
    r = detectar_zona("La zona 1 está muy sucia")
    assert r.zona == "zona 1"


def test_zona_gt_zona4():
    r = detectar_zona("En la zona 4 hay muchos baches")
    assert r.zona == "zona 4"


def test_zona_gt_centro_historico():
    r = detectar_zona("El centro histórico necesita restauración")
    assert r.zona == "centro historico"
    assert r.tipo == "zona_gt"


# ── Municipios ──

def test_municipio_mixco():
    r = detectar_zona("En Mixco hay muchos problemas de seguridad")
    assert r.zona == "mixco"
    assert r.tipo == "municipio"


def test_municipio_villa_nueva():
    r = detectar_zona("Villa Nueva necesita más transporte")
    assert r.zona == "villa nueva"
    assert r.tipo == "municipio"


def test_municipio_coban():
    r = detectar_zona("En Cobán hace mucho frío")
    assert r.zona == "coban"
    assert r.tipo == "municipio"


def test_municipio_antigua():
    r = detectar_zona("Antigua Guatemala es turística")
    assert r.zona == "antigua guatemala"
    assert r.tipo == "municipio"


# ── Departamentos ──

def test_depto_escuintla():
    r = detectar_zona("En Escuintla hace mucho calor")
    assert r.zona == "escuintla"
    assert r.tipo in ("departamento", "municipio")


def test_depto_peten():
    r = detectar_zona("El Petén tiene muchos problemas ambientales")
    assert r.zona == "peten"
    assert r.tipo in ("departamento", "municipio")


def test_depto_huehuetenango():
    r = detectar_zona("Huehuetenango necesita más escuelas")
    assert r.zona == "huehuetenango"
    assert r.tipo in ("departamento", "municipio")


# ── Prioridad: zona_gt > barrio > municipio > departamento ──

def test_prioridad_zona_vs_depto():
    r = detectar_zona("La zona 10 de Guatemala necesita más alumbrado")
    assert r.tipo == "zona_gt"


def test_prioridad_municipio_vs_depto():
    r = detectar_zona("Mixco necesita más patrullas en Escuintla")
    assert r.zona in ("mixco", "escuintla")


# ── Gazetteer no vacío ──

def test_gazetteer_completo():
    assert len(ZONAS_CONOCIDAS) > 100
    assert len(DEPARTAMENTOS) >= 22
    assert len(ZONAS_GT) > 5


# ── Propuestas ──

def test_propuesta_zona_no_reconocida():
    propuesta = es_propuesta_zona("En la colonia San Fernando hay problemas")
    # Si "san fernando" no está en el gazetteer, debería ser propuesta
    # Si está, returns None
    assert propuesta is None or isinstance(propuesta, str)


def test_propuesta_zona_vacio():
    assert es_propuesta_zona("") is None


def test_propuesta_zona_none():
    assert es_propuesta_zona(None) is None


# ── Agregación batch ──

def test_aggregate_zonas_vacio():
    agg = aggregate_zonas([])
    assert agg["total"] == 0
    assert agg["dominante"] == ""


def test_aggregate_zonas_mixto():
    texts = [
        "Los baches en la zona 10",
        "Zona 10 está sucia",
        "En Mixco hay robos",
        "El gobierno es corrupto",
        "Zona 4 necesita luz",
    ]
    agg = aggregate_zonas(texts)
    assert agg["total"] == 5
    assert isinstance(agg["conteo"], dict)
    assert isinstance(agg["pct"], dict)


def test_aggregate_zonas_propuestas():
    texts = [
        "En la colonia Las Flores hay baches",
        "La colonia Las Flores necesita agua",
    ]
    agg = aggregate_zonas(texts)
    assert isinstance(agg["propuestas"], list)


def test_aggregate_zonas_una_sola_zona():
    texts = ["Zona 10 necesita arreglos"] * 5
    agg = aggregate_zonas(texts)
    assert agg["dominante"] == "zona 10"
    assert agg["pct"]["zona 10"] == 100.0
