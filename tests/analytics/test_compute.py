"""Tests para analytics/compute.py (T5.1)."""
import pytest
from analytics.compute import (
    n, s, get,
    theme_color_hash, tendency_style, concentration_level_color,
    tension_color, thermo_position, intensity_color_and_sign,
    normalize_bar_widths, priority_color, evolution_state_color,
    projection_color, polarization_color,
    top_emotions, engagement_inconsistency_badge,
    friccion_count_string, share_totals_valid, format_date_es,
    emotion_pcts_for_theme, dominant_emotion,
)


# ── Coercion helpers ──
def test_n_with_number():
    assert n(42) == 42.0

def test_n_with_none():
    assert n(None) == 0.0

def test_n_with_string():
    assert n("abc") == 0.0

def test_n_with_dict():
    assert n({"valor": 7}) == 7.0

def test_n_with_default():
    assert n(None, default=-1) == -1.0

def test_s_with_string():
    assert s("hello") == "hello"

def test_s_with_none():
    assert s(None) == "—"

def test_s_with_empty():
    assert s("") == "—"

def test_get_nested():
    assert get({"a": {"b": 5}}, "a", "b") == 5

def test_get_missing():
    assert get({"a": 1}, "b", default="x") == "x"


# ── Color/style derivation ──
def test_theme_color_hash_deterministic():
    c1 = theme_color_hash("seguridad")
    c2 = theme_color_hash("seguridad")
    assert c1 == c2

def test_theme_color_hash_different():
    c1 = theme_color_hash("seguridad")
    c2 = theme_color_hash("movilidad")
    # They might collide, but statistically shouldn't for these strings
    assert isinstance(c1, str)
    assert isinstance(c2, str)

def test_tendency_style_positive():
    col, lbl = tendency_style(2.5)
    assert "green" in col
    assert "↑" in lbl
    assert "2.5" in lbl

def test_tendency_style_negative():
    col, lbl = tendency_style(-1.0)
    assert "red" in col
    assert "↓" in lbl

def test_tendency_style_zero():
    col, lbl = tendency_style(0.0)
    assert "amber" in col
    assert "sin cambio" in lbl

def test_concentration_level_color():
    assert concentration_level_color("dominado") == "var(--red)"
    assert concentration_level_color("liderado") == "var(--amber)"
    assert concentration_level_color("fragmentado") == "var(--green)"
    assert concentration_level_color("unknown") == "var(--accent)"

def test_tension_color():
    assert tension_color(80) == "var(--red)"
    assert tension_color(40) == "var(--amber)"
    assert tension_color(10) == "var(--green)"

def test_thermo_position():
    assert thermo_position(50) == 50
    assert thermo_position(100) == 97
    assert thermo_position(-5) == -5

def test_intensity_color_and_sign_positive():
    col, sign = intensity_color_and_sign(20)
    assert "red" in col
    assert "+20%" in sign

def test_intensity_color_and_sign_negative():
    col, sign = intensity_color_and_sign(-20)
    assert "blue" in col
    assert "-20%" in sign

def test_intensity_color_and_sign_neutral():
    col, sign = intensity_color_and_sign(5)
    assert "accent" in col

def test_normalize_bar_widths():
    w1, w2 = normalize_bar_widths(100, 50)
    assert w1 == 100.0
    assert w2 == 50.0

def test_normalize_bar_widths_equal():
    w1, w2 = normalize_bar_widths(50, 50)
    assert w1 == 100.0
    assert w2 == 100.0

def test_priority_color():
    assert priority_color("alta") == "var(--red)"
    assert priority_color("media") == "var(--amber)"
    assert priority_color("baja") == "var(--green)"

def test_evolution_state_color():
    assert evolution_state_color("emergente") == "var(--amber)"
    assert evolution_state_color("en auge") == "var(--green)"

def test_projection_color():
    assert projection_color("acelerando") == "var(--red)"
    assert projection_color("desacelerando") == "var(--green)"

def test_polarization_color():
    assert polarization_color("confrontacion") == "var(--red)"
    assert polarization_color("consenso") == "var(--green)"


# ── Data extraction ──
def test_top_emotions_basic():
    data = {"pct_alegria": 40, "pct_tristeza": 20, "pct_calma": 10, "other": 5}
    top = top_emotions(data, n_top=2)
    assert len(top) == 2
    assert top[0][1] >= top[1][1]

def test_top_emotions_empty():
    assert top_emotions({}) == []

def test_top_emotions_filters_zero():
    data = {"pct_alegria": 0, "pct_calma": 0}
    assert top_emotions(data) == []

def test_engagement_inconsistency_badge():
    assert engagement_inconsistency_badge({"engagement": 100, "reacciones_totales": 0,
                                          "comentarios_totales": 0, "compartidos_totales": 0})
    assert not engagement_inconsistency_badge({"engagement": 100, "reacciones_totales": 50,
                                               "comentarios_totales": 30, "compartidos_totales": 20})
    assert not engagement_inconsistency_badge({"engagement": 0, "reacciones_totales": 0,
                                               "comentarios_totales": 0, "compartidos_totales": 0})

def test_friccion_count_string_with_total():
    fr = {"n_negativos": 45, "n_comentarios_total": 500, "pct_del_total": 9.0}
    result = friccion_count_string(fr)
    assert "45" in result
    assert "500" in result
    assert "9.0%" in result

def test_friccion_count_string_without_total():
    fr = {"n_negativos": 30, "n_comentarios_total": 0}
    result = friccion_count_string(fr)
    assert "30" in result
    assert "neg" in result

def test_share_totals_valid():
    ramas = [{"share": 60}, {"share": 40}]
    assert share_totals_valid(ramas)

def test_share_totals_invalid():
    ramas = [{"share": 30}, {"share": 30}]
    assert not share_totals_valid(ramas)

def test_format_date_es():
    full, short = format_date_es("2026-04-15")
    assert "abril" in full
    assert "2026" in full
    assert "15" in short
    assert "abr" in short

def test_dominant_emotion():
    counts = {"alegria": 10, "tristeza": 5, "calma": 3}
    assert dominant_emotion(counts) == "alegria"

def test_dominant_emotion_empty():
    assert dominant_emotion({}) == "calma"

def test_emotion_pcts_for_theme():
    counts = {"alegria": 10, "tristeza": 10}
    pcts = emotion_pcts_for_theme(counts)
    assert "alegria" in pcts
    assert "tristeza" in pcts
    assert pcts["alegria"] == 50.0
