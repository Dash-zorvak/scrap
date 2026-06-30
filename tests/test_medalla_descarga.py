"""Regresión del bug: «aprobé la medalla, dice que está lista para descargar,
pero en el dashboard no aparece nada para descargar».

Causa raíz: el dashboard solo mostraba un botón «Generar informe PDF» y la
descarga aparecía recién después de pulsarlo. Fix: render_descarga_medalla
prepara el PDF automáticamente y ofrece la descarga sin pasos manuales.

Estos tests cubren tres capas independientes:
  1. Datos     — aprobar_medalla + get_medalla_vigente.
  2. PDF       — generar_pdf_medalla devuelve bytes %PDF válidos.
  3. Render    — render_descarga_medalla ofrece la descarga sin pulsar nada.
"""

import pytest

# El render y el PDF dependen de reportlab (medalla_pdf lo importa al cargar).
pytest.importorskip("reportlab")


class TestCapaDatos:
    """La aprobación persiste y get_medalla_vigente la recupera."""

    def test_aprobar_y_obtener_vigente(self):
        from dashboard import medalla_store

        medalla_store.aprobar_medalla(
            post_id="post_test_descarga_1",
            score=42,
            periodo_label="junio 2026",
            medios=[],
            nota="prueba de regresión",
        )
        vigente = medalla_store.get_medalla_vigente()
        assert vigente is not None
        assert vigente.get("post_id") == "post_test_descarga_1"


class TestPDF:
    """generar_pdf_medalla produce un PDF real sin depender de Streamlit."""

    def test_genera_pdf_bytes(self):
        from dashboard.medalla_pdf import generar_pdf_medalla

        post = {
            "post_id": "p1",
            "page_name": "Alcaldía de Santa Ana",
            "message": "Texto de prueba para el informe. " * 20,
            "created_time": "2026-06-15 10:00:00",
            "post_url": "https://facebook.com/post/1",
            "likes_count": 1000,
            "loves_count": 200,
            "cares_count": 10,
            "hahas_count": 5,
            "wows_count": 3,
            "sads_count": 1,
            "angrys_count": 1,
            "comments_count": 50,
            "shares_count": 30,
            "views_count": 5000,
        }
        contexto = {
            "periodo_label": "junio 2026",
            "enlaces": ["https://facebook.com/post/1"],
            "medios": [],
        }
        pdf = generar_pdf_medalla(post, contexto, imagenes=[], usar_ia=False)
        assert isinstance(pdf, (bytes, bytearray))
        assert bytes(pdf[:4]) == b"%PDF"
        assert len(pdf) > 1000


class _Ctx:
    """Context manager trivial para simular st.spinner(...)."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeSt:
    """Doble de Streamlit que captura descargas e infos sin pintar UI."""

    def __init__(self):
        self.session_state = {}
        self.downloads = []
        self.infos = []
        self.warnings = []
        self.errors = []

    def markdown(self, *a, **k):
        pass

    def caption(self, *a, **k):
        pass

    def info(self, msg="", *a, **k):
        self.infos.append(msg)

    def warning(self, msg="", *a, **k):
        self.warnings.append(msg)

    def error(self, msg="", *a, **k):
        self.errors.append(msg)

    def download_button(self, *a, **k):
        self.downloads.append((a, k))
        return False

    def button(self, *a, **k):
        # El alcalde no pulsa nada: la descarga debe ofrecerse igual.
        return False

    def spinner(self, *a, **k):
        return _Ctx()


class TestRenderDescarga:
    """El dashboard ofrece la descarga sin pasos manuales."""

    def _patch_md(self, monkeypatch, fake, vigente, post=None):
        from dashboard import medalla_dashboard as md

        monkeypatch.setattr(md, "st", fake)
        monkeypatch.setattr(
            md.medalla_store, "get_medalla_vigente", lambda *a, **k: vigente
        )
        monkeypatch.setattr(md.db_edits, "leer_post", lambda *a, **k: post)
        monkeypatch.setattr(
            md.medalla_seleccion, "externos_por_ids", lambda ids: []
        )
        monkeypatch.setattr(md, "listar_capturas", lambda *a, **k: [])
        monkeypatch.setattr(
            md, "generar_pdf_medalla", lambda *a, **k: b"%PDF-fake"
        )
        return md

    def test_ofrece_descarga_sin_pulsar(self, monkeypatch):
        fake = _FakeSt()
        vigente = {
            "post_id": "p1",
            "decidido_en": "2026-06-20 09:00:00",
            "medios": [],
            "periodo_label": "junio 2026",
        }
        post = {
            "post_id": "p1",
            "page_name": "Alcaldía de Santa Ana",
            "created_time": "2026-06-15",
            "post_url": "https://facebook.com/post/1",
        }
        md = self._patch_md(monkeypatch, fake, vigente, post)

        md.render_descarga_medalla("junio 2026")

        # Hay exactamente una descarga, ofrecida sin pulsar «generar».
        assert len(fake.downloads) == 1
        # Y el PDF quedó cacheado por la medalla vigente.
        assert (
            fake.session_state.get("medalla_pdf_cache", {}).get("bytes")
            == b"%PDF-fake"
        )

    def test_sin_medalla_muestra_info_y_no_descarga(self, monkeypatch):
        fake = _FakeSt()
        md = self._patch_md(monkeypatch, fake, vigente=None)

        md.render_descarga_medalla()

        assert len(fake.downloads) == 0
        assert len(fake.infos) == 1
