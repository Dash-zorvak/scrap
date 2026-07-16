"""Taxonomia englobante de temas ciudadanos (fuente unica de verdad).

En vez de que la IA descubra temas libremente, definimos por defecto un conjunto
pequeno de temas ENGLOBANTES. Algunos temas historicos se fusionan aqui:

  - obras_publicas + servicios_publicos -> obras_servicios
  - corrupcion + transparencia          -> gobernanza
  - cultura + deportes                  -> cultura_deportes

Se mantienen separados los que son preocupaciones claramente distintas
(seguridad, salud, educacion, empleo, movilidad, medio_ambiente).

IMPORTANTE - los temas son NEUTRALES: describen el ASUNTO del comentario, no si
es positivo o negativo. Un mismo tema puede aparecer en apoyo, en critica o de
forma neutral. La POLARIDAD vive en un eje SEPARADO (ver POSTURAS): asi una
queja sobre, por ejemplo, gobernanza se clasifica en 'gobernanza' con postura
'critica' y NO se contabiliza como un impulso positivo del tema.

`REMAP_LEGACY` traduce las 13 claves antiguas a estas claves englobantes, de modo
que NO hace falta tocar src/analyzer/topic_detection.py (cuyos tests dependen de
las claves viejas): el remapeo se aplica en la capa nueva.

Modulo puro (sin dependencias externas), facil de probar.
"""

# clave englobante -> {label legible, desc para el prompt de la IA}
TEMAS = {
    "obras_servicios": {
        "label": "Obras y servicios públicos",
        "desc": "calles, baches, parques, puentes, construccion, agua potable, "
        "luz, basura, alcantarillado, alumbrado y tramites municipales.",
    },
    "seguridad": {
        "label": "Seguridad",
        "desc": "delincuencia, robos, pandillas, violencia, policia y vigilancia.",
    },
    "movilidad": {
        "label": "Movilidad y transporte",
        "desc": "trafico, buses, rutas, semaforos, accidentes, transporte publico "
        "y estacionamiento.",
    },
    "empleo": {
        "label": "Empleo y economía",
        "desc": "trabajo, empleo, negocios, emprendimiento, economia y salarios.",
    },
    "salud": {
        "label": "Salud",
        "desc": "hospitales, clinicas, medicinas, jornadas medicas y enfermedades.",
    },
    "educacion": {
        "label": "Educación",
        "desc": "escuelas, maestros, becas, estudiantes y materiales escolares.",
    },
    "medio_ambiente": {
        "label": "Medio ambiente",
        "desc": "contaminacion, rios, arboles, reforestacion, desechos y areas verdes.",
    },
    "gobernanza": {
        "label": "Transparencia y confianza",
        "desc": "corrupcion, fraude, mal gobierno, abuso de poder, presupuesto, "
        "rendicion de cuentas, gestion municipal y desconfianza hacia las "
        "autoridades (incluye reclamos, criticas y burlas sobre la honestidad o "
        "el manejo del gobierno local).",
    },
    "cultura_deportes": {
        "label": "Cultura y deportes",
        "desc": "eventos, fiestas, festivales, tradiciones, conciertos, canchas, "
        "torneos y deportistas.",
    },
    "apoyo_generico": {
        "label": "Mensajes de apoyo",
        "desc": "felicitaciones, bendiciones o 'buen trabajo' SIN un tema concreto.",
    },
    "no_aplica": {
        "label": "Sin tema municipal",
        "desc": "NO habla de ningun asunto municipal: dichos, refranes, bromas, "
        "sarcasmo sin tema, saludos, etiquetar a alguien, spam o texto sin sentido.",
    },
}

CATEGORIAS_VALIDAS = set(TEMAS.keys())

# Temas que se muestran como tarjeta (todo menos 'no_aplica').
TEMAS_VISIBLES = [k for k in TEMAS if k != "no_aplica"]

TEMA_LABELS = {k: v["label"] for k, v in TEMAS.items()}

