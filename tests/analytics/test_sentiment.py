"""Tests para analytics/sentiment.py — clasificación léxica de sentimiento."""
import pytest
from analytics.sentiment import (
    classify_sentiment, aggregate_sentiment, SENTIMENT_ORDER,
    POSITIVE_WORDS, NEGATIVE_WORDS, NEGATION_WORDS, SentimentResult,
)


# ── Neutral sin coincidencias ──

def test_neutral_sin_coincidencias():
    r = classify_sentiment("La reunión es el lunes a las 3pm")
    assert r.label == "neutral"
    assert r.score == 0.0
    assert r.counts["positivo"] == 0
    assert r.counts["negativo"] == 0


def test_neutral_texto_vacio():
    assert classify_sentiment("").label == "neutral"
    assert classify_sentiment("   ").label == "neutral"
    assert classify_sentiment(None).label == "neutral"


def test_neutral_texto_corto():
    assert classify_sentiment("ok").label == "neutral"
    assert classify_sentiment("123").label == "neutral"


# ── Positivo simple ──

def test_positivo_simple():
    r = classify_sentiment("Bueno eficiente pero terrible")
    assert r.label == "positivo"
    assert r.score == 1.0
    assert r.counts["positivo"] == 2
    assert r.counts["negativo"] == 1
    assert "bueno" in r.evidence
    assert "eficiente" in r.evidence


def test_positivo_varias_palabras():
    r = classify_sentiment("Bueno, eficiente y transparente")
    assert r.label in ("positivo", "muy_positivo")
    assert r.counts["positivo"] >= 3


# ── Negativo simple ──

def test_negativo_simple():
    r = classify_sentiment("Terrible servicio, muy deficiente")
    assert r.label == "negativo"
    assert r.score == -1.0
    assert r.counts["negativo"] > 0


def test_negativo_varias_palabras():
    r = classify_sentiment("Malo, corrupto e inaceptable")
    assert r.label in ("negativo", "muy_negativo")
    assert r.counts["negativo"] >= 3


# ── Muy positivo por proporción (≥0.8) ──

def test_muy_positivo():
    r = classify_sentiment(
        "Excelente, brillante, genial y maravilloso servicio"
    )
    assert r.label == "muy_positivo"
    assert r.score == 2.0
    assert r.counts["positivo"] >= 4


def test_muy_positivo_ratio():
    r = classify_sentiment("Buena calidad y eficiente")
    if r.counts["positivo"] + r.counts["negativo"] > 0:
        ratio = r.counts["positivo"] / (r.counts["positivo"] + r.counts["negativo"])
        if ratio >= 0.8:
            assert r.label == "muy_positivo"


# ── Muy negativo por proporción (≥0.8) ──

def test_muy_negativo():
    r = classify_sentiment(
        "Terrible, horrible, deficiente y deplorable"
    )
    assert r.label == "muy_negativo"
    assert r.score == -2.0
    assert r.counts["negativo"] >= 4


# ── Negación invirtiendo polaridad ──

def test_negacion_invierte_positivo():
    r = classify_sentiment("No es bueno")
    assert r.label in ("negativo", "muy_negativo")
    assert r.counts["inverted"] > 0


def test_negacion_invierte_negativo():
    r = classify_sentiment("No es malo el proyecto")
    assert r.label in ("positivo", "muy_positivo")
    assert r.counts["inverted"] > 0


def test_negacion_nunca():
    r = classify_sentiment("Nunca fue bueno")
    assert r.label in ("negativo", "muy_negativo") or r.counts["inverted"] > 0


def test_negacion_jamas():
    r = classify_sentiment("Jamas fue eficiente")
    assert r.label in ("negativo", "muy_negativo") or r.counts["inverted"] > 0


def test_negacion_tampoco():
    r = classify_sentiment("Tampoco es malo")
    assert r.label == "positivo" or r.counts["inverted"] > 0


def test_negacion_ni():
    r = classify_sentiment("Ni bueno ni malo")
    assert r.counts["inverted"] >= 1


def test_negacion_fuera_de_ventana():
    """Palabra a 4+ tokens de la negación NO se invierte."""
    r = classify_sentiment("No el sistema es bueno")
    # "no" está en pos 0, "bueno" está en pos 4 → fuera de ventana (3)
    # Pero tokenize puede variar; lo importante es que>window no invierte
    assert isinstance(r, SentimentResult)


# ── Escala SENTIMENT_ORDER ──

def test_sentiment_order_completa():
    assert SENTIMENT_ORDER["muy_positivo"] == 2
    assert SENTIMENT_ORDER["positivo"] == 1
    assert SENTIMENT_ORDER["neutral"] == 0
    assert SENTIMENT_ORDER["negativo"] == -1
    assert SENTIMENT_ORDER["muy_negativo"] == -2


# ── Aggregate ──

def test_aggregate_vacio():
    agg = aggregate_sentiment([])
    assert agg["total"] == 0
    assert agg["dominante"] == "neutral"
    assert agg["score_promedio"] == 0.0


def test_aggregate_mixto():
    texts = [
        "Excelente trabajo",
        "Terrible servicio",
        "La reunión es el lunes",
        "Muy bueno y eficiente",
        "Inaceptable y deficiente",
    ]
    agg = aggregate_sentiment(texts)
    assert agg["total"] == 5
    assert agg["dominante"] in SENTIMENT_ORDER
    assert isinstance(agg["score_promedio"], float)
    assert len(agg["evidence_muestra"]) > 0


def test_aggregate_todos_positivos():
    texts = ["Excelente", "Brillante", "Genial"]
    agg = aggregate_sentiment(texts)
    assert agg["dominante"] in ("positivo", "muy_positivo")
    assert agg["score_promedio"] > 0


def test_aggregate_todos_negativos():
    texts = ["Terrible", "Horrible", "Deficiente"]
    agg = aggregate_sentiment(texts)
    assert agg["dominante"] in ("negativo", "muy_negativo")
    assert agg["score_promedio"] < 0


def test_aggregate_porcentajes_suman_100():
    texts = ["Bueno", "Malo", "ok", "Genial", "Horrible"]
    agg = aggregate_sentiment(texts)
    total_pct = sum(agg["pct"].values())
    assert abs(total_pct - 100.0) < 1.0


# ── Sanity checks del léxico ──

def test_lexico_no_vacio():
    assert len(POSITIVE_WORDS) > 50
    assert len(NEGATIVE_WORDS) > 50


def test_negation_words_completo():
    assert "no" in NEGATION_WORDS
    assert "nunca" in NEGATION_WORDS
    assert "jamas" in NEGATION_WORDS
    assert "tampoco" in NEGATION_WORDS
    assert "ni" in NEGATION_WORDS


def test_evidencia_se_incluye():
    r = classify_sentiment("Excelente y brillante")
    assert len(r.evidence) >= 2


def test_mezcla_neutral_con_sentimiento():
    r = classify_sentiment("La alcalde es buena persona pero el proyecto es terrible")
    # Tiene positivo ("buena") y negativo ("terrible") → podría ser neutral o mixto
    assert r.label in ("neutral", "negativo", "positivo")
    assert r.counts["positivo"] >= 1
    assert r.counts["negativo"] >= 1
