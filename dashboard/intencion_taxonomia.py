"""Taxonomía abierta de intención comunicativa (modelo MIPA).

Catálogo de 12 familias del modelo A01 con semillas de intención (seeds).
Nuevas intenciones se registran en ``taxonomias_pendientes.json``; nunca se
rechazan ni se fuerzan a un valor por defecto.

Fuentes:
  - docs/appendix/A01_COMMUNICATIVE_INTENT_MODEL.md (secciones 11, 14.3, 17-24)

Convenciones:
  - ``familia``: clave Plutchik/cívica (fija, 12 familias del modelo A01)
  - ``intencion``: código de intención (abierto — las semillas son IC-XXXX,
    las propuestas nuevas pueden tener claves libres)
  - ``principal`` / ``secundaria``: clasificación dual por comentario (A01 §11)
"""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# 12 familias del modelo A01 (sección 14.3)
# ---------------------------------------------------------------------------
FAMILIAS_INTENCION = {
    "informacion": {
        "label": "Información y Descripción",
        "descripcion": "Proporcionar datos, hechos o descripciones sobre un tema.",
    },
    "evaluacion": {
        "label": "Evaluación",
        "descripcion": "Expresar juicios de valor (positivos o negativos) sobre un tema.",
    },
    "solicitud": {
        "label": "Solicitud e Intervención",
        "descripcion": "Pedir acciones concretas a las autoridades o actores.",
    },
    "fiscalizacion": {
        "label": "Fiscalización Ciudadana",
        "descripcion": "Exigir transparencia, rendición de cuentas o acciones correctivas.",
    },
    "participacion": {
        "label": "Participación Cívica",
        "descripcion": "Participar en procesos democráticos, votaciones o consultas.",
    },
    "deliberacion": {
        "label": "Deliberación",
        "descripcion": "Argumentar, razonar o debatir posiciones con fundamento.",
    },
    "expresion_social": {
        "label": "Expresión Social",
        "descripcion": "Expresar emociones, solidaridad, gratitud o vínculos comunitarios.",
    },
    "movilizacion": {
        "label": "Movilización",
        "descripcion": "Convocar, organizar o influir para la acción colectiva.",
    },
    "humor": {
        "label": "Humor y Discurso Figurativo",
        "descripcion": "Usar ironía, sarcasmo, parodia o recursos retóricos.",
    },
    "identidad": {
        "label": "Identidad y Pertenencia",
        "descripcion": "Expresar orgullo local, barrial, municipal o nacional.",
    },
    "interaccion": {
        "label": "Interacción Conversacional",
        "descripcion": "Responder, mencionar usuarios o mantener la conversación.",
    },
    "enganoso": {
        "label": "Contenido Potencialmente Engañoso",
        "descripcion": "Rumores, especulación, insinuaciones o afirmaciones sin evidencia.",
    },
}

