"""Capa 3 - robustez del respaldo por palabras clave.

Verifica que:
  - los dichos / frases hechas locales no se clasifican como un tema literal;
  - una sola palabra ambigua (rio, arbol, verde, ...) no basta para asignar tema;
  - una palabra ambigua con una segunda senal si asigna tema;
  - una sola palabra fuerte/especifica sigue bastando (sin regresiones).
"""

from src.analyzer.topic_detection import get_main_topic, detect_topics


class TestCapa3DichosYSenales:
    def test_dicho_no_es_tema(self):
        # Dicho burlon que menciona "rio" pero no habla de medio ambiente.
        assert get_main_topic("panchito el río estaba") == ""
        assert detect_topics("panchito el río estaba") == []

    def test_una_palabra_ambigua_no_basta(self):
        # "rio" sola (ambigua) no debe asignar medio_ambiente.
        assert get_main_topic("ahí va el río") == ""

    def test_palabra_ambigua_con_respaldo_si_asigna(self):
        # "rio" + "contaminacion" (fuerte) si asigna medio_ambiente.
        assert get_main_topic("contaminación del río") == "medio_ambiente"

    def test_dos_senales_ambiguas_asignan(self):
        # Dos palabras ambiguas del mismo tema alcanzan el minimo de senales.
        assert get_main_topic("cuidemos el río y el árbol") == "medio_ambiente"

    def test_palabra_fuerte_sola_si_asigna(self):
        # Una sola palabra fuerte y especifica sigue asignando tema (sin regresion).
        assert get_main_topic("nuevas oportunidades de empleo") == "empleo"

    def test_texto_sin_senales(self):
        assert get_main_topic("hola que tal como amanecieron") == ""
