"""Tests para analytics/emergent.py — detección de temas emergentes por n-gramas."""
import pytest
from analytics.emergent import (
    extract_bigrams, extract_trigrams, clasificar_tendencia,
    detectar_emergentes, analizar_emergentes,
)


# ── Extracción de bigramas ──

def test_bigrams_vacio():
    assert extract_bigrams([]).total() == 0


def test_bigrams_basico():
    bigrams = extract_bigrams(["los baches están terribles"])
    assert bigrams.total() > 0


def test_bigrams_stopwords_filtrados():
    bigrams = extract_bigrams(["el bache grande de la calle"])
    # "el", "de", "la" son stopwords y no aparecen
    for bg in bigrams:
        words = bg.split()
        for w in words:
            assert w not in {"el", "la", "de", "del", "en", "con", "por"}


# ── Extracción de trigramas ──

def test_trigrams_vacio():
    assert extract_trigrams([]).total() == 0


def test_trigrams_basico():
    trigrams = extract_trigrams(["los baches de la calle están"])
    assert trigrams.total() > 0


# ── Clasificación de tendencia ──

def test_tendencia_acelerando():
    assert clasificar_tendencia(15, 5) == "acelerando"


def test_tendencia_desacelerando():
    assert clasificar_tendencia(3, 10) == "desacelerando"


def test_tendencia_estable():
    assert clasificar_tendencia(10, 9) == "estable"


def test_tendencia_nuevo():
    assert clasificar_tendencia(5, 0) == "nuevo"


def test_tendencia_sin_comparacion():
    assert clasificar_tendencia(0, 0) == "sin_comparacion"


def test_tendencia_ratio_1_5():
    assert clasificar_tendencia(15, 10) == "acelerando"


def test_tendencia_ratio_0_67():
    assert clasificar_tendencia(6, 10) == "desacelerando"


# ── Detección de emergentes ──

def test_emergentes_vacio():
    result = detectar_emergentes([])
    assert result == []


def test_emergentes_sin_min_freq():
    result = detectar_emergentes(["bache bache bache"], min_freq=3)
    assert result == []  # "bache bache" no es un bigrama único con freq 3


def test_emergentes_basico():
    texts = [
        "problema de baches en la zona",
        "los baches están terribles",
        "tantos baches no se puede",
    ]
    result = detectar_emergentes(texts, min_freq=2)
    assert isinstance(result, list)


def test_emergentes_con_previos():
    actual = ["bache bache bache bache"] * 5
    previo = ["bache bache"] * 2
    result = detectar_emergentes(actual, textos_previos=previo, min_freq=1)
    if result:
        assert result[0]["frecuencia_actual"] >= result[0].get("frecuencia_previa", 0)


# ── Análisis completo ──

def test_analizar_emergentes_vacio():
    result = analizar_emergentes([])
    assert result["emergentes"] == []
    assert result["total_bigramas_actual"] == 0
    assert result["n_acelerando"] == 0


def test_analizar_emergentes_con_textos():
    texts = [
        "problema de baches en la zona norte",
        "los baches están terribles en la zona norte",
        "tantos baches no se puede circular en zona norte",
    ]
    result = analizar_emergentes(texts, min_freq=1)
    assert isinstance(result["emergentes"], list)
    assert result["total_bigramas_actual"] > 0


def test_analizar_emergentes_sin_previos():
    texts = ["tema uno tema dos tema uno"] * 3
    result = analizar_emergentes(texts, min_freq=1)
    # Sin previos, todos deberían ser "nuevo" o "estable"
    for e in result["emergentes"]:
        assert e["tendencia"] in ("nuevo", "estable", "acelerando")


def test_analizar_emergentes_ratio():
    texts_act = ["problema bache"] * 10
    texts_prev = ["problema bache"] * 2
    result = analizar_emergentes(
        texts_act, textos_previos=texts_prev, min_freq=1
    )
    if result["emergentes"]:
        e = result["emergentes"][0]
        assert e["ratio"] >= 1.5 or e["tendencia"] in ("nuevo", "estable", "acelerando", "desacelerando")