# ---------------------------------------------------------------------------
# Semillas de intención por familia (códigos IC-XXXX de A01)
#
# Para familias con tabla detallada (I-IV): usamos los códigos IC del doc.
# Para familias sin tabla detallada (V-VIII en 14.3): usamos IC-XXXX
# derivados de la sección 14.3 o descriptivos.
# Para familias solo mencionadas en 14.3 (IX-XII): usamos códigos
# descriptivos basados en los bullets de ejemplo.
# ---------------------------------------------------------------------------
INTENCIONES = {
    # Familia I — Información y Descripción (A01 §17)
    "IC-0101": {"familia": "informacion", "label": "Describir"},
    "IC-0102": {"familia": "informacion", "label": "Informar"},
    "IC-0103": {"familia": "informacion", "label": "Explicar"},
    "IC-0104": {"familia": "informacion", "label": "Detallar"},
    "IC-0105": {"familia": "informacion", "label": "Contextualizar"},
    "IC-0106": {"familia": "informacion", "label": "Resumir"},
    "IC-0107": {"familia": "informacion", "label": "Citar fuentes"},
    "IC-0108": {"familia": "informacion", "label": "Preguntar por datos"},
    "IC-0109": {"familia": "informacion", "label": "Comparar información"},
    "IC-0110": {"familia": "informacion", "label": "Actualiz"},

    # Familia II — Evaluación (A01 §18)
    "IC-0201": {"familia": "evaluacion", "label": "Valorar"},
    "IC-0202": {"familia": "evaluacion", "label": "Aprobar"},
    "IC-0203": {"familia": "evaluacion", "label": "Crit"},
    "IC-0204": {"familia": "evaluacion", "label": "Sugerir"},
    "IC-0205": {"familia": "evaluacion", "label": "Recomendar"},
    "IC-0206": {"familia": "evaluacion", "label": "Cuestionar"},
    "IC-0207": {"familia": "evaluacion", "label": "Comparar"},
    "IC-0208": {"familia": "evaluacion", "label": "Evaluar calidad"},
    "IC-0209": {"familia": "evaluacion", "label": "Evaluar efectividad"},
    "IC-0210": {"familia": "evaluacion", "label": "Evaluar impacto"},

    # Familia III — Solicitud e Intervención (A01 §19)
    "IC-0301": {"familia": "solicitud", "label": "Solicitar"},
    "IC-0302": {"familia": "solicitud", "label": "Pedir acción"},
    "IC-0303": {"familia": "solicitud", "label": "Exigir"},
    "IC-0304": {"familia": "solicitud", "label": "Demandar"},
    "IC-0305": {"familia": "solicitud", "label": "Solicitar información"},
    "IC-0306": {"familia": "solicitud", "label": "Pedir justicia"},
    "IC-0307": {"familia": "solicitud", "label": "Solicitar mejora"},
    "IC-0308": {"familia": "solicitud", "label": "Pedir reparación"},
    "IC-0309": {"familia": "solicitud", "label": "Proponer solución"},
    "IC-0310": {"familia": "solicitud", "label": "Solicitar audiencia"},

    # Familia IV — Fiscalización Ciudadana (A01 §20)
    "IC-0401": {"familia": "fiscalizacion", "label": "Exigir transparencia"},
    "IC-0402": {"familia": "fiscalizacion", "label": "Denunciar"},
    "IC-0403": {"familia": "fiscalizacion", "label": "Señalar irregularidad"},
    "IC-0404": {"familia": "fiscalizacion", "label": "Exigir rendición de cuentas"},
    "IC-0405": {"familia": "fiscalizacion", "label": "Cuestionar uso de recursos"},
    "IC-0406": {"familia": "fiscalizacion", "label": "Alertar sobre riesgo"},
    "IC-0407": {"familia": "fiscalizacion", "label": "Verificar información"},
    "IC-0408": {"familia": "fiscalizacion", "label": "Solicitar auditoría"},
    "IC-0409": {"familia": "fiscalizacion", "label": "Exigir acciones correctivas"},
    "IC-0410": {"familia": "fiscalizacion", "label": "Monitorear cumplimiento"},

    # Familia V — Participación Cívica (A01 §21 — Participación Democrática)
    "IC-0501": {"familia": "participacion", "label": "Convocar a votar"},
    "IC-0502": {"familia": "participacion", "label": "Informar sobre proceso electoral"},
    "IC-0503": {"familia": "participacion", "label": "Promover participación"},
    "IC-0504": {"familia": "participacion", "label": "Invitar a debate público"},
    "IC-0505": {"familia": "participacion", "label": "Organizar comunitariamente"},
    "IC-0506": {"familia": "participacion", "label": "Convocar a consulta"},
    "IC-0507": {"familia": "participacion", "label": "Promover voto informado"},
    "IC-0508": {"familia": "participacion", "label": "Invitar a observar elecciones"},
    "IC-0509": {"familia": "participacion", "label": "Convocar asamblea"},
    "IC-0510": {"familia": "participacion", "label": "Promover candidatura ciudadana"},

    # Familia VI — Deliberación (A01 §22 — Deliberación y Argumentación)
    "IC-0601": {"familia": "deliberacion", "label": "Argumentar"},
    "IC-0602": {"familia": "deliberacion", "label": "Justificar"},
    "IC-0603": {"familia": "deliberacion", "label": "Explicar razonamiento"},
    "IC-0604": {"familia": "deliberacion", "label": "Convencer"},
    "IC-0605": {"familia": "deliberacion", "label": "Refutar"},
    "IC-0606": {"familia": "deliberacion", "label": "Debatir"},
    "IC-0607": {"familia": "deliberacion", "label": "Interpretar"},
    "IC-0608": {"familia": "deliberacion", "label": "Contextualizar debate"},
    "IC-0609": {"familia": "deliberacion", "label": "Fundamentar"},
    "IC-0610": {"familia": "deliberacion", "label": "Razonar"},

    # Familia VII — Expresión Social (A01 §23 — Expresión Social y Vinculación)
    "IC-0701": {"familia": "expresion_social", "label": "Agradecer"},
    "IC-0702": {"familia": "expresion_social", "label": "Felicitar"},
    "IC-0703": {"familia": "expresion_social", "label": "Reconocer"},
    "IC-0704": {"familia": "expresion_social", "label": "Apoyar emocionalmente"},
    "IC-0705": {"familia": "expresion_social", "label": "Solidarizarse"},
    "IC-0706": {"familia": "expresion_social", "label": "Saludar"},
    "IC-0707": {"familia": "expresion_social", "label": "Despedirse"},
    "IC-0708": {"familia": "expresion_social", "label": "Consolar"},
    "IC-0709": {"familia": "expresion_social", "label": "Celebrar"},
    "IC-0710": {"familia": "expresion_social", "label": "Expresar buenos deseos"},

    # Familia VIII — Movilización (A01 §24 — Movilización e Influencia)
    "IC-0801": {"familia": "movilizacion", "label": "Convocar"},
    "IC-0802": {"familia": "movilizacion", "label": "Invitar a actuar"},
    "IC-0803": {"familia": "movilizacion", "label": "Movilizar"},
    "IC-0804": {"familia": "movilizacion", "label": "Organizar"},
    "IC-0805": {"familia": "movilizacion", "label": "Coordinar"},
    "IC-0806": {"familia": "movilizacion", "label": "Promover campaña"},
    "IC-0807": {"familia": "movilizacion", "label": "Difundir campaña"},
    "IC-0808": {"familia": "movilizacion", "label": "Persuadir para actuar"},
    "IC-0809": {"familia": "movilizacion", "label": "Incentivar participación"},
    "IC-0810": {"familia": "movilizacion", "label": "Llamar a la acción"},

    # Familia IX — Humor y Discurso Figurativo (A01 §14.3)
    # Solo bullets de ejemplo en el documento; códigos derivados.
    "hum-01": {"familia": "humor", "label": "Ironizar"},
    "hum-02": {"familia": "humor", "label": "Usar sarcasmo"},
    "hum-03": {"familia": "humor", "label": "Satirizar"},
    "hum-04": {"familia": "humor", "label": "Exagerar"},
    "hum-05": {"familia": "humor", "label": "Ridiculizar"},
    "hum-06": {"familia": "humor", "label": "Realizar humor"},
    "hum-07": {"familia": "humor", "label": "Utilizar doble sentido"},
    "hum-08": {"familia": "humor", "label": "Emplear parodia"},

    # Familia X — Identidad y Pertenencia (A01 §14.3)
    "id-01": {"familia": "identidad", "label": "Orgullo local"},
    "id-02": {"familia": "identidad", "label": "Identidad barrial"},
    "id-03": {"familia": "identidad", "label": "Identidad municipal"},
    "id-04": {"familia": "identidad", "label": "Identidad institucional"},
    "id-05": {"familia": "identidad", "label": "Identidad nacional"},
    "id-06": {"familia": "identidad", "label": "Sentido de pertenencia"},
    "id-07": {"familia": "identidad", "label": "Reconocimiento comunitario"},

    # Familia XI — Interacción Conversacional (A01 §14.3)
    "int-01": {"familia": "interaccion", "label": "Responder"},
    "int-02": {"familia": "interaccion", "label": "Mencionar usuarios"},
    "int-03": {"familia": "interaccion", "label": "Continuar conversación"},
    "int-04": {"familia": "interaccion", "label": "Pedir aclaraciones"},
    "int-05": {"familia": "interaccion", "label": "Confirmar recepción"},
    "int-06": {"familia": "interaccion", "label": "Corregir información"},
    "int-07": {"familia": "interaccion", "label": "Ampliar respuestas"},

    # Familia XII — Contenido Potencialmente Engañoso (A01 §14.3)
    "eng-01": {"familia": "enganoso", "label": "Rumor"},
    "eng-02": {"familia": "enganoso", "label": "Especulación"},
    "eng-03": {"familia": "enganoso", "label": "Insinuación"},
    "eng-04": {"familia": "enganoso", "label": "Afirmación sin evidencia"},
    "eng-05": {"familia": "enganoso", "label": "Descontextualización"},
    "eng-06": {"familia": "enganoso", "label": "Narrativa conspirativa"},
}