# ---------------------------------------------------------------------------
# Postura (polaridad) de una mencion de tema.
#
# Es un EJE SEPARADO del tema. El tema dice DE QUE habla el comentario; la
# postura dice COMO lo dice respecto a la alcaldia/gestion:
#   - apoyo:   felicita, agradece, respalda o defiende.
#   - critica: reclama, se queja, expresa enojo, reprocha o se burla.
#   - neutral: pregunta o comenta sin una postura clara a favor o en contra.
#
# Mantener la polaridad aparte evita que una critica sobre un tema infle ese
# tema como si fuera impulso positivo (lo que distorsionaba los calculos).
# ---------------------------------------------------------------------------
POSTURAS = {
    "apoyo": "Apoyo",
    "critica": "Crítica",
    "neutral": "Neutral",
}

POSTURAS_VALIDAS = set(POSTURAS.keys())
POSTURA_LABELS = dict(POSTURAS)
POSTURA_DEFAULT = "neutral"

# Sinonimos frecuentes que puede devolver el modelo -> postura canonica.
_POSTURA_SINONIMOS = {
    "positivo": "apoyo", "positiva": "apoyo", "favor": "apoyo",
    "a_favor": "apoyo", "afavor": "apoyo", "elogio": "apoyo",
    "negativo": "critica", "negativa": "critica", "critico": "critica",
    "crítica": "critica", "crítico": "critica", "queja": "critica",
    "reclamo": "critica", "enojo": "critica", "en_contra": "critica",
    "neutro": "neutral", "neutra": "neutral", "": "neutral",
}


# Las 13 categorias historicas -> claves englobantes nuevas.
REMAP_LEGACY = {
    "obras_publicas": "obras_servicios",
    "servicios_publicos": "obras_servicios",
    "seguridad": "seguridad",
    "empleo": "empleo",
    "salud": "salud",
    "educacion": "educacion",
    "movilidad": "movilidad",
    "corrupcion": "gobernanza",
    "transparencia": "gobernanza",
    "medio_ambiente": "medio_ambiente",
    "cultura": "cultura_deportes",
    "deportes": "cultura_deportes",
    "apoyo_generico": "apoyo_generico",
    "no_aplica": "no_aplica",
}


def remapear(cat):
    """Devuelve la clave englobante para una categoria (nueva o historica).

    - Cadena vacia / None -> "" (sin tema detectado).
    - Clave ya englobante -> se devuelve igual.
    - Clave historica conocida -> su englobante.
    - Cualquier otra cosa -> "no_aplica".
    """
    if not cat:
        return ""
    if cat in CATEGORIAS_VALIDAS:
        return cat
    return REMAP_LEGACY.get(cat, "no_aplica")


def etiqueta_tema(cat):
    """Etiqueta legible para una categoria (acepta claves historicas)."""
    cat2 = remapear(cat)
    if cat2 in TEMA_LABELS:
        return TEMA_LABELS[cat2]
    if cat:
        return str(cat).replace("_", " ").capitalize()
    return "Sin clasificar"


def normalizar_postura(postura):
    """Devuelve una postura canonica (apoyo/critica/neutral).

    Acepta None, sinonimos comunes del modelo y mayusculas/espacios.
    Lanza ValueError si la postura no es reconocida (H-DS1: sin normalizacion
    silenciosa).  None devuelve POSTURA_DEFAULT ("neutral").
    """
    if not postura:
        return POSTURA_DEFAULT
    p = str(postura).strip().lower()
    if p in POSTURAS_VALIDAS:
        return p
    resultado = _POSTURA_SINONIMOS.get(p)
    if resultado is not None:
        return resultado
    raise ValueError(
        f"Postura '{postura}' no reconocida.  "
        f"Valores validos: {sorted(POSTURAS_VALIDAS)}"
    )


def etiqueta_postura(postura):
    """Etiqueta legible para una postura (acepta sinonimos / None).

    Si la postura no es reconocida, devuelve la postura original sin formato.
    """
    try:
        norm = normalizar_postura(postura)
        return POSTURA_LABELS.get(norm, POSTURA_LABELS[POSTURA_DEFAULT])
    except ValueError:
        return str(postura).strip().capitalize() if postura else POSTURA_LABELS[POSTURA_DEFAULT]


