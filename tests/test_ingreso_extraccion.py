"""Tests for ingreso_extraccion.py: normalizar_numero, _detectar_mime,
_num_confianza, _fecha_confianza, _aplicar_contrato."""
from dashboard.ingreso_extraccion import (
    normalizar_numero,
    _detectar_mime,
    _num_confianza,
    _fecha_confianza,
    _aplicar_contrato,
)


class TestNormalizarNumero:
    def test_simple_number(self):
        assert normalizar_numero("1234") == 1234

    def test_with_commas(self):
        assert normalizar_numero("1,234") == 1234

    def test_with_dots(self):
        assert normalizar_numero("1.234") == 1234

    def test_three_or_more_same_separator_commas(self):
        assert normalizar_numero("1,234,567") == 1234567

    def test_three_or_more_same_separator_dots(self):
        assert normalizar_numero("1.234.567") == 1234567

    def test_three_or_more_mixed_separator_comma_decimal(self):
        assert normalizar_numero("1,234,567.89") == 1234567

    def test_three_or_more_mixed_separator_dot_decimal(self):
        assert normalizar_numero("1.234.567,89") == 1234567

    def test_k_suffix(self):
        assert normalizar_numero("1.2 K") == 1200

    def test_k_suffix_lowercase(self):
        assert normalizar_numero("1.2k") == 1200

    def test_mil(self):
        assert normalizar_numero("34 mil") == 34000

    def test_millones(self):
        assert normalizar_numero("2 millones") == 2000000

    def test_m_suffix(self):
        assert normalizar_numero("1.5 M") == 1500000

    def test_null_input(self):
        assert normalizar_numero(None) is None

    def test_empty_string(self):
        assert normalizar_numero("") is None

    def test_dash(self):
        assert normalizar_numero("—") is None

    def test_na(self):
        assert normalizar_numero("N/A") is None

    def test_non_numeric(self):
        assert normalizar_numero("abc") is None


class TestDetectarMime:
    def test_jpeg_magic_bytes(self):
        assert _detectar_mime(b"\xff\xd8\xff") == "image/jpeg"

    def test_png_magic_bytes(self):
        assert _detectar_mime(b"\x89PNG\r\n\x1a\n") == "image/png"

    def test_webp_magic_bytes(self):
        assert _detectar_mime(b"RIFF....WEBP") == "image/webp"

    def test_unknown_bytes_fallback(self):
        assert _detectar_mime(b"\x00\x00\x00") == "image/png"

    def test_respects_declared_image(self):
        assert _detectar_mime(b"", declarado="image/jpeg") == "image/jpeg"

    def test_ignores_declared_non_image(self):
        assert _detectar_mime(b"", declarado="text/plain") == "image/png"

    def test_empty_bytes(self):
        assert _detectar_mime(b"") == "image/png"


class TestNumConfianza:
    def test_dict_with_valor_confianza_dudoso(self):
        r = _num_confianza({"valor": "1.2K", "confianza": "dudoso"})
        assert r == {"valor": 1200, "confianza": "dudoso"}

    def test_dict_with_valor_confianza_seguro(self):
        r = _num_confianza({"valor": 50, "confianza": "seguro"})
        assert r == {"valor": 50, "confianza": "seguro"}

    def test_dict_null_valor_no_detectado(self):
        r = _num_confianza({"valor": None, "confianza": "dudoso"})
        assert r == {"valor": None, "confianza": "no_detectado"}

    def test_raw_number_compat(self):
        r = _num_confianza(100)
        assert r == {"valor": 100, "confianza": "seguro"}

    def test_raw_none_compat(self):
        r = _num_confianza(None)
        assert r == {"valor": None, "confianza": "no_detectado"}

    def test_dict_invalid_confianza_forces_seguro(self):
        r = _num_confianza({"valor": 50, "confianza": "invalida"})
        assert r == {"valor": 50, "confianza": "seguro"}

    def test_dict_missing_confianza_defaults_seguro(self):
        r = _num_confianza({"valor": 50})
        assert r == {"valor": 50, "confianza": "seguro"}

    def test_predeterminado_dudoso(self):
        r = _num_confianza(None, predeterminado="dudoso")
        assert r == {"valor": None, "confianza": "dudoso"}

    def test_raw_str_normalized(self):
        r = _num_confianza("1.5K")
        assert r == {"valor": 1500, "confianza": "seguro"}


