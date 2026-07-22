"""Tests para analytics/evidence.py."""
import pytest
from unittest.mock import patch, MagicMock


def test_resolver_evidencia_tema_vacia():
    """Sin evidencia retorna lista vacia."""
    from analytics.evidence import resolver_evidencia_tema
    result = resolver_evidencia_tema("seguridad", {})
    assert result == []


def test_resolver_evidencia_tema_ids_a_urls():
    """Resuelve post_ids a URLs usando queries de referencia."""
    from analytics.evidence import resolver_evidencia_tema

    mock_rows = [
        {"post_id": "p1", "post_url": "https://fb.com/post1"},
        {"post_id": "p2", "post_url": "https://fb.com/post2"},
    ]

    with patch("analytics.evidence.get_fb_references_by_ids", return_value=mock_rows):
        with patch("analytics.evidence.get_tk_references_by_ids", return_value=[]):
            result = resolver_evidencia_tema(
                "seguridad",
                {"seguridad": ["p1", "p2"]},
            )

    assert "https://fb.com/post1" in result
    assert "https://fb.com/post2" in result
    assert len(result) == 2


def test_resolver_evidencia_tema_sin_duplicados():
    """No duplica URLs aunque el mismo post_id aparezca varias veces."""
    from analytics.evidence import resolver_evidencia_tema

    mock_rows = [
        {"post_id": "p1", "post_url": "https://fb.com/post1"},
    ]

    with patch("analytics.evidence.get_fb_references_by_ids", return_value=mock_rows):
        with patch("analytics.evidence.get_tk_references_by_ids", return_value=[]):
            result = resolver_evidencia_tema(
                "seguridad",
                {"seguridad": ["p1", "p1", "p1"]},
            )

    assert len(result) == 1


def test_resolver_evidencia_emocion():
    """Resuelve post_ids de emocion a URLs."""
    from analytics.evidence import resolver_evidencia_emocion

    mock_rows = [
        {"post_id": "e1", "post_url": "https://fb.com/emo1"},
    ]

    with patch("analytics.evidence.get_fb_references_by_ids", return_value=mock_rows):
        with patch("analytics.evidence.get_tk_references_by_ids", return_value=[]):
            result = resolver_evidencia_emocion(
                "enojo",
                {"enojo": ["e1"]},
            )

    assert "https://fb.com/emo1" in result


def test_resolver_evidencia_friccion_combina_fuentes():
    """Friccion busca post_ids del tema en por_tema."""
    from analytics.evidence import resolver_evidencia_friccion

    evidencia = {
        "por_tema": {"seguridad": ["p1", "p2"]},
        "por_emocion": {"enojo": ["p3"]},
    }

    mock_fb = [
        {"post_id": "p1", "post_url": "https://fb.com/p1"},
        {"post_id": "p2", "post_url": "https://fb.com/p2"},
    ]

    with patch("analytics.evidence.get_fb_references_by_ids", return_value=mock_fb):
        with patch("analytics.evidence.get_tk_references_by_ids", return_value=[]):
            result = resolver_evidencia_friccion("seguridad", evidencia)

    assert len(result) == 2


def test_resolver_evidencia_alertas():
    """Extrae enlaces de alertas de Cambridge."""
    from analytics.evidence import resolver_evidencia_alertas

    alertas = [
        {"tipo": "ICI", "descripcion": "Alto", "enlaces_referencia": ["https://a.com"]},
        {"tipo": "SDI", "descripcion": "Medio", "enlaces_referencia": ["https://b.com"]},
    ]

    result = resolver_evidencia_alertas(alertas, {})
    assert "https://a.com" in result
    assert "https://b.com" in result


def test_resolver_evidencia_alertas_sin_duplicados():
    """No duplica URLs de alertas."""
    from analytics.evidence import resolver_evidencia_alertas

    alertas = [
        {"tipo": "ICI", "descripcion": "Alto", "enlaces_referencia": ["https://a.com"]},
        {"tipo": "SDI", "descripcion": "Medio", "enlaces_referencia": ["https://a.com"]},
    ]

    result = resolver_evidencia_alertas(alertas, {})
    assert len(result) == 1