INTENCIONES_VALIDAS = set(INTENCIONES.keys())

# Claves familiares (aliases) para normalización flexible de la familia.
_FAMILIA_ALIASES = {
    "información": "informacion",
    "evaluación": "evaluacion",
    "solicitud": "solicitud",
    "fiscalización": "fiscalizacion",
    "participación": "participacion",
    "deliberación": "deliberacion",
    "expresión social": "expresion_social",
    "movilización": "movilizacion",
    "humor": "humor",
    "identidad": "identidad",
    "interacción": "interaccion",
    "interaccion": "interaccion",
    "contenido engañoso": "enganoso",
    "engañoso": "enganoso",
    "informacion_descripcion": "informacion",
    "evaluacion_juicio": "evaluacion",
    "solicitud_intervencion": "solicitud",
    "fiscalizacion_ciudadana": "fiscalizacion",
    "participacion_civica": "participacion",
    "deliberacion_argumentacion": "deliberacion",
    "expresion_social_vinculacion": "expresion_social",
    "movilizacion_influencia": "movilizacion",
    "humor_discurso_figurativo": "humor",
    "identidad_pertenencia": "identidad",
    "interaccion_conversacional": "interaccion",
    "contenido_potencialmente_enganoso": "enganoso",
}


def _normalizar_familia(familia):
    """Normaliza una clave de familia a su forma canónica.

    Devuelve la clave canónica o la original si no se reconoce.
    """
    f = str(familia).strip().lower()
    return _FAMILIA_ALIASES.get(f, f)


