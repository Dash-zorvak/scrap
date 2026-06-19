"""Regresion del fix de fusion (#32): un post repartido en varias paginas
NO debe partirse en varios.

El bug original (2.pdf): un PDF de 1 post real (pagina de enlace + pagina de
captura + pagina de comentarios + pagina en blanco) se leia como 4 posts. La
correccion (_fusionar_posts / _depurar_posts en dashboard/ingreso_extraccion.py)
ancla la segmentacion al ENLACE:
  - 0 o 1 URL distinta en todo el documento -> 1 solo post (se fusionan los
    fragmentos).
  - 2+ URLs distintas -> 1 post por URL, respetando el orden de aparicion; los
    fragmentos sin URL pertenecen al post de la ultima URL vista.

Estos tests son deterministas (no llaman a Groq), salvo el de extremo a extremo,
que mockea chat_vision.
"""
import io
from unittest.mock import patch

from dashboard.ingreso_extraccion import (
    _depurar_posts,
    extraer_posts_desde_archivos,
)


def _frag_fb(texto="", enlace=None, comentarios=None):
    """Fragmento Facebook con forma de contrato (post-_aplicar_contrato)."""
    return {
        "plataforma": "facebook",
        "texto_post": texto,
        "fecha": {"valor": None, "confianza": "no_detectado"},
        "autor_pagina": None,
        "enlace": {
            "valor": enlace,
            "confianza": "seguro" if enlace else "no_detectado",
        },
        "reacciones": {},
        "comentarios_count": {"valor": None, "confianza": "no_detectado"},
        "compartidos": {"valor": None, "confianza": "manual"},
        "vistas": {"valor": None, "confianza": "manual"},
        "comentarios": comentarios or [],
    }


class TestFusionUnPost:
    def test_un_post_repartido_en_cuatro_paginas_es_uno(self):
        """Caso 2.pdf: 1 enlace repartido en 4 fragmentos -> 1 post."""
        frags = [
            _frag_fb(enlace="https://www.facebook.com/share/p/1Z4huszzzF/"),
            _frag_fb(texto="Texto real del post de Gustavo Acevedo"),
            _frag_fb(comentarios=[{"texto": "Buen trabajo", "autor": "Ana"}]),
            _frag_fb(),  # pagina en blanco -> se descarta
        ]
        out = _depurar_posts(frags)
        assert len(out) == 1
        post = out[0]
        assert post["enlace"]["valor"] == "https://www.facebook.com/share/p/1Z4huszzzF/"
        assert post["texto_post"] == "Texto real del post de Gustavo Acevedo"
        assert len(post["comentarios"]) == 1

    def test_dos_enlaces_distintos_son_dos_posts(self):
        frags = [
            _frag_fb(texto="post uno", enlace="https://www.facebook.com/p/1"),
            _frag_fb(comentarios=[{"texto": "c1", "autor": None}]),  # sigue al post 1
            _frag_fb(texto="post dos", enlace="https://www.facebook.com/p/2"),
        ]
        out = _depurar_posts(frags)
        assert len(out) == 2
        assert out[0]["enlace"]["valor"] == "https://www.facebook.com/p/1"
        assert len(out[0]["comentarios"]) == 1  # fragmento sin URL se fusiona al post 1
        assert out[1]["enlace"]["valor"] == "https://www.facebook.com/p/2"

    def test_sin_enlace_fallback_a_un_post(self):
        frags = [
            _frag_fb(texto="frag a"),
            _frag_fb(
                texto="frag b mas larga",
                comentarios=[{"texto": "x", "autor": None}],
            ),
        ]
        out = _depurar_posts(frags)
        assert len(out) == 1
        assert len(out[0]["comentarios"]) == 1


class TestFusionEndToEnd:
    """Mockea chat_vision: el modelo parte 1 post en 4 fragmentos; el motor
    debe devolver 1 solo post tras la fusion."""

    def _crear_png(self):
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_pdf_un_post_cuatro_fragmentos(self):
        resp_json = (
            '{"posts": ['
            '{"texto_post": "", "fecha": null, "enlace": {"valor": "https://www.facebook.com/share/p/1Z4huszzzF/", "confianza": "seguro"}, "reacciones": {}, "comentarios": []},'
            '{"texto_post": "Comunicado oficial de la Alcaldia", "fecha": "2026-05-12", "enlace": null, "reacciones": {}, "comentarios": []},'
            '{"texto_post": "", "fecha": null, "enlace": null, "reacciones": {"likes": 52, "total": 95}, "comentarios": [{"texto": "Excelente", "autor": "Juan"}]},'
            '{"texto_post": "", "fecha": null, "enlace": null, "reacciones": {}, "comentarios": []}'
            "]}"
        )
        # 4 paginas <= VENTANA (4) -> una sola llamada
        paginas = [self._crear_png() for _ in range(4)]
        with patch(
            "dashboard.ingreso_extraccion.groq_disponible", return_value=True
        ), patch(
            "dashboard.ingreso_extraccion.chat_vision", return_value=resp_json
        ):
            result = extraer_posts_desde_archivos(paginas, "facebook")

        assert "error" not in result, result.get("error")
        assert len(result["posts"]) == 1, (
            f"El PDF de 1 post no debe partirse; got {len(result['posts'])}"
        )
        post = result["posts"][0]
        assert (
            post["enlace"]["valor"]
            == "https://www.facebook.com/share/p/1Z4huszzzF/"
        )
        assert post["texto_post"] == "Comunicado oficial de la Alcaldia"
        assert post["reacciones"]["likes"]["valor"] == 52
        assert len(post["comentarios"]) == 1
