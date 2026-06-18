"""Tests Fase 2 ampliada: PDF, extracción multi-post, windowed + dedupe.

Cubren partes deterministas (sin llamar a Groq):
  - _detectar_mime con PDF
  - _enlace_confianza
  - enlace dentro de _aplicar_contrato (FB y TikTok)
  - _extraer_lista_posts (segmentación 1->N y fallbacks)
  - _deduplicar_posts
  - _pdf_a_imagenes
  - extraer_posts_desde_archivos (con chat_vision mockeado)
  - extraer_post_desde_capturas
"""
from dashboard.ingreso_extraccion import (
    _detectar_mime,
    _enlace_confianza,
    _aplicar_contrato,
    _extraer_lista_posts,
    _deduplicar_posts,
)


class TestDetectarMimePDF:
    def test_pdf_magic_bytes(self):
        assert _detectar_mime(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3") == "application/pdf"

    def test_pdf_minimal_header(self):
        assert _detectar_mime(b"%PDF") == "application/pdf"

    def test_respects_declared_pdf(self):
        assert _detectar_mime(b"", declarado="application/pdf") == "application/pdf"

    def test_image_still_detected(self):
        assert _detectar_mime(b"\xff\xd8\xff") == "image/jpeg"

    def test_non_pdf_text_fallback(self):
        assert _detectar_mime(b"hello world") == "image/png"


class TestEnlaceConfianza:
    def test_dict_valor_confianza(self):
        r = _enlace_confianza({"valor": "https://facebook.com/x", "confianza": "dudoso"})
        assert r == {"valor": "https://facebook.com/x", "confianza": "dudoso"}

    def test_raw_string(self):
        r = _enlace_confianza("https://tiktok.com/@a/video/1")
        assert r == {"valor": "https://tiktok.com/@a/video/1", "confianza": "seguro"}

    def test_none(self):
        assert _enlace_confianza(None) == {"valor": None, "confianza": "no_detectado"}

    def test_empty_string(self):
        assert _enlace_confianza("") == {"valor": None, "confianza": "no_detectado"}

    def test_whitespace_only(self):
        assert _enlace_confianza("   ") == {"valor": None, "confianza": "no_detectado"}

    def test_dict_empty_valor(self):
        assert _enlace_confianza({"valor": "", "confianza": "seguro"}) == {
            "valor": None,
            "confianza": "no_detectado",
        }

    def test_invalid_confianza_forces_seguro(self):
        r = _enlace_confianza({"valor": "https://x.com", "confianza": "???"})
        assert r == {"valor": "https://x.com", "confianza": "seguro"}


class TestContratoEnlace:
    def test_facebook_enlace_presente(self):
        resp = {
            "texto_post": "hola",
            "fecha": None,
            "enlace": {"valor": "https://facebook.com/p/1", "confianza": "seguro"},
            "reacciones": {},
            "comentarios": [],
        }
        result = _aplicar_contrato(resp, "facebook")
        assert result["enlace"] == {"valor": "https://facebook.com/p/1", "confianza": "seguro"}

    def test_facebook_enlace_ausente(self):
        resp = {"texto_post": "hola", "fecha": None, "reacciones": {}, "comentarios": []}
        result = _aplicar_contrato(resp, "facebook")
        assert result["enlace"] == {"valor": None, "confianza": "no_detectado"}

    def test_tiktok_enlace_presente(self):
        resp = {
            "texto_post": "vid",
            "fecha": None,
            "enlace": "https://tiktok.com/@a/video/9",
            "metricas": {},
            "comentarios": [],
        }
        result = _aplicar_contrato(resp, "tiktok")
        assert result["enlace"] == {"valor": "https://tiktok.com/@a/video/9", "confianza": "seguro"}


class TestExtraerListaPosts:
    def test_posts_key(self):
        parsed = {"posts": [{"texto_post": "a"}, {"texto_post": "b"}, {"texto_post": "c"}]}
        out = _extraer_lista_posts(parsed)
        assert len(out) == 3
        assert out[0]["texto_post"] == "a"

    def test_list_directly(self):
        parsed = [{"texto_post": "a"}, {"texto_post": "b"}]
        assert len(_extraer_lista_posts(parsed)) == 2

    def test_single_post_fallback(self):
        parsed = {"texto_post": "solo", "reacciones": {}, "comentarios": []}
        out = _extraer_lista_posts(parsed)
        assert len(out) == 1
        assert out[0]["texto_post"] == "solo"

    def test_empty_dict(self):
        assert _extraer_lista_posts({}) == []

    def test_none(self):
        assert _extraer_lista_posts(None) == []

    def test_posts_filters_non_dicts(self):
        parsed = {"posts": [{"texto_post": "a"}, "basura", None, {"metricas": {}}]}
        out = _extraer_lista_posts(parsed)
        assert len(out) == 2

    def test_multi_post_contrato(self):
        """Un PDF -> varios posts -> cada uno pasa por el contrato."""
        parsed = {
            "posts": [
                {"texto_post": "post 1", "reacciones": {"likes": 10},
                 "enlace": "https://facebook.com/1", "comentarios": []},
                {"texto_post": "post 2", "reacciones": {"likes": 20},
                 "enlace": "https://facebook.com/2", "comentarios": []},
            ]
        }
        posts = [_aplicar_contrato(p, "facebook") for p in _extraer_lista_posts(parsed)]
        assert len(posts) == 2
        assert posts[0]["enlace"]["valor"] == "https://facebook.com/1"
        assert posts[1]["reacciones"]["likes"]["valor"] == 20


class TestDeduplicarPosts:
    def test_no_duplicates_returns_all(self):
        posts = [
            {"enlace": {"valor": "https://fb.com/1"}, "comentarios_count": {"valor": 5}, "texto_post": "a"},
            {"enlace": {"valor": "https://fb.com/2"}, "comentarios_count": {"valor": 3}, "texto_post": "b"},
        ]
        result = _deduplicar_posts(posts)
        assert len(result) == 2

    def test_dedupe_by_link_keeps_more_comments(self):
        posts = [
            {"enlace": {"valor": "https://fb.com/1"}, "comentarios_count": {"valor": 5}, "texto_post": "first"},
            {"enlace": {"valor": "https://fb.com/2"}, "comentarios_count": {"valor": 3}, "texto_post": "second"},
            {"enlace": {"valor": "https://fb.com/1"}, "comentarios_count": {"valor": 10}, "texto_post": "third"},
        ]
        result = _deduplicar_posts(posts)
        assert len(result) == 2
        assert result[0]["texto_post"] == "third"

    def test_dedupe_by_text_when_no_link(self):
        posts = [
            {"enlace": {"valor": None}, "comentarios_count": {"valor": 2}, "texto_post": "Texto común aquí"},
            {"enlace": {"valor": None}, "comentarios_count": {"valor": 7}, "texto_post": "Texto común aquí"},
        ]
        result = _deduplicar_posts(posts)
        assert len(result) == 1
        assert result[0]["comentarios_count"]["valor"] == 7

    def test_no_link_no_text_unique(self):
        posts = [
            {"enlace": {"valor": None}, "comentarios_count": {"valor": 2}, "texto_post": ""},
            {"enlace": {"valor": None}, "comentarios_count": {"valor": 3}, "texto_post": ""},
        ]
        result = _deduplicar_posts(posts)
        assert len(result) == 2

    def test_link_case_insensitive(self):
        posts = [
            {"enlace": {"valor": "https://FB.com/Post"}, "comentarios_count": {"valor": 1}, "texto_post": "a"},
            {"enlace": {"valor": "https://fb.com/post"}, "comentarios_count": {"valor": 5}, "texto_post": "b"},
        ]
        result = _deduplicar_posts(posts)
        assert len(result) == 1
        assert result[0]["texto_post"] == "b"


import pytest
from dashboard.ingreso_extraccion import (
    _pdf_a_imagenes,
    extraer_posts_desde_archivos,
    extraer_post_desde_capturas,
)


class TestPDFaImagenes:
    def test_two_pages(self):
        pytest.importorskip("fitz")
        import fitz
        doc = fitz.open()
        doc.new_page(width=300, height=400)
        doc.new_page(width=300, height=400)
        data = doc.tobytes()
        doc.close()
        result = _pdf_a_imagenes(data)
        assert len(result) == 2
        for png in result:
            assert png[:4] == b"\x89PNG"

    def test_corrupt_bytes_returns_empty(self):
        result = _pdf_a_imagenes(b"not a pdf at all")
        assert result == []


class TestGroqFlow:
    """Tests que mockean chat_vision para probar el flujo de extracción."""

    def _crear_png(self):
        from PIL import Image
        import io
        img = Image.new("RGB", (50, 50), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_single_image_one_post(self):
        """1 página (<= VENTANA) → una sola llamada, devuelve 1 post."""
        from unittest.mock import patch

        png = self._crear_png()

        resp_json = '{"posts": [{"texto_post": "solo post", "fecha": "2024-01-01", "enlace": null, "reacciones": {"likes": 5}, "comentarios": []}]}'

        with patch("dashboard.ingreso_extraccion.groq_disponible", return_value=True), \
             patch("dashboard.ingreso_extraccion.chat_vision", return_value=resp_json):
            result = extraer_posts_desde_archivos([png], "facebook")

        assert "error" not in result, result.get("error")
        assert len(result["posts"]) == 1
        assert result["posts"][0]["texto_post"] == "solo post"

    def test_two_images_two_posts(self):
        """2 páginas (<= VENTANA) → una sola llamada, devuelve 2 posts."""
        from unittest.mock import patch

        png1 = self._crear_png()
        png2 = self._crear_png()

        resp_json = (
            '{"posts": ['
            '{"texto_post": "post 1", "fecha": "2024-01-01", "enlace": {"valor": "https://fb.com/1"}, "reacciones": {"likes": 10}, "comentarios": []},'
            '{"texto_post": "post 2", "fecha": "2024-01-02", "enlace": null, "reacciones": {"likes": 20}, "comentarios": []}'
            "]}"
        )

        with patch("dashboard.ingreso_extraccion.groq_disponible", return_value=True), \
             patch("dashboard.ingreso_extraccion.chat_vision", return_value=resp_json):
            result = extraer_posts_desde_archivos([png1, png2], "facebook")

        assert "error" not in result, result.get("error")
        assert len(result["posts"]) == 2
        assert result["posts"][0]["texto_post"] == "post 1"
        assert result["posts"][1]["texto_post"] == "post 2"
        assert result["posts"][0]["enlace"]["valor"] == "https://fb.com/1"

    def test_windowed_dedupe_by_link(self):
        """> VENTANA páginas → llamadas por ventanas + dedupe por enlace."""
        from unittest.mock import patch

        # Creamos 5 páginas (VENTANA por defecto es 4)
        pngs = [self._crear_png() for _ in range(5)]

        # Ventana 0 (páginas 0-3): devuelve posts con enlaces
        # Ventana 1 (páginas 3-4, solape 1): devuelve post repetido con más comentarios
        resp_w0 = (
            '{"posts": ['
            '{"texto_post": "post A", "fecha": "2024-01-01", "enlace": {"valor": "https://fb.com/a"}, "reacciones": {"likes": 10}, "comentarios_count": {"valor": 5}, "comentarios": []},'
            '{"texto_post": "post B", "fecha": "2024-01-02", "enlace": {"valor": "https://fb.com/b"}, "reacciones": {"likes": 20}, "comentarios_count": {"valor": 3}, "comentarios": []}'
            "]}"
        )
        resp_w1 = (
            '{"posts": ['
            '{"texto_post": "post A REPEAT", "fecha": "2024-01-01", "enlace": {"valor": "https://fb.com/a"}, "reacciones": {"likes": 10}, "comentarios_count": {"valor": 15}, "comentarios": []}'
            "]}"
        )

        with patch("dashboard.ingreso_extraccion.groq_disponible", return_value=True), \
             patch("dashboard.ingreso_extraccion.chat_vision", side_effect=[resp_w0, resp_w1]):
            result = extraer_posts_desde_archivos(pngs, "facebook")

        assert "error" not in result, result.get("error")
        assert len(result["posts"]) == 2, (
            f"Expected 2 deduplicated posts, got {len(result['posts'])}"
        )

        posts_por_enlace = {}
        for p in result["posts"]:
            e = p.get("enlace", {}).get("valor")
            posts_por_enlace[e] = p

        # Post A debe tener 15 comentarios (el de mayor valor)
        assert posts_por_enlace["https://fb.com/a"]["comentarios_count"]["valor"] == 15, (
            "Dedupe should keep the post with more comments"
        )
        # Post B debe tener 3 comentarios
        assert posts_por_enlace["https://fb.com/b"]["comentarios_count"]["valor"] == 3

    def test_extraer_post_desde_capturas(self):
        """Compat: 1-post path devuelve contrato."""
        from unittest.mock import patch

        png = self._crear_png()

        resp_json = (
            '{"texto_post": "single post", "fecha": "2024-06-01", '
            '"reacciones": {"likes": 100}, "comentarios": []}'
        )

        with patch("dashboard.ingreso_extraccion.groq_disponible", return_value=True), \
             patch("dashboard.ingreso_extraccion.chat_vision", return_value=resp_json):
            result = extraer_post_desde_capturas([png], "facebook")

        assert "error" not in result, result.get("error")
        assert result["texto_post"] == "single post"

    def test_missing_api_key(self):
        """Sin GROQ_API_KEY → error."""
        from unittest.mock import patch

        with patch("dashboard.ingreso_extraccion.groq_disponible", return_value=False):
            result = extraer_posts_desde_archivos([self._crear_png()], "facebook")

        assert "error" in result
        assert "GROQ_API_KEY" in result["error"]
