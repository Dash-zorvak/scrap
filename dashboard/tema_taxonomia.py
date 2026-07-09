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

    Acepta None, sinonimos comunes del modelo y mayusculas/espacios. Cualquier
    valor desconocido cae a 'neutral' (POSTURA_DEFAULT), de modo que un dato mal
    formado nunca se cuente como apoyo ni como critica por error.
    """
    if not postura:
        return POSTURA_DEFAULT
    p = str(postura).strip().lower()
    if p in POSTURAS_VALIDAS:
        return p
    return _POSTURA_SINONIMOS.get(p, POSTURA_DEFAULT)


def etiqueta_postura(postura):
    """Etiqueta legible para una postura (acepta sinonimos / None)."""
    return POSTURA_LABELS.get(normalizar_postura(postura), POSTURA_LABELS[POSTURA_DEFAULT])


# ---------------------------------------------------------------------------
# Catálogo de emociones (mismo que bloque1.indice_emociones del schema).
# ---------------------------------------------------------------------------
EMOCIONES = {
    "reclamo": "Reclamo",
    "objecion": "Objeción",
    "satisfaccion": "Satisfacción",
    "calma": "Calma",
    "enojo": "Enojo",
    "tristeza": "Tristeza",
    "alegria": "Alegría",
    "reconocimiento": "Reconocimiento",
    "ironia": "Ironía",
    "preocupacion": "Preocupación",
}

EMOCIONES_VALIDAS = set(EMOCIONES.keys())
EMOCION_LABELS = dict(EMOCIONES)
EMOCION_DEFAULT = "calma"

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


def normalizar_emocion(emocion):
    """Devuelve una emoción canónica (10 emociones).

    Acepta None, sinónimos, mayúsculas/espacios. Valor desconocido cae a
    EMOCION_DEFAULT ("calma").
    """
    if not emocion:
        return EMOCION_DEFAULT
    e = str(emocion).strip().lower()
    if e in EMOCIONES_VALIDAS:
        return e
    return _EMOCION_SINONIMOS.get(e, EMOCION_DEFAULT)
