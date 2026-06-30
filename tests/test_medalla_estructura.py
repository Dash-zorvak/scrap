"""Regresión: el informe PDF debe seguir la ESTRUCTURA de la plantilla y
autollenarse con datos reales (totales, tabla de publicaciones, narrativa
editable, posts que no traducen tracción).
"""

import datetime as dt
import sqlite3

import pytest

pytest.importorskip("reportlab")

PROHIBIDAS = ["fas", "perritos", "mario dur\u00e1n", "mario duran", "es noticias"]

POST = {
    "post_id": "medalla1",
    "page_name": "Alcaldía de Santa Ana",
    "message": (
        "Una persona fue captada botando basura en la vía pública, una falta que "
        "puede ser multada conforme a la ordenanza municipal de Santa Ana."
    ),
    "created_time": "2026-06-18 12:00:00",
    "post_url": "https://facebook.com/post/medalla1",
    "likes_count": 800, "loves_count": 50, "cares_count": 10, "hahas_count": 5,
    "wows_count": 8, "sads_count": 2, "angrys_count": 30,
    "comments_count": 140, "shares_count": 60, "views_count": 9000,
}

MEDIOS = [
    {"page_name": "Diario de Occidente", "total_reactions": 200,
     "comments_count": 30, "post_url": "https://diario.com/nota"},
    {"page_name": "Radio Local", "total_reactions": 90,
     "comments_count": 12, "post_url": "https://radio.com/nota"},
]


class TestTotales:
    def test_suma_medalla_mas_medios(self):
        from dashboard.medalla_pdf import _publicaciones_y_totales, metricas_post
        m = metricas_post(POST)
        rows, tot = _publicaciones_y_totales(POST, m, MEDIOS)
        assert len(rows) == 3  # medalla + 2 medios
        assert tot["reac"] == m["total_reacciones"] + 200 + 90
        assert tot["com"] == m["comentarios"] + 30 + 12
        # Los medios externos no aportan compartidos.
        assert tot["comp"] == m["compartidos"]
        assert tot["impacto"] == tot["reac"] + tot["com"] + tot["comp"]

    def test_medios_sin_compartidos_no_inflan(self):
        from dashboard.medalla_pdf import _publicaciones_y_totales, metricas_post
        m = metricas_post(POST)
        rows, _ = _publicaciones_y_totales(POST, m, MEDIOS)
        # Las filas de medios marcan compartidos como desconocidos.
        assert rows[0]["comp_known"] is True
        assert rows[1]["comp_known"] is False


class TestBorradorNarrativa:
    def test_sin_ia_tiene_claves_y_es_generico(self):
        from dashboard.medalla_pdf import borrador_narrativa
        n = borrador_narrativa(POST, {"descripcion_post": POST["message"]}, usar_ia=False)
        for k in ("mensaje_corto", "emocion_real", "autoridad_cercana", "evidencia_tangible"):
            assert n.get(k)
        blob = " ".join(str(v) for v in n.values()).lower()
        for p in PROHIBIDAS:
            assert p not in blob

    def test_mensaje_corto_sale_del_post(self):
        from dashboard.medalla_pdf import borrador_narrativa
        n = borrador_narrativa(POST, {"descripcion_post": POST["message"]}, usar_ia=False)
        assert "basura" in n["mensaje_corto"].lower()


class TestNarrativaEditadaManda:
    def test_contexto_narrativa_se_respeta(self):
        from dashboard.medalla_pdf import _resolver_narrativa, metricas_post
        m = metricas_post(POST)
        contexto = {"narrativa": {
            "mensaje_corto": "la falta que se multa",
            "emocion_real": "indignaci\u00f3n c\u00edvica",
            "autoridad_cercana": "la alcald\u00eda actuando",
            "evidencia_tangible": "la c\u00e1mara que capta el hecho",
        }}
        n = _resolver_narrativa(POST, contexto, m, usar_ia=False)
        assert n["mensaje_corto"] == "la falta que se multa"
        assert n["emocion_real"] == "indignaci\u00f3n c\u00edvica"


class TestPDFEstructura:
    def test_genera_pdf_con_narrativa_y_no_traccion(self):
        from dashboard.medalla_pdf import generar_pdf_medalla
        contexto = {
            "periodo_label": "junio 2026",
            "descripcion_post": POST["message"],
            "medios": MEDIOS,
            "narrativa": {
                "mensaje_corto": "persona botando basura",
                "emocion_real": "indignaci\u00f3n c\u00edvica",
                "autoridad_cercana": "la alcald\u00eda presente",
                "evidencia_tangible": "la c\u00e1mara que capta el hecho",
                "titular": "falta multable",
                "medio_retomo": "Diario de Occidente",
                "comparacion": "Otro alcalde con menos seguidores logra m\u00e1s interacci\u00f3n.",
            },
            "no_traccion": [{"page_name": "Obra vial", "imagenes": []}],
            "enlaces": [POST["post_url"]],
        }
        pdf = generar_pdf_medalla(POST, contexto, imagenes=[], usar_ia=False)
        assert isinstance(pdf, (bytes, bytearray))
        assert bytes(pdf[:4]) == b"%PDF"
        assert len(pdf) > 1000

    def test_genera_pdf_minimo_sin_medios_ni_narrativa(self):
        from dashboard.medalla_pdf import generar_pdf_medalla
        pdf = generar_pdf_medalla(POST, {"periodo_label": "junio 2026"},
                                  imagenes=[], usar_ia=False)
        assert bytes(pdf[:4]) == b"%PDF"


class TestStoreNarrativaRoundtrip:
    def test_aprobar_y_recuperar_narrativa(self, tmp_path):
        db = str(tmp_path / "facebook.db")
        from dashboard import medalla_store as ms
        narrativa = {"mensaje_corto": "x", "emocion_real": "y",
                     "no_traccion": ["a", "b"]}
        ms.aprobar_medalla("p1", score=1.0, periodo_label="junio", medios=["m1"],
                           nota="n", narrativa=narrativa, db_path=db)
        v = ms.get_medalla_vigente(db_path=db)
        assert v["post_id"] == "p1"
        assert v["narrativa"]["mensaje_corto"] == "x"
        assert v["narrativa"]["no_traccion"] == ["a", "b"]
        assert v["medios"] == ["m1"]


class TestSugerirNoTraccion:
    def _crear_db(self, db):
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE fb_posts (post_id TEXT, page_name TEXT, message TEXT, "
            "created_time TEXT, likes_count INT, loves_count INT, cares_count INT, "
            "hahas_count INT, wows_count INT, sads_count INT, angrys_count INT, "
            "comments_count INT, shares_count INT)"
        )
        # Alta tracci\u00f3n
        conn.execute(
            "INSERT INTO fb_posts VALUES ('hi','Alcald\u00eda de Santa Ana','a',"
            "'2026-06-10 10:00:00',10,100,50,0,20,0,0,40,30)")
        # Baja tracci\u00f3n
        conn.execute(
            "INSERT INTO fb_posts VALUES ('lo','Alcald\u00eda de Santa Ana','b',"
            "'2026-06-11 10:00:00',5,0,0,0,0,1,1,1,0)")
        conn.commit()
        conn.close()

    def test_devuelve_los_de_menor_traccion(self, tmp_path):
        db = str(tmp_path / "facebook.db")
        self._crear_db(db)
        from dashboard import medalla_seleccion as msel
        ini = dt.datetime(2026, 6, 1)
        fin = dt.datetime(2026, 6, 30)
        res = msel.sugerir_no_traccion(ini, fin, top=1, db_path=db)
        assert res and res[0]["post_id"] == "lo"
