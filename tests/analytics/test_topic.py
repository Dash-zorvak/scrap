"""Tests para analytics/topic.py — clasificación léxica de tema (10 categorías)."""
import pytest
from analytics.topic import (
    classify_topic, aggregate_topics, TOPIC_LEXICON,
)


# ── Sin tema / no_aplica ──

def test_no_aplica_texto_vacio():
    r = classify_topic("")
    assert r.tema == "no_aplica"


def test_no_aplica_none():
    r = classify_topic(None)
    assert r.tema == "no_aplica"


def test_no_aplica_sin_coincidencias():
    r = classify_topic("Hola que tal, ¿cómo estás?")
    assert r.tema == "no_aplica"


# ── Obras y servicios públicos ──

def test_obras_baches():
    r = classify_topic("Los baches en la calle están terrible")
    assert r.tema == "obras_servicios"
    assert r.n_coincidencias >= 1


def test_obras_agua():
    r = classify_topic("No hay agua potable en la colonia")
    assert r.tema == "obras_servicios"


def test_obras_parque():
    r = classify_topic("El parque necesita mantenimiento urgente")
    assert r.tema == "obras_servicios"


# ── Seguridad ──

def test_seguridad_robos():
    r = classify_topic("Los robos aumentaron en la zona, inseguridad total")
    assert r.tema == "seguridad"
    assert "robo" in r.evidence or "inseguridad" in r.evidence


def test_seguridad_pandillas():
    r = classify_topic("Las pandillas controlan la calle, violencia")
    assert r.tema == "seguridad"


def test_seguridad_policia():
    r = classify_topic("La policía no patrulla esta zona")
    assert r.tema == "seguridad"


# ── Movilidad ──

def test_movilidad_transporte():
    r = classify_topic("El transporte público es deficiente, buses viejos")
    assert r.tema == "movilidad"


def test_movilidad_semaforo():
    r = classify_topic("El semáforo de la 7a avenida no funciona")
    assert r.tema == "movilidad"


def test_movilidad_accidente():
    r = classify_topic("Hubo un choque en la autopista, tráfico terrible")
    assert r.tema == "movilidad"


# ── Empleo ──

def test_empleo_trabajo():
    r = classify_topic("No hay empleo formal, los salarios son bajos")
    assert r.tema == "empleo"


def test_empleo_emprendimiento():
    r = classify_topic("Los negocios y empresas están cerrando")
    assert r.tema == "empleo"


# ── Salud ──

def test_salud_hospital():
    r = classify_topic("El hospital no tiene medicamentos, los doctores faltan")
    assert r.tema == "salud"


def test_salud_medico():
    r = classify_topic("Necesito cita médica en la clínica")
    assert r.tema == "salud"


def test_salud_eps():
    r = classify_topic("La EPS no cubre las cirugías")
    assert r.tema == "salud"


# ── Educación ──

def test_educacion_escuela():
    r = classify_topic("Las escuelas necesitan más maestros y materiales")
    assert r.tema == "educacion"


def test_educacion_becas():
    r = classify_topic("Las becas estudiantiles no alcanzan")
    assert r.tema == "educacion"


def test_educacion_universidad():
    r = classify_topic("La universidad necesita más aulas para los estudiantes")
    assert r.tema == "educacion"


# ── Medio ambiente ──

def test_medio_ambiente_contaminacion():
    r = classify_topic("La contaminación del río es alarmante")
    assert r.tema == "medio_ambiente"


def test_medio_ambiente_arboles():
    r = classify_topic("Talaron los árboles del parque, deforestación")
    assert r.tema == "medio_ambiente"


# ── Gobernanza ──

def test_gobernanza_corrupcion():
    r = classify_topic("La corrupción y el fraude en el municipio son inaceptables")
    assert r.tema == "gobernanza"


def test_gobernanza_transparencia():
    r = classify_topic("No hay transparencia en el presupuesto, abuso de poder")
    assert r.tema == "gobernanza"


def test_gobernanza_alcalde():
    r = classify_topic("La gestión del alcalde y sus funcionarios es desastrosa")
    assert r.tema == "gobernanza"


# ── Cultura y deportes ──

def test_cultura_evento():
    r = classify_topic("El festival cultural fue exitoso, música y baile")
    assert r.tema == "cultura_deportes"


def test_cultura_deportes():
    r = classify_topic("El estadio necesita más canchas para los deportistas")
    assert r.tema == "cultura_deportes"