class TestFechaConfianza:
    def test_dict_valor_confianza(self):
        r = _fecha_confianza({"valor": "2024-01-15", "confianza": "dudoso"})
        assert r == {"valor": "2024-01-15", "confianza": "dudoso"}

    def test_raw_string(self):
        r = _fecha_confianza("2024-01-15")
        assert r == {"valor": "2024-01-15", "confianza": "seguro"}

    def test_none(self):
        r = _fecha_confianza(None)
        assert r == {"valor": None, "confianza": "no_detectado"}

    def test_empty_string(self):
        r = _fecha_confianza("")
        assert r == {"valor": None, "confianza": "no_detectado"}

    def test_dict_empty_valor(self):
        r = _fecha_confianza({"valor": "", "confianza": "seguro"})
        assert r == {"valor": None, "confianza": "no_detectado"}

    def test_dict_invalid_confianza_forces_seguro(self):
        r = _fecha_confianza({"valor": "2024-01-15", "confianza": "invalida"})
        assert r == {"valor": "2024-01-15", "confianza": "seguro"}


class TestAplicarContratoFacebook:
    def test_new_format_dict_values(self):
        resp = {
            "texto_post": "Hola mundo",
            "fecha": {"valor": "2024-01-15", "confianza": "dudoso"},
            "autor_pagina": "Mi Pagina",
            "reacciones": {
                "likes": {"valor": "1.2K", "confianza": "dudoso"},
                "loves": {"valor": 500, "confianza": "seguro"},
                "hahas": None,
                "sads": None,
                "wows": None,
                "angrys": None,
                "total": None,
            },
            "comentarios_count": {"valor": "150", "confianza": "seguro"},
            "comentarios": [{"texto": "Primero", "autor": "User1"}],
        }
        result = _aplicar_contrato(resp, "facebook")
        assert result["plataforma"] == "facebook"
        assert result["texto_post"] == "Hola mundo"
        assert result["fecha"] == {"valor": "2024-01-15", "confianza": "dudoso"}
        assert result["autor_pagina"] == "Mi Pagina"
        assert result["reacciones"]["likes"] == {"valor": 1200, "confianza": "dudoso"}
        assert result["reacciones"]["loves"] == {"valor": 500, "confianza": "seguro"}
        assert result["reacciones"]["hahas"] == {"valor": None, "confianza": "no_detectado"}
        assert result["reacciones"]["total"] == {"valor": None, "confianza": "dudoso"}
        assert result["comentarios_count"] == {"valor": 150, "confianza": "seguro"}
        assert result["compartidos"] == {"valor": None, "confianza": "manual"}
        assert result["vistas"] == {"valor": None, "confianza": "manual"}
        assert len(result["comentarios"]) == 1

    def test_compat_raw_numbers(self):
        resp = {
            "texto_post": "",
            "fecha": "2024-06-01",
            "autor_pagina": None,
            "reacciones": {
                "likes": 100, "loves": None, "hahas": None,
                "sads": None, "wows": None, "angrys": None, "total": None,
            },
            "comentarios_count": None,
            "comentarios": [],
        }
        result = _aplicar_contrato(resp, "facebook")
        assert result["fecha"] == {"valor": "2024-06-01", "confianza": "seguro"}
        assert result["reacciones"]["likes"] == {"valor": 100, "confianza": "seguro"}

    def test_texto_post_fallback(self):
        resp = {"texto_post": None, "fecha": None, "reacciones": {}, "comentarios": []}
        result = _aplicar_contrato(resp, "facebook")
        assert result["texto_post"] == ""


class TestAplicarContratoTikTok:
    def test_new_format(self):
        resp = {
            "texto_post": "TikTok vid",
            "fecha": {"valor": "2024-03-10", "confianza": "seguro"},
            "autor_cuenta": "@user",
            "metricas": {
                "likes": {"valor": "5K", "confianza": "dudoso"},
                "favoritos": None,
                "comentarios_count": {"valor": 50, "confianza": "seguro"},
            },
            "comentarios": [],
        }
        result = _aplicar_contrato(resp, "tiktok")
        assert result["plataforma"] == "tiktok"
        assert result["texto_post"] == "TikTok vid"
        assert result["fecha"] == {"valor": "2024-03-10", "confianza": "seguro"}
        assert result["metricas"]["likes"] == {"valor": 5000, "confianza": "dudoso"}
        assert result["metricas"]["favoritos"] == {"valor": None, "confianza": "no_detectado"}
        assert result["metricas"]["comentarios_count"] == {"valor": 50, "confianza": "seguro"}
        assert result["metricas"]["compartidos"] == {"valor": None, "confianza": "manual"}
        assert result["metricas"]["vistas"] == {"valor": None, "confianza": "manual"}