# ---------------------------------------------------------------------------
# Catálogo de emociones — Plutchik expandido (31 categorías).
#
# Fuente: modelo de Plutchik (8 emociones primarias, leve/media/intensa)
# + 8 díadas secundarias + posturas cívicas del catálogo original.
# Las 10 claves legacy se conservan idénticas.
# ---------------------------------------------------------------------------
EMOCIONES = {
    # Familia: ALEGRÍA (joy)
    "serenidad": {
        "label": "Serenidad", "familia": "joy", "intensidad": "leve",
        "descripcion": "Comentario positivo, tranquilo, sin entusiasmo marcado.",
    },
    "alegria": {
        "label": "Alegría", "familia": "joy", "intensidad": "media",
        "descripcion": "Comentario que expresa contento o satisfacción emocional visible.",
    },
    "euforia": {
        "label": "Euforia", "familia": "joy", "intensidad": "intensa",
        "descripcion": "Entusiasmo desbordado, celebración explícita.",
    },
    # Familia: CONFIANZA (trust)
    "aceptacion": {
        "label": "Aceptación", "familia": "trust", "intensidad": "leve",
        "descripcion": "Conformidad neutra con lo publicado, sin objeción.",
    },
    "confianza": {
        "label": "Confianza", "familia": "trust", "intensidad": "media",
        "descripcion": "Respaldo explícito a la gestión o la fuente de la información.",
    },
    "admiracion": {
        "label": "Admiración", "familia": "trust", "intensidad": "intensa",
        "descripcion": "Reconocimiento elevado, elogio directo a una persona o acción.",
    },
    # Familia: MIEDO (fear)
    "aprension": {
        "label": "Aprensión", "familia": "fear", "intensidad": "leve",
        "descripcion": "Duda o inquietud leve sobre lo que puede pasar.",
    },
    "preocupacion": {
        "label": "Preocupación", "familia": "fear", "intensidad": "media",
        "descripcion": "Inquietud explícita por un riesgo o problema concreto.",
    },
    "terror": {
        "label": "Terror", "familia": "fear", "intensidad": "intensa",
        "descripcion": "Miedo extremo ante una amenaza concreta y percibida como real.",
    },
    "panico": {
        "label": "Pánico", "familia": "fear", "intensidad": "intensa",
        "descripcion": "Reacción de alarma generalizada, sin amenaza concreta identificable.",
    },
    # Familia: SORPRESA (surprise)
    "distraccion": {
        "label": "Distracción", "familia": "surprise", "intensidad": "leve",
        "descripcion": "Comentario que nota algo inesperado sin darle mayor peso.",
    },
    "sorpresa": {
        "label": "Sorpresa", "familia": "surprise", "intensidad": "media",
        "descripcion": "Reacción de asombro ante un anuncio o dato no esperado.",
    },
    "asombro": {
        "label": "Asombro", "familia": "surprise", "intensidad": "intensa",
        "descripcion": "Sorpresa muy marcada, puede ser admiración o escándalo.",
    },
    # Familia: TRISTEZA (sadness)
    "melancolia": {
        "label": "Melancolía", "familia": "sadness", "intensidad": "leve",
        "descripcion": "Tono apagado, resignación leve.",
    },
    "tristeza": {
        "label": "Tristeza", "familia": "sadness", "intensidad": "media",
        "descripcion": "Pesar explícito frente a una noticia o situación.",
    },
    "dolor": {
        "label": "Dolor", "familia": "sadness", "intensidad": "intensa",
        "descripcion": "Duelo o pesar intenso por una pérdida o tragedia concreta.",
    },
    "pena_profunda": {
        "label": "Pena profunda", "familia": "sadness", "intensidad": "intensa",
        "descripcion": "Luto colectivo, conmoción por hechos que afectan a la comunidad.",
    },
    # Familia: DESAGRADO / ASCO (disgust)
    "aburrimiento": {
        "label": "Aburrimiento", "familia": "disgust", "intensidad": "leve",
        "descripcion": "Desinterés manifiesto, comentario desganado sobre el tema.",
    },
    "indiferencia": {
        "label": "Indiferencia", "familia": "disgust", "intensidad": "leve",
        "descripcion": "Ausencia de reacción emocional, desapego explícito respecto al tema.",
    },
    "desagrado": {
        "label": "Desagrado", "familia": "disgust", "intensidad": "media",
        "descripcion": "Rechazo explícito, algo 'no gusta' sin llegar a la indignación.",
    },
    "repulsion": {
        "label": "Repulsión", "familia": "disgust", "intensidad": "intensa",
        "descripcion": "Rechazo visceral, lenguaje de asco ante lo percibido como inaceptable.",
    },
    "indignacion_moral": {
        "label": "Indignación moral", "familia": "disgust", "intensidad": "intensa",
        "descripcion": "Condena ética explícita, juicio de valor sobre una acción institucional.",
    },
    # Familia: ENOJO (anger)
    "fastidio": {
        "label": "Fastidio", "familia": "anger", "intensidad": "leve",
        "descripcion": "Irritación acumulada, hartazgo ante una situación repetida.",
    },
    "molestia": {
        "label": "Molestia", "familia": "anger", "intensidad": "leve",
        "descripcion": "Incomodidad puntual, queja sin agresividad ante un hecho concreto.",
    },
    "enojo": {
        "label": "Enojo", "familia": "anger", "intensidad": "media",
        "descripcion": "Molestia clara y directa.",
    },
    "furia": {
        "label": "Furia", "familia": "anger", "intensidad": "intensa",
        "descripcion": "Enojo extremo con expresión explosiva, insultos o mayúsculas.",
    },
    "ira": {
        "label": "Ira", "familia": "anger", "intensidad": "intensa",
        "descripcion": "Enojo profundo y sostenido, con carga de condena moral.",
    },
    # Familia: ANTICIPACIÓN (anticipation)
    "interes": {
        "label": "Interés", "familia": "anticipation", "intensidad": "leve",
        "descripcion": "Curiosidad o atención hacia lo publicado, preguntas.",
    },
    "expectativa": {
        "label": "Expectativa", "familia": "anticipation", "intensidad": "media",
        "descripcion": "Comentario que anticipa un resultado o pide seguimiento.",
    },
    "vigilancia": {
        "label": "Vigilancia", "familia": "anticipation", "intensidad": "intensa",
        "descripcion": "Seguimiento atento y desconfiado de una situación en desarrollo.",
    },
    "alerta_expectante": {
        "label": "Alerta expectante", "familia": "anticipation", "intensidad": "intensa",
        "descripcion": "Atención elevada ante un posible desenlace, con tono de advertencia.",
    },
    # DÍADAS (combinación de dos primarias adyacentes)
    "optimismo": {
        "label": "Optimismo", "familia": "diada", "deriva_de": ["anticipation", "joy"],
        "descripcion": "Anticipación + alegría: expectativa positiva explícita sobre el futuro.",
    },
    "amor_civico": {
        "label": "Cariño / Aprecio", "familia": "diada", "deriva_de": ["joy", "trust"],
        "descripcion": "Alegría + confianza: afecto y respaldo emocional combinados.",
    },
    "sumision": {
        "label": "Resignación conforme", "familia": "diada", "deriva_de": ["trust", "fear"],
        "descripcion": "Confianza + miedo: acepta la situación aunque le genera inquietud.",
    },
    "asombro_temeroso": {
        "label": "Sobrecogimiento", "familia": "diada", "deriva_de": ["fear", "surprise"],
        "descripcion": "Miedo + sorpresa: reacción de shock ante algo inesperado y alarmante.",
    },
    "desaprobacion": {
        "label": "Desaprobación", "familia": "diada", "deriva_de": ["surprise", "sadness"],
        "descripcion": "Sorpresa + tristeza: decepción ante algo inesperado.",
    },
    "remordimiento": {
        "label": "Remordimiento / Lamento", "familia": "diada", "deriva_de": ["sadness", "disgust"],
        "descripcion": "Tristeza + desagrado: lamento con rechazo hacia lo ocurrido.",
    },
    "desprecio": {
        "label": "Desprecio", "familia": "diada", "deriva_de": ["disgust", "anger"],
        "descripcion": "Desagrado + enojo: menosprecio combinado con hostilidad.",
    },
    "agresividad": {
        "label": "Agresividad", "familia": "diada", "deriva_de": ["anger", "anticipation"],
        "descripcion": "Enojo + anticipación: amenaza o confrontación activa.",
    },
    "envidia": {
        "label": "Envidia", "familia": "diada", "deriva_de": ["sadness", "anger"],
        "descripcion": "Tristeza + enojo: frustración por ver que otros reciben lo que uno desea.",
    },
    "culpa": {
        "label": "Culpa", "familia": "diada", "deriva_de": ["joy", "fear"],
        "descripcion": "Alegría + miedo: remordimiento por haber disfrutado algo que se percibe como indebido.",
    },
    "curiosidad": {
        "label": "Curiosidad", "familia": "diada", "deriva_de": ["trust", "surprise"],
        "descripcion": "Confianza + sorpresa: interés genuino por entender algo nuevo o inesperado.",
    },
    "esperanza": {
        "label": "Esperanza", "familia": "diada", "deriva_de": ["anticipation", "trust"],
        "descripcion": "Anticipación + confianza: expectativa positiva sustentada en credibilidad.",
    },
    "indignacion": {
        "label": "Indignación", "familia": "diada", "deriva_de": ["surprise", "anger"],
        "descripcion": "Sorpresa + enojo: reacción ante algo que se considera injusto o inaceptable.",
    },
    "incredulidad": {
        "label": "Incredulidad", "familia": "diada", "deriva_de": ["surprise", "disgust"],
        "descripcion": "Sorpresa + disgusto: incapacidad de aceptar algo percibido como falso o absurdo.",
    },
    "ansiedad": {
        "label": "Ansiedad", "familia": "diada", "deriva_de": ["anticipation", "fear"],
        "descripcion": "Anticipación + miedo: inquietud anticipatoria ante un resultado incierto.",
    },
    "pesimismo": {
        "label": "Pesimismo", "familia": "diada", "deriva_de": ["sadness", "anticipation"],
        "descripcion": "Tristeza + anticipación: expectativa negativa sobre el futuro.",
    },
    # POSTURAS CÍVICAS (del catálogo original)
    "reclamo": {
        "label": "Reclamo", "familia": "civica", "intensidad": "moderada",
        "descripcion": "Exige una acción o respuesta concreta de la institución.",
    },
    "objecion": {
        "label": "Objeción", "familia": "civica", "intensidad": "leve",
        "descripcion": "Cuestiona una decisión o dato sin necesariamente exigir acción.",
    },
    "satisfaccion": {
        "label": "Satisfacción", "familia": "civica", "intensidad": "moderada",
        "descripcion": "Declara conformidad con un resultado o servicio concreto.",
    },
    "calma": {
        "label": "Calma", "familia": "civica", "intensidad": "leve",
        "descripcion": "Tono neutro, informativo, sin carga emocional relevante.",
    },
    "reconocimiento": {
        "label": "Reconocimiento", "familia": "civica", "intensidad": "moderada",
        "descripcion": "Agradece o felicita explícitamente una acción institucional.",
    },
    "ironia": {
        "label": "Ironía / Sarcasmo", "familia": "civica", "intensidad": "moderada",
        "descripcion": "Crítica indirecta disfrazada de elogio o burla.",
    },
}

