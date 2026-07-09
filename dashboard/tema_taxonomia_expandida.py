"""Catálogo de emociones robustecido para bloque1.indice_emociones.

Investigación de base: modelo de Plutchik (8 emociones primarias, cada una con
un derivado "leve" y uno "intenso") + las 8 díadas/emociones secundarias que
resultan de combinar dos primarias adyacentes, más las emociones específicas
de conversación cívica/política que ya existían en el dashboard (reclamo,
objeción, satisfacción, calma, reconocimiento, ironía, preocupación), que se
conservan como categoría aparte porque no son "emociones básicas" sino
posturas discursivas.

Esto sube el catálogo de 10 a 31 categorías, agrupadas por familia, sin perder
compatibilidad: las 10 claves viejas siguen existiendo (con su mismo texto),
solo se les asigna una familia y una intensidad.

Uso:
    from tema_taxonomia_expandida import EMOCIONES, EMOCIONES_VALIDAS, familia_de

Cada valor de EMOCIONES es un dict:
    {
        "label": "Nombre en español",
        "familia": "joy|trust|fear|surprise|sadness|disgust|anger|anticipation|diada|civica",
        "intensidad": "leve|media|intensa" (solo aplica a familias primarias),
        "deriva_de": ["clave1", "clave2"]  (solo para díadas: de qué dos primarias nace),
        "descripcion": "qué significa en el contexto de un comentario ciudadano",
    }
"""

EMOCIONES = {
    # ------------------------------------------------------------------
    # FAMILIA: ALEGRÍA (joy) — espectro de leve a intenso
    # ------------------------------------------------------------------
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
        "descripcion": "Entusiasmo desbordado, celebración explícita (\"excelente\", \"increíble\", muchos signos de exclamación).",
    },
    # ------------------------------------------------------------------
    # FAMILIA: CONFIANZA (trust)
    # ------------------------------------------------------------------
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
    # ------------------------------------------------------------------
    # FAMILIA: MIEDO (fear)
    # ------------------------------------------------------------------
    "aprension": {
        "label": "Aprensión", "familia": "fear", "intensidad": "leve",
        "descripcion": "Duda o inquietud leve sobre lo que puede pasar.",
    },
    "preocupacion": {
        "label": "Preocupación", "familia": "fear", "intensidad": "media",
        "descripcion": "Inquietud explícita por un riesgo o problema concreto (ya existía en el catálogo original).",
    },
    "terror": {
        "label": "Terror / Pánico", "familia": "fear", "intensidad": "intensa",
        "descripcion": "Miedo extremo, lenguaje de alarma o emergencia (inseguridad, catástrofe).",
    },
    # ------------------------------------------------------------------
    # FAMILIA: SORPRESA (surprise)
    # ------------------------------------------------------------------
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
        "descripcion": "Sorpresa muy marcada, puede ser admiración o escándalo (categoría ambigua, ya existía en dash_ui como reacción de Facebook).",
    },
    # ------------------------------------------------------------------
    # FAMILIA: TRISTEZA (sadness)
    # ------------------------------------------------------------------
    "melancolia": {
        "label": "Melancolía", "familia": "sadness", "intensidad": "leve",
        "descripcion": "Tono apagado, resignación leve.",
    },
    "tristeza": {
        "label": "Tristeza", "familia": "sadness", "intensidad": "media",
        "descripcion": "Pesar explícito frente a una noticia o situación (ya existía en el catálogo original).",
    },
    "dolor": {
        "label": "Dolor / Pena profunda", "familia": "sadness", "intensidad": "intensa",
        "descripcion": "Duelo o pesar intenso (pérdidas, tragedias, luto).",
    },
    # ------------------------------------------------------------------
    # FAMILIA: DESAGRADO / ASCO (disgust)
    # ------------------------------------------------------------------
    "aburrimiento": {
        "label": "Aburrimiento / Indiferencia", "familia": "disgust", "intensidad": "leve",
        "descripcion": "Desinterés, comentario desganado.",
    },
    "desagrado": {
        "label": "Desagrado", "familia": "disgust", "intensidad": "media",
        "descripcion": "Rechazo explícito, algo \"no gusta\" sin llegar a la indignación.",
    },
    "repulsion": {
        "label": "Repulsión / Indignación moral", "familia": "disgust", "intensidad": "intensa",
        "descripcion": "Rechazo fuerte, lenguaje de asco o condena moral (\"qué vergüenza\", \"asco\").",
    },
    # ------------------------------------------------------------------
    # FAMILIA: ENOJO (anger)
    # ------------------------------------------------------------------
    "fastidio": {
        "label": "Fastidio / Molestia", "familia": "anger", "intensidad": "leve",
        "descripcion": "Irritación leve, queja sin agresividad.",
    },
    "enojo": {
        "label": "Enojo", "familia": "anger", "intensidad": "media",
        "descripcion": "Molestia clara y directa (ya existía en el catálogo original).",
    },
    "furia": {
        "label": "Furia / Ira", "familia": "anger", "intensidad": "intensa",
        "descripcion": "Enojo extremo, insultos, mayúsculas, lenguaje agresivo.",
    },
    # ------------------------------------------------------------------
    # FAMILIA: ANTICIPACIÓN (anticipation)
    # ------------------------------------------------------------------
    "interes": {
        "label": "Interés", "familia": "anticipation", "intensidad": "leve",
        "descripcion": "Curiosidad o atención hacia lo publicado, preguntas.",
    },
    "expectativa": {
        "label": "Expectativa", "familia": "anticipation", "intensidad": "media",
        "descripcion": "Comentario que anticipa un resultado o pide seguimiento (\"esperamos que...\").",
    },
    "vigilancia": {
        "label": "Vigilancia / Alerta expectante", "familia": "anticipation", "intensidad": "intensa",
        "descripcion": "Seguimiento atento y desconfiado (\"vamos a ver si esta vez sí cumplen\").",
    },
    # ------------------------------------------------------------------
    # DÍADAS (combinación de dos primarias adyacentes en la rueda de Plutchik)
    # ------------------------------------------------------------------
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
        "descripcion": "Sorpresa + tristeza: \"no puedo creer que hicieran esto\", decepción.",
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
        "descripcion": "Enojo + anticipación: amenaza o confrontación activa (\"esto no se va a quedar así\").",
    },
    # ------------------------------------------------------------------
    # FAMILIA CÍVICA (posturas discursivas, no emociones básicas — se
    # conservan del catálogo original porque describen el TIPO de mensaje,
    # no un afecto puro)
    # ------------------------------------------------------------------
    "reclamo": {
        "label": "Reclamo", "familia": "civica",
        "descripcion": "Exige una acción o respuesta concreta de la institución.",
    },
    "objecion": {
        "label": "Objeción", "familia": "civica",
        "descripcion": "Cuestiona una decisión o dato sin necesariamente exigir acción.",
    },
    "satisfaccion": {
        "label": "Satisfacción", "familia": "civica",
        "descripcion": "Declara conformidad con un resultado o servicio concreto.",
    },
    "calma": {
        "label": "Calma", "familia": "civica",
        "descripcion": "Tono neutro, informativo, sin carga emocional relevante.",
    },
    "reconocimiento": {
        "label": "Reconocimiento", "familia": "civica",
        "descripcion": "Agradece o felicita explícitamente una acción institucional.",
    },
    "ironia": {
        "label": "Ironía / Sarcasmo", "familia": "civica",
        "descripcion": "Crítica indirecta disfrazada de elogio o burla.",
    },
}