def _registrar_propuesta(tipo, clave, familia, ejemplo=""):
    """Registra una propuesta nueva en taxonomias_pendientes.json.

    Deduplica por ``(tipo, clave)'' y registra un máximo de
    ``_MAX_PROPUESTAS_POR_CLAVE`` entradas por clave.
    """
    _MAX_PROPUESTAS_POR_CLAVE = 3
    ruta = Path(__file__).resolve().parent / "taxonomias_pendientes.json"
    try:
        registros = json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        registros = []

    existing = [r for r in registros if r.get("tipo") == tipo and r.get("clave_propuesta") == clave]
    if len(existing) >= _MAX_PROPUESTAS_POR_CLAVE:
        return

    from datetime import datetime, timezone
    registros.append({
        "tipo": tipo,
        "clave_propuesta": clave,
        "familia_mas_cercana": familia,
        "ejemplo_texto": str(ejemplo)[:200],
        "fecha": datetime.now(timezone.utc).isoformat(),
        "estado": "pendiente",
    })
    ruta.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")


def normalizar_intencion(intencion, *, estricto=False, familia_sugerida=None):
    """Devuelve un código de intención canónico o la clave propuesta.

    Acepta None, códigos IC-XXXX, sinónimos, mayúsculas/espacios.

    - Si ``intencion`` está en INTENCIONES_VALIDAS, devuelve la clave tal cual.
    - Si no está reconocida y estricto es False (por defecto): registra la
      propuesta en taxonomias_pendientes.json con la familia más cercana y
      devuelve la clave propuesta tal cual (no-canónica). Nunca fuerza a un
      valor por defecto.
    - Si estricto es True: lanza ValueError (útil para depuración manual).
    - None devuelve None (sin intención asignada).

    ``familia_sugerida`` permite al llamador indicar la familia A01 conocida
    para una intención nueva. Si no se da, se usa "informacion" como familia
    por defecto (la más genérica del catálogo).
    """
    if not intencion:
        return None
    i = str(intencion).strip()
    i_lower = i.lower()

    if i_lower in INTENCIONES_VALIDAS:
        return i_lower

    if estricto:
        raise ValueError(
            f"Intención '{intencion}' no reconocida.  "
            f"Valores válidos: {sorted(INTENCIONES_VALIDAS)}"
        )

    familia = _normalizar_familia(familia_sugerida) if familia_sugerida else "informacion"
    if familia not in FAMILIAS_INTENCION:
        familia = "informacion"
    _registrar_propuesta("intencion", i_lower, familia, ejemplo=str(intencion))
    return i_lower


def etiqueta_intencion(codigo):
    """Etiqueta legible para un código de intención.

    Si el código no está en el catálogo, devuelve el código tal cual.
    """
    if codigo in INTENCIONES:
        return INTENCIONES[codigo]["label"]
    return str(codigo).strip().capitalize() if codigo else ""


def etiqueta_familia_intencion(codigo_familia):
    """Etiqueta legible para un código de familia de intención.

    Si la familia no está en el catálogo, devuelve la clave tal cual.
    """
    f = _normalizar_familia(codigo_familia)
    if f in FAMILIAS_INTENCION:
        return FAMILIAS_INTENCION[f]["label"]
    return str(codigo_familia).strip().capitalize() if codigo_familia else ""