def test_resolver_ids_a_urls_tiktok():
    """Resuelve IDs de TikTok a URLs."""
    from analytics.evidence import _resolver_ids_a_urls

    mock_tk = [
        {"post_id": "tk1", "post_url": "https://tiktok.com/video1"},
    ]

    with patch("analytics.evidence.get_fb_references_by_ids", return_value=[]):
        with patch("analytics.evidence.get_tk_references_by_ids", return_value=mock_tk):
            result = _resolver_ids_a_urls(["tk1"])

    assert "https://tiktok.com/video1" in result


def test_resolver_ids_a_urls_fb_fallback():
    """Fallback a fb_posts recientes cuando get_fb_references_by_ids no encuentra."""
    from analytics.evidence import _resolver_ids_a_urls

    # No encuentra en las queries de referencia
    with patch("analytics.evidence.get_fb_references_by_ids", return_value=[]):
        with patch("analytics.evidence.get_tk_references_by_ids", return_value=[]):
            # Fallback a fb_posts recientes
            with patch("analytics.evidence._obtener_fb_recent_references",
                       return_value={"p1": "https://fb.com/recent1"}):
                result = _resolver_ids_a_urls(["p1"])

    assert "https://fb.com/recent1" in result


def test_resolver_evidencia_voz_sin_datos():
    """Voz sin posts en DB retorna lista vacia (no hardcoded)."""
    from analytics.evidence import resolver_evidencia_voz

    with patch("analytics.evidence.get_fb_post_urls_by_pagina", return_value=[]):
        with patch("analytics.evidence.get_tk_post_urls_by_cuenta", return_value=[]):
            result = resolver_evidencia_voz("Alcaldia", {})

    assert result == []


def test_resolver_evidencia_voz_retorna_urls_fb():
    """Voz con posts en FB retorna URLs reales."""
    from analytics.evidence import resolver_evidencia_voz

    with patch("analytics.evidence.get_fb_post_urls_by_pagina",
               return_value=["https://fb.com/post1", "https://fb.com/post2"]):
        with patch("analytics.evidence.get_tk_post_urls_by_cuenta", return_value=[]):
            result = resolver_evidencia_voz("Alcaldia", {})

    assert "https://fb.com/post1" in result
    assert "https://fb.com/post2" in result
    assert len(result) == 2


def test_resolver_evidencia_voz_combina_fb_y_tk():
    """Voz con posts en FB y TikTok combina ambos."""
    from analytics.evidence import resolver_evidencia_voz

    with patch("analytics.evidence.get_fb_post_urls_by_pagina",
               return_value=["https://fb.com/post1"]):
        with patch("analytics.evidence.get_tk_post_urls_by_cuenta",
                   return_value=["https://tiktok.com/video1"]):
            result = resolver_evidencia_voz("Alcaldia", {})

    assert len(result) == 2
    assert "https://fb.com/post1" in result
    assert "https://tiktok.com/video1" in result


def test_resolver_evidencia_voz_sin_duplicados():
    """Voz no duplica URLs aunque las mismas aparezcan en FB y TK."""
    from analytics.evidence import resolver_evidencia_voz

    with patch("analytics.evidence.get_fb_post_urls_by_pagina",
               return_value=["https://shared.com/post1"]):
        with patch("analytics.evidence.get_tk_post_urls_by_cuenta",
                   return_value=["https://shared.com/post1"]):
            result = resolver_evidencia_voz("Alcaldia", {})

    assert len(result) == 1


def test_resolver_evidencia_voz_pagina_vacia():
    """Pagina vacia retorna lista vacia sin llamar queries."""
    from analytics.evidence import resolver_evidencia_voz

    with patch("analytics.evidence.get_fb_post_urls_by_pagina") as mock_fb:
        with patch("analytics.evidence.get_tk_post_urls_by_cuenta") as mock_tk:
            result = resolver_evidencia_voz("", {})

    assert result == []
    assert not mock_fb.called
    assert not mock_tk.called


def test_resolver_evidencia_voz_fb_falla_tk_funciona():
    """Si FB falla, still returns TikTok URLs."""
    from analytics.evidence import resolver_evidencia_voz

    with patch("analytics.evidence.get_fb_post_urls_by_pagina",
               side_effect=Exception("DB error")):
        with patch("analytics.evidence.get_tk_post_urls_by_cuenta",
                   return_value=["https://tiktok.com/video1"]):
            result = resolver_evidencia_voz("Alcaldia", {})

    assert result == ["https://tiktok.com/video1"]