# Compatibilidad con el catálogo anterior (10 claves) — se mantienen igual.
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

# Sinónimos frecuentes que puede devolver el modelo -> emoción canónica.
# Fusionados del catálogo original tema_taxonomia.py.
_EMOCION_SINONIMOS = {
    "queja": "reclamo",
    "reclamos": "reclamo",
    "objeción": "objecion",
    "objetar": "objecion",
    "satisfacción": "satisfaccion",
    "satisfecho": "satisfaccion",
    "enojo": "enojo",
    "enojado": "enojo",
    "rabia": "enojo",
    "triste": "tristeza",
    "tristeza": "tristeza",
    "alegre": "alegria",
    "alegría": "alegria",
    "feliz": "alegria",
    "felicidad": "alegria",
    "reconocimiento": "reconocimiento",
    "agradecimiento": "reconocimiento",
    "gratitud": "reconocimiento",
    "ironía": "ironia",
    "ironico": "ironia",
    "irónico": "ironia",
    "burla": "ironia",
    "preocupación": "preocupacion",
    "preocupado": "preocupacion",
    "inquietud": "preocupacion",
    "calma": "calma",
    "tranquilidad": "calma",
    "tranquilo": "calma",
}


def familia_de(clave_emocion: str) -> str:
    return EMOCIONES.get(clave_emocion, {}).get("familia", "civica")


def emociones_por_familia() -> dict:
    """Agrupa las claves de emoción por familia, en el orden de la rueda de
    Plutchik seguido de díadas y posturas cívicas. Útil para poblar el
    selector de la UI (02 · Índice de Emociones) con secciones.
    """
    orden_familias = ["joy", "trust", "fear", "surprise", "sadness",
                       "disgust", "anger", "anticipation", "diada", "civica"]
    agrupado = {f: [] for f in orden_familias}
    for clave, meta in EMOCIONES.items():
        agrupado[meta["familia"]].append(clave)
    return {f: agrupado[f] for f in orden_familias if agrupado[f]}


def normalizar_emocion(emocion):
    """Devuelve una emoción canónica (31 emociones expandidas).

    Acepta None, sinónimos, mayúsculas/espacios. Valor desconocido cae a
    EMOCION_DEFAULT ("calma").
    """
    if not emocion:
        return EMOCION_DEFAULT
    e = str(emocion).strip().lower()
    if e in EMOCIONES_VALIDAS:
        return e
    return _EMOCION_SINONIMOS.get(e, EMOCION_DEFAULT)
