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

---

CATALOGO ABIERTO (desde esta enmienda):

EMOCIONES y TEMAS son el punto de partida, no el techo. Cuando el texto real no
calza en ninguna clave existente, el sistema NO fuerza un valor por defecto ni
lanza error. En su lugar, registra la propuesta nueva en
``dashboard/taxonomias_pendientes.json`` con la familia o categoría más cercana
y devuelve la clave propuesta tal cual (marcada como no-canónica). Las claves
semilla se mantienen por compatibilidad con datos históricos.

Las familias de emociones (joy, trust, fear, surprise, sadness, disgust, anger,
anticipation, diada, civica) y los temas englobantes sí quedan fijos — son la
estructura. Las hojas dentro de cada familia dejan de estar cerradas.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_PENDIENTES_PATH = Path(__file__).resolve().parent / "taxonomias_pendientes.json"


def _cargar_pendientes():
    if _PENDIENTES_PATH.exists():
        with open(_PENDIENTES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _guardar_pendientes(lista):
    with open(_PENDIENTES_PATH, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def _registrar_propuesta(tipo, clave, familia, ejemplo=""):
    """Registra una propuesta nueva en taxonomias_pendientes.json.

    Evita duplicados: si la misma clave_propuesta + tipo ya está pendiente,
    no la vuelve a registrar.
    """
    pendientes = _cargar_pendientes()
    for p in pendientes:
        if p["tipo"] == tipo and p["clave_propuesta"] == clave and p["estado"] == "pendiente":
            return
    pendientes.append({
        "tipo": tipo,
        "clave_propuesta": clave,
        "familia_mas_cercana": familia,
        "ejemplo_texto": ejemplo,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "estado": "pendiente",
    })
    _guardar_pendientes(pendientes)


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
    - Cualquier otra cosa -> se propone como clave nueva y se registra en
      taxonomias_pendientes.json para revision. No se fuerza a 'no_aplica'.
    """
    if not cat:
        return ""
    if cat in CATEGORIAS_VALIDAS:
        return cat
    remapeada = REMAP_LEGACY.get(cat)
    if remapeada is not None:
        return remapeada
    _registrar_propuesta("tema", cat, "sin_familia", ejemplo=cat)
    return cat


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
        "label": "Terror / Pánico", "familia": "fear", "intensidad": "intensa",
        "descripcion": "Miedo extremo, lenguaje de alarma o emergencia.",
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
        "label": "Dolor / Pena profunda", "familia": "sadness", "intensidad": "intensa",
        "descripcion": "Duelo o pesar intenso (pérdidas, tragedias, luto).",
    },
    # Familia: DESAGRADO / ASCO (disgust)
    "aburrimiento": {
        "label": "Aburrimiento / Indiferencia", "familia": "disgust", "intensidad": "leve",
        "descripcion": "Desinterés, comentario desganado.",
    },
    "desagrado": {
        "label": "Desagrado", "familia": "disgust", "intensidad": "media",
        "descripcion": "Rechazo explícito, algo 'no gusta' sin llegar a la indignación.",
    },
    "repulsion": {
        "label": "Repulsión / Indignación moral", "familia": "disgust", "intensidad": "intensa",
        "descripcion": "Rechazo fuerte, lenguaje de asco o condena moral.",
    },
    # Familia: ENOJO (anger)
    "fastidio": {
        "label": "Fastidio / Molestia", "familia": "anger", "intensidad": "leve",
        "descripcion": "Irritación leve, queja sin agresividad.",
    },
    "enojo": {
        "label": "Enojo", "familia": "anger", "intensidad": "media",
        "descripcion": "Molestia clara y directa.",
    },
    "furia": {
        "label": "Furia / Ira", "familia": "anger", "intensidad": "intensa",
        "descripcion": "Enojo extremo, insultos, mayúsculas, lenguaje agresivo.",
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
        "label": "Vigilancia / Alerta expectante", "familia": "anticipation", "intensidad": "intensa",
        "descripcion": "Seguimiento atento y desconfiado.",
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
    # POSTURAS CÍVICAS (del catálogo original)
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

# ---------------------------------------------------------------------------
# Heurística de familia Plutchik para emociones nuevas.
#
# Diccionario de arranque derivado de EMOCIONES (descripciones) y
# _EMOCION_SINONIMOS. Solo cubre las 8 familias primarias de Plutchik;
# diada y civica se usan como fallback cuando la heurística no tiene
# señal suficiente.
# ---------------------------------------------------------------------------
_FAMILIA_KEYWORDS = {
    "joy": [
        "alegria", "felicidad", "feliz", "contento", "satisfecho", "euforia",
        "serenidad", "tranquilo", "calma", " paz ", "celebrar", "celebración",
        "gozo", "regocijo", "bienestar", "placidez",
    ],
    "trust": [
        "confianza", "confío", "respaldo", "apoyo", "aceptación", "acepto",
        "admiración", "admiro", "elogio", "credibilidad", "fiabilidad",
        "honestidad", "transparencia",
    ],
    "fear": [
        "miedo", "preocupación", "preocupado", "inquietud", "aprensión",
        "pánico", "terror", "alarma", "temor", "angustia", "nerviosismo",
        "incertidumbre",
    ],
    "surprise": [
        "sorpresa", "sorprendido", "asombro", "asombrado", "impacto",
        "inesperado", "increíble", "imprevisto", "novedad", "descubrimiento",
    ],
    "sadness": [
        "tristeza", "triste", "pena", "dolor", "luto", "duelo", "melancolía",
        "melancólico", "decepción", "decepcionado", "desilusión", "pesar",
        "llanto",
    ],
    "disgust": [
        "asco", "repulsión", "desagrado", "rechazo", "indignación",
        "indignado", "indigna", "vergüenza", "fastidio", "hartazgo",
        "aburrimiento", "indiferente", "desprecio",
    ],
    "anger": [
        "enojo", "enojado", "rabia", "furioso", "furia", "ira", "iracundo",
        "molestia", "molesto", "irritación", "irritado", "hostilidad",
        "agresividad",
    ],
    "anticipation": [
        "interés", "interesado", "curiosidad", "curioso", "expectativa",
        "espera", "ansiedad", "ansioso", "anticipación", "vigilancia",
        "atento", "seguimiento",
    ],
}


def _detectar_familia_emocion(clave, ejemplo=""):
    """Detecta la familia Plutchik más probable para una emoción nueva.

    Usa coincidencia de palabras clave contra las 8 familias primarias.
    Solo diada y civica se usan como fallback (no tienen keywords propios
    porque son categorías compuestas/institucionales, no emociones puras).

    Devuelve el código de familia (joy, trust, ..., anger, anticipation)
    o "civica" si no hay coincidencia real.
    """
    texto = (clave + " " + ejemplo).lower()
    mejor_familia = None
    mejor_puntaje = 0
    for familia, palabras in _FAMILIA_KEYWORDS.items():
        puntaje = sum(1 for p in palabras if p in texto)
        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_familia = familia
    return mejor_familia or "civica"


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
    "miedo": "terror", "pánico": "terror", "panico": "terror", "alarma": "terror",
    "sorprendido": "sorpresa", "asombrado": "asombro",
    "melancólico": "melancolia", "melancolico": "melancolia",
    "pena": "dolor", "duelo": "dolor",
    "aburrido": "aburrimiento", "indiferente": "aburrimiento",
    "disgusto": "desagrado", "me molesta": "desagrado",
    "asco": "repulsion", "vergüenza": "repulsion", "indignación": "repulsion",
    "molesto": "fastidio", "cansado de": "fastidio", "hartazgo": "fastidio",
    "furioso": "furia", "iracundo": "furia",
    "interesado": "interes", "curioso": "interes",
    "espero que": "expectativa", "a ver si": "expectativa",
    "vigilo": "vigilancia", "atento a": "vigilancia",
    "optimista": "optimismo",
    "cariño": "amor_civico", "aprecio": "amor_civico",
    "resignado": "sumision", "toca aceptar": "sumision",
    "sobrecogido": "asombro_temeroso",
    "decepcionado": "desaprobacion", "no puedo creer": "desaprobacion",
    "lamento": "remordimiento", "me arrepiento": "remordimiento",
    "desprecio": "desprecio", "menosprecio": "desprecio",
    "amenaza": "agresividad", "confrontación": "agresividad",
}


def normalizar_emocion(emocion, *, estricto=False, familia_sugerida=None):
    """Devuelve una emoción canónica o la clave propuesta (no-canónica).

    Acepta None, sinónimos, mayúsculas/espacios.

    - Si la emoción está en EMOCIONES_VALIDAS o en _EMOCION_SINONIMOS, devuelve
      la clave canónica correspondiente.
    - Si no está reconocida y estricto es False (por defecto): registra la
      propuesta en taxonomias_pendientes.json con la familia más cercana y
      devuelve la clave propuesta tal cual (no-canónica). Nunca fuerza a
      EMOCION_DEFAULT.
    - Si estricto es True: lanza ValueError (útil para depuración manual).
    - None devuelve EMOCION_DEFAULT ("calma") siempre.

    ``familia_sugerida`` permite al llamador indicar la familia Plutchik
    conocida (joy, trust, ..., anger, anticipation) para una emoción nueva.
    Si no se da, se usa heurística de palabras clave contra las 8 familias.
    """
    if not emocion:
        return EMOCION_DEFAULT
    e = str(emocion).strip().lower()
    if e in EMOCIONES_VALIDAS:
        return e
    resultado = _EMOCION_SINONIMOS.get(e)
    if resultado is not None:
        return resultado
    if estricto:
        raise ValueError(
            f"Emoción '{emocion}' no reconocida.  "
            f"Valores válidos: {sorted(EMOCIONES_VALIDAS)}"
        )
    familia = familia_sugerida or _detectar_familia_emocion(e, str(emocion))
    _registrar_propuesta("emocion", e, familia, ejemplo=str(emocion))
    return e