# Compatibilidad con el catálogo anterior (10 claves).
EMOCIONES_LEGACY = {
    "reclamo", "objecion", "satisfaccion", "calma", "enojo", "tristeza",
    "alegria", "reconocimiento", "ironia", "preocupacion",
}

EMOCIONES_VALIDAS = set(EMOCIONES.keys())
EMOCION_LABELS = {k: v["label"] for k, v in EMOCIONES.items()}
EMOCION_DEFAULT = "calma"

FAMILIAS_LABELS = {
    "joy": "Alegría", "trust": "Confianza", "fear": "Miedo",
    "surprise": "Sorpresa", "sadness": "Tristeza", "disgust": "Desagrado",
    "anger": "Enojo", "anticipation": "Anticipación",
    "diada": "Emociones combinadas", "civica": "Posturas cívicas",
}


def familia_de(clave_emocion: str) -> str:
    """Devuelve la familia de una emoción (joy, trust, …, civica)."""
    return EMOCIONES.get(clave_emocion, {}).get("familia", "civica")


def emociones_por_familia() -> dict:
    """Agrupa las claves de emoción por familia, en el orden de la rueda de
    Plutchik seguido de díadas y posturas cívicas.
    """
    orden_familias = ["joy", "trust", "fear", "surprise", "sadness",
                       "disgust", "anger", "anticipation", "diada", "civica"]
    agrupado = {f: [] for f in orden_familias}
    for clave, meta in EMOCIONES.items():
        agrupado[meta["familia"]].append(clave)
    return {f: agrupado[f] for f in orden_familias if agrupado[f]}