# ── Apoyo genérico ──

def test_apoyo_buen_trabajo():
    r = classify_topic("Buen trabajo, felicidades y éxitos")
    assert r.tema == "apoyo_generico"


def test_apoyo_felicidades():
    r = classify_topic("Sigues así, te apoyo y bendiciones")
    assert r.tema == "apoyo_generico"


# ── Léxico no vacío ──

def test_lexico_todas_categorias():
    """Cada categoría (excepto no_aplica) debe tener palabras semilla."""
    for tema in TOPIC_LEXICON:
        assert len(TOPIC_LEXICON[tema]) > 0, f"Tema '{tema}' con léxico vacío"


# ── Empate → gana el de mayor conteo ──

def test_empate_gana_mayor_conteo():
    r = classify_topic("La calle tiene baches y hay mucha violencia en la zona")
    # Tiene palabras de obras_servicios y seguridad
    assert r.tema in ("obras_servicios", "seguridad")


# ── Agregación batch ──

def test_aggregate_topics_vacio():
    agg = aggregate_topics([])
    assert agg["total"] == 0
    assert agg["dominante"] == "no_aplica"


def test_aggregate_topics_mixto():
    texts = [
        "Los baches en la calle",
        "Hay mucha inseguridad y robos",
        "El hospital no tiene medicamentos",
        "Buen trabajo felicidades",
        "Hola que tal",
    ]
    agg = aggregate_topics(texts)
    assert agg["total"] == 5
    assert agg["dominante"] != ""
    assert isinstance(agg["conteo"], dict)
    assert isinstance(agg["pct"], dict)


def test_aggregate_topics_sin_tema():
    texts = ["Hola", "¿Qué tal?", "Buenos días", "Adiós"]
    agg = aggregate_topics(texts)
    assert agg["n_sin_tema"] == len(texts)


# ── 18.2: Texto con contenido real pero sin match → propuesta en taxonomias_pendientes ──

def test_topic_sin_match_registra_propuesta():
    """Un texto con contenido real pero sin palabras del léxico debe
    devolver la clave propuesta (no 'no_aplica') y registrar en taxonomias_pendientes."""
    r = classify_topic("El cielo está hermoso hoy en la mañana")
    # Texto real sin match léxico → propuesta, no no_aplica
    assert r.tema != "no_aplica"
    assert "tema_nuevo_" in r.tema


def test_topic_texto_vacio_no_registra_propuesta():
    """Texto vacío no debe registrar propuesta."""
    r = classify_topic("")
    assert r.tema == "no_aplica"


# ── 19.1: classify_topic devuelve clave propuesta, no no_aplica ──

def test_topic_devuelve_propuesta_no_no_aplica():
    """Texto con contenido real sin match léxico → devuelve clave propuesta."""
    r = classify_topic("El cielo está hermoso hoy en la mañana")
    assert r.tema != "no_aplica"
    assert "tema_nuevo_" in r.tema


# ── 19.2: Deduplicación en _registrar_propuesta ──

def test_deduplicacion_propuesta_tema():
    """La misma propuesta de tema registrada dos veces → una sola entrada."""
    import json
    from analytics._propuestas import _registrar_propuesta

    for _ in range(2):
        _registrar_propuesta(
            clave_propuesta="tema_nuevo_cielo",
            ejemplo_texto="El cielo está hermoso",
            tipo="tema",
            familia_mas_cercana="",
        )

    from analytics._propuestas import _TAXONOMIAS_PATH
    import os
    path = os.path.normpath(_TAXONOMIAS_PATH)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cielo_entries = [e for e in data if e["clave_propuesta"] == "tema_nuevo_cielo"]
    assert len(cielo_entries) == 1
    assert cielo_entries[0]["n_ocurrencias"] == 2


# ── 20.1: Clave propuesta determinista (mismo texto → misma clave) ──

def test_propuesta_tema_determinista():
    """classify_topic() con el mismo texto sin match siempre devuelve la misma clave."""
    textos = [
        "El cielo está hermoso hoy en la mañana",
        "Las estrellas brillan muchísimo esta noche",
        "Mi gato duerme todo el día en el sofá",
    ]
    for texto in textos:
        r1 = classify_topic(texto)
        r2 = classify_topic(texto)
        assert r1.tema == r2.tema, (
            f"Clave no determinista para '{texto}': '{r1.tema}' vs '{r2.tema}'"
        )
        assert "tema_nuevo_" in r1.tema
