import pytest
from src.analyzer.topic_detection import get_main_topic, detect_zona, detect_topics, is_emergency


class TestTopicDetection:
    def test_obras_publicas(self):
        assert get_main_topic("reparación de baches en la calle") == "obras_publicas"

    def test_seguridad(self):
        assert get_main_topic("preocupa la delincuencia y violencia") == "seguridad"

    def test_salud(self):
        assert get_main_topic("campaña de salud en el hospital") == "salud"

    def test_educacion(self):
        assert get_main_topic("mejorando las escuelas y colegios") == "educacion"

    def test_empleo(self):
        assert get_main_topic("nuevas oportunidades de empleo") == "empleo"

    def test_medio_ambiente(self):
        assert get_main_topic("contaminación del río") == "medio_ambiente"

    def test_corrupcion(self):
        assert get_main_topic("gobierno corrupto y ladrones") == "corrupcion"

    def test_movilidad(self):
        assert get_main_topic("tráfico y congestion vial") == "movilidad"

    def test_servicios_publicos(self):
        assert get_main_topic("sin agua ni luz en la colonia") == "servicios_publicos"

    def test_cultura(self):
        assert get_main_topic("festival cultural y desfile") == "cultura"

    def test_deportes(self):
        assert get_main_topic("torneo de fútbol este fin de semana") == "deportes"

    def test_transparencia(self):
        assert get_main_topic("rendición de cuentas y presupuesto") == "transparencia"

    def test_empty_text(self):
        assert get_main_topic("") == ""

    def test_none_text(self):
        assert get_main_topic(None) == ""

    def test_no_match(self):
        assert get_main_topic("texto sin palabras clave") == ""

    def test_detect_topics_returns_list(self):
        topics = detect_topics("baches y calles en mal estado")
        assert len(topics) > 0
        assert topics[0][1] > 0

    def test_detect_topics_multiple(self):
        topics = detect_topics("baches, delincuencia y contaminación")
        assert len(topics) >= 3


class TestZoneDetection:
    def test_centro(self):
        assert detect_zona("en el centro de santa ana") == "Centro"

    def test_norte(self):
        assert detect_zona("barrio norte de la ciudad") == "Norte"

    def test_sur(self):
        assert detect_zona("colonia sur") == "Sur"

    def test_este(self):
        assert detect_zona("sector este") == "Este"

    def test_oeste(self):
        assert detect_zona("zona oeste") == "Oeste"

    def test_empty(self):
        assert detect_zona("") == ""

    def test_no_match(self):
        assert detect_zona("texto genérico sin zona") == ""


class TestEmergency:
    def test_emergency_keyword(self):
        assert is_emergency("esto es una emergencia") is True

    def test_no_emergency(self):
        assert is_emergency("todo está tranquilo") is False

    def test_empty(self):
        assert is_emergency("") is False