_EMOCION_SINONIMOS = {
    # Legadas
    "queja": "reclamo", "reclamos": "reclamo",
    "objeción": "objecion", "objetar": "objecion",
    "satisfacción": "satisfaccion", "satisfecho": "satisfaccion",
    "rabia": "enojo", "enojado": "enojo",
    "triste": "tristeza",
    "alegre": "alegria", "alegría": "alegria", "feliz": "alegria", "felicidad": "alegria",
    "agradecimiento": "reconocimiento", "gratitud": "reconocimiento",
    "ironico": "ironia", "irónico": "ironia", "burla": "ironia",
    "preocupado": "preocupacion", "inquietud": "preocupacion",
    "tranquilidad": "calma", "tranquilo": "calma",
    # Nuevas — Plutchik
    "sereno": "serenidad", "tranquilo": "calma",
    "eufórico": "euforia", "euforico": "euforia", "increíble": "euforia",
    "acepto": "aceptacion", "de acuerdo": "aceptacion",
    "confío": "confianza", "confio": "confianza", "respaldo": "confianza",
    "admiro": "admiracion", "bravo": "admiracion", "elogio": "admiracion",
    "aprensión": "aprension", "aprehensión": "aprension",
    "miedo": "terror", "pánico": "panico", "panico": "panico", "alarma": "panico",
    "pánico generalizado": "panico", "angustia extrema": "panico",
    "sorprendido": "sorpresa", "asombrado": "asombro",
    "melancólico": "melancolia", "melancolico": "melancolia",
    "pena": "dolor", "duelo": "dolor",
    "luto": "pena_profunda", "conmoción": "pena_profunda", "conmocion": "pena_profunda",
    "aburrido": "aburrimiento", "indiferente": "indiferencia",
    "disgusto": "desagrado", "me molesta": "desagrado",
    "asco": "repulsion", "vergüenza": "repulsion", "indignación": "repulsion",
    "indignación moral": "indignacion_moral", "conda moral": "indignacion_moral",
    "molesto": "molestia", "cansado de": "fastidio", "hartazgo": "fastidio",
    "furioso": "furia", "iracundo": "ira",
    "interesado": "interes", "curioso": "interes",
    "espero que": "expectativa", "a ver si": "expectativa",
    "vigilo": "vigilancia", "atento a": "alerta_expectante",
    "optimista": "optimismo",
    "cariño": "amor_civico", "aprecio": "amor_civico",
    "resignado": "sumision", "toca aceptar": "sumision",
    "sobrecogido": "asombro_temeroso",
    "decepcionado": "desaprobacion", "no puedo creer": "desaprobacion",
    "lamento": "remordimiento", "me arrepiento": "remordimiento",
    "desprecio": "desprecio", "menosprecio": "desprecio",
    "amenaza": "agresividad", "confrontación": "agresividad",
    "envidioso": "envidia", "le duele que": "envidia",
    "culpable": "culpa", "me siento culpable": "culpa",
    "curioso": "curiosidad", "quiero saber": "curiosidad",
    "espero": "esperanza", "confío en que": "esperanza", "ojalá": "esperanza",
    "indignado": "indignacion", "no es justo": "indignacion",
    "no puedo creer": "incredulidad", "imposible": "incredulidad",
    "ansioso": "ansiedad", "nervioso": "ansiedad", "inquietud anticipatoria": "ansiedad",
    "pesimista": "pesimismo", "no va a mejorar": "pesimismo",
}


def normalizar_emocion(emocion):
    """Devuelve una emoción canónica (31 categorías).

    Acepta None, sinónimos, mayúsculas/espacios.
    Lanza ValueError si la emoción no es reconocida (H-DS1: sin normalización
    silenciosa).  None devuelve EMOCION_DEFAULT ("calma").
    """
    if not emocion:
        return EMOCION_DEFAULT
    e = str(emocion).strip().lower()
    if e in EMOCIONES_VALIDAS:
        return e
    resultado = _EMOCION_SINONIMOS.get(e)
    if resultado is not None:
        return resultado
    raise ValueError(
        f"Emoción '{emocion}' no reconocida.  "
        f"Valores válidos: {sorted(EMOCIONES_VALIDAS)}"
    )
