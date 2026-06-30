"""Regresión: el informe PDF de la medalla debe ADAPTARSE al post real del período.

Bug reportado: el PDF descargado del dashboard mostraba siempre el caso del PDF
original (FAS / perritos / Mario Durán / ES Noticias) y la misma conclusión, sin
importar cuál fuera la publicación medalla real. Causa raíz: el texto del caso
estaba escrito verbatim en constantes y el contexto no pasaba la descripción del
post real, así que la plantilla caía siempre al caso por defecto.

Fix: la doctrina («prueba del dolor» y anti-patrones) queda como marco genérico
reutilizable; la lectura del caso y el párrafo de alcance se redactan a partir de
los datos reales del post (con respaldo determinista sin LLM). También se cubre
el alta de réplicas de medios externos pegando el enlace a mano.
"""

import pytest

pytest.importorskip("reportlab")

# Palabras del caso original que NUNCA deben aparecer cuando la medalla es otra.
PROHIBIDAS = ["fas", "perritos", "mario durán", "mario duran", "es noticias", "club fas"]

POST_BASURA = {
    "post_id": "p_basura",
    "page_name": "Alcaldía de Santa Ana",
    "message": (
        "Una persona fue captada por las cámaras de videovigilancia botando basura "
        "en la vía pública, una falta que puede ser multada conforme a la ordenanza "
        "municipal de Santa Ana."
    ),
    "created_time": "2026-06-18 12:00:00",
    "post_url": "https://facebook.com/post/basura",
    "likes_count": 800, "loves_count": 50, "cares_count": 10, "hahas_count": 5,
    "wows_count": 8, "sads_count": 2, "angrys_count": 30,
    "comments_count": 140, "shares_count": 60, "views_count": 9000,
}


def _texto_doctrina():
    """Concatena todo el texto del marco GENÉRICO del módulo, en minúsculas."""
    from dashboard import medalla_pdf as mp
    partes = [
        mp.DOCTRINA_TITULO, mp.DOCTRINA_INTRO, mp.DOCTRINA_LEAD, mp.DOCTRINA_IGUAL,
        mp.DOCTRINA_CIERRE, mp.NO_TRACCION_TITULO, mp.NO_TRACCION_CIERRE,
        mp.LECTURA_TITULO, mp.TITULO,
    ]
    for t, d in mp.DOCTRINA_ELEMENTOS:
        partes += [t, d]
    for t, d in mp.NO_TRACCION_PUNTOS:
        partes += [t, d]
    return " ".join(partes).lower()


class TestDoctrinaGenerica:
    """El marco fijo del módulo ya no menciona ningún caso concreto."""

    def test_doctrina_no_menciona_el_caso_original(self):
        texto = _texto_doctrina()
        for palabra in PROHIBIDAS:
            assert palabra not in texto, f"La doctrina genérica no debe mencionar «{palabra}»"


class TestParrafoAlcanceAdaptativo:
    def test_alcance_refleja_el_post_real(self):
        from dashboard.medalla_pdf import _parrafo_alcance_plantilla, metricas_post
        m = metricas_post(POST_BASURA)
        parrafo = _parrafo_alcance_plantilla(
            POST_BASURA, {"periodo_label": "junio 2026"}, m
        ).lower()
        assert "basura" in parrafo
        for palabra in PROHIBIDAS:
            assert palabra not in parrafo


class TestLecturaCasoAdaptativa:
    def test_lectura_refleja_el_post_real(self):
        from dashboard.medalla_pdf import _lectura_caso_plantilla, metricas_post
        m = metricas_post(POST_BASURA)
        lectura = _lectura_caso_plantilla(POST_BASURA, {}, m).lower()
        assert "basura" in lectura
        assert "alcaldía de santa ana" in lectura
        for palabra in PROHIBIDAS:
            assert palabra not in lectura

    def test_usa_descripcion_post_del_contexto(self):
        from dashboard.medalla_pdf import _lectura_caso_plantilla, metricas_post
        post = {"post_id": "x", "page_name": "Gustavo Acevedo"}  # sin message
        m = metricas_post(post)
        lectura = _lectura_caso_plantilla(
            post, {"descripcion_post": "Reparación de la cancha del parque central"}, m
        ).lower()
        assert "cancha" in lectura


class TestPDFAdaptativoSinIA:
    def test_genera_pdf_bytes(self):
        from dashboard.medalla_pdf import generar_pdf_medalla
        contexto = {
            "periodo_label": "junio 2026",
            "descripcion_post": POST_BASURA["message"],
            "enlaces": [POST_BASURA["post_url"]],
            "medios": [],
        }
        pdf = generar_pdf_medalla(POST_BASURA, contexto, imagenes=[], usar_ia=False)
        assert isinstance(pdf, (bytes, bytearray))
        assert bytes(pdf[:4]) == b"%PDF"
        assert len(pdf) > 1000


class TestEnlaceMedioExternoManual:
    def test_agregar_y_recuperar(self, tmp_path):
        db = str(tmp_path / "externos.db")
        from dashboard import externos_store, medalla_seleccion
        pid = externos_store.agregar_post_externo_manual(
            url="https://diario.com/nota/medalla",
            page_name="Diario de Occidente",
            total_reactions=210, comments_count=18, db_path=db,
        )
        assert pid
        filas = medalla_seleccion.externos_por_ids([pid], db_path=db)
        assert len(filas) == 1
        assert filas[0]["post_url"] == "https://diario.com/nota/medalla"
        assert filas[0]["page_name"] == "Diario de Occidente"
        assert int(filas[0]["total_reactions"]) == 210

    def test_sin_datos_devuelve_none(self, tmp_path):
        from dashboard import externos_store
        db = str(tmp_path / "externos.db")
        assert externos_store.agregar_post_externo_manual(
            url="", page_name="", db_path=db
        ) is None


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeSt:
    """Doble mínimo de Streamlit para capturar el contexto del PDF."""

    def __init__(self):
        self.session_state = {}
        self.downloads = []

    def markdown(self, *a, **k):
        pass

    def caption(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass

    def download_button(self, *a, **k):
        self.downloads.append((a, k))
        return False

    def button(self, *a, **k):
        return False

    def spinner(self, *a, **k):
        return _Ctx()


class TestContextoDashboard:
    """El dashboard pasa la descripción del post real al contexto del PDF."""

    def test_contexto_incluye_descripcion_post(self, monkeypatch):
        from dashboard import medalla_dashboard as md
        capturado = {}
        fake = _FakeSt()
        monkeypatch.setattr(md, "st", fake)
        vigente = {
            "post_id": "p1", "decidido_en": "2026-06-20 09:00:00",
            "medios": [], "periodo_label": "junio 2026",
        }
        post = {
            "post_id": "p1", "page_name": "Alcaldía de Santa Ana",
            "message": "Persona botando basura en la vía pública",
            "created_time": "2026-06-18", "post_url": "https://facebook.com/post/1",
        }
        monkeypatch.setattr(md.medalla_store, "get_medalla_vigente", lambda *a, **k: vigente)
        monkeypatch.setattr(md.db_edits, "leer_post", lambda *a, **k: post)
        monkeypatch.setattr(md.medalla_seleccion, "externos_por_ids", lambda ids: [])
        monkeypatch.setattr(md, "listar_capturas", lambda *a, **k: [])

        def fake_gen(post_arg, contexto_arg, **k):
            capturado["contexto"] = contexto_arg
            return b"%PDF-fake"

        monkeypatch.setattr(md, "generar_pdf_medalla", fake_gen)

        md.render_descarga_medalla("junio 2026")
        assert capturado["contexto"].get("descripcion_post") == post["message"]
