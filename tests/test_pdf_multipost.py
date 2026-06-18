"""Tests Fase 2 ampliada: PDF, segmentación multi-post y enlace automático.

Cubren las partes deterministas (sin llamar a Gemini):
  - _detectar_mime con PDF
  - _enlace_confianza
  - enlace dentro de _aplicar_contrato (FB y TikTok)
  - _extraer_lista_posts (segmentación 1->N y fallbacks)
"""
from dashboard.ingreso_extraccion import (
    _detectar_mime,
    _enlace_confianza,
    _aplicar_contrato,
    _extraer_lista_posts,
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

    def test_segmentacion_1_a_n_contrato(self):
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


import pytest
from dashboard.ingreso_extraccion import (
    _pdf_a_imagenes,
    _extraer_grupos,
    extraer_posts_desde_archivos,
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


class TestExtraerGrupos:
    def test_normal(self):
        parsed = {"posts": [{"paginas": [1, 2], "enlace": "https://x.com"}, {"paginas": [3]}]}
        g = _extraer_grupos(parsed)
        assert g is not None
        assert len(g) == 2
        assert g[0]["paginas"] == [1, 2]
        assert g[0]["enlace"] == "https://x.com"
        assert g[1]["paginas"] == [3]

    def test_none_on_missing_key(self):
        assert _extraer_grupos({}) is None
        assert _extraer_grupos({"posts": []}) is None
        assert _extraer_grupos({"posts": [{}]}) is None

    def test_filters_non_dict(self):
        parsed = {"posts": [{"paginas": [1]}, "basura", None]}
        g = _extraer_grupos(parsed)
        assert g is not None
        assert len(g) == 1


class TestTwoPassFlow:
    def _crear_png(self):
        from PIL import Image
        import io
        img = Image.new("RGB", (50, 50), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_two_posts_from_two_images(self):
        from unittest.mock import Mock, patch

        png1 = self._crear_png()
        png2 = self._crear_png()

        seg_resp = Mock()
        seg_resp.text = '{"posts": [{"paginas": [1], "enlace": "https://fb.com/1"}, {"paginas": [2]}]}'

        post1_resp = Mock()
        post1_resp.text = '{"texto_post": "post 1", "fecha": "2024-01-01", "reacciones": {"likes": 10}, "comentarios": []}'

        post2_resp = Mock()
        post2_resp.text = '{"texto_post": "post 2", "fecha": "2024-01-02", "reacciones": {"likes": 20}, "comentarios": []}'

        mock_model = Mock()
        mock_model.generate_content.side_effect = [seg_resp, post1_resp, post2_resp]

        with patch("dashboard.ingreso_extraccion._configurar_gemini", return_value=True), \
             patch("google.generativeai.GenerativeModel", return_value=mock_model):
            result = extraer_posts_desde_archivos([png1, png2], "facebook")

        assert "error" not in result, result.get("error")
        assert len(result["posts"]) == 2
        assert result["posts"][0]["texto_post"] == "post 1"
        assert result["posts"][1]["texto_post"] == "post 2"
        # Link injection from pass 1
        assert result["posts"][0]["enlace"]["valor"] == "https://fb.com/1"
        assert result["posts"][0]["enlace"]["confianza"] == "seguro"

    def test_single_page_still_works_single_pass(self):
        from unittest.mock import Mock, patch

        png = self._crear_png()

        resp = Mock()
        resp.text = '{"posts": [{"texto_post": "solo post", "fecha": "2024-01-01", "reacciones": {"likes": 5}, "comentarios": []}]}'

        mock_model = Mock()
        mock_model.generate_content.return_value = resp

        with patch("dashboard.ingreso_extraccion._configurar_gemini", return_value=True), \
             patch("google.generativeai.GenerativeModel", return_value=mock_model):
            result = extraer_posts_desde_archivos([png], "facebook")

        assert "error" not in result, result.get("error")
        assert len(result["posts"]) == 1
        assert result["posts"][0]["texto_post"] == "solo post"
        mock_model.generate_content.assert_called_once()
