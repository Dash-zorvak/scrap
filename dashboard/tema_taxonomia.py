"""Taxonomia englobante de temas ciudadanos (fuente unica de verdad).

En vez de que la IA descubra temas libremente, definimos por defecto un conjunto
pequeno de temas ENGLOBANTES. Algunos temas historicos se fusionan aqui:

  - obras_publicas + servicios_publicos -> obras_servicios
  - corrupcion + transparencia          -> gobernanza
  - cultura + deportes                  -> cultura_deportes

Se mantienen separados los que son preocupaciones claramente distintas
(seguridad, salud, educacion, empleo, movilidad, medio_ambiente).

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
        "rendicion de cuentas y gestion municipal.",
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
