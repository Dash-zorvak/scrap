"""Catálogo creciente de entidades y subtemas específicos.

Cada comentario puede pertenecer a un tema englobante (ej. "gobernanza") y
además a una entidad o subtema específico (ej. "Juan Carlos", "Alcaldía de
Santa Ana Centro", "Parque Morazán").

El catálogo es abierto (RG-6): cuando un analista escribe una entidad nueva,
se registra automáticamente en `data/taxonomias_pendientes.json` con
`tipo="entidad"` para que pueda revisarse y promoverse al catálogo reutilizable.

Estructura similar a TEMAS en tema_taxonomia.py.
"""

# clave -> {label, tema_englobante, desc}
ENTIDADES = {
    # --- Personas / Candidaturas ---
    "juan_carlos": {
        "label": "Juan Carlos",
        "tema_englobante": "gobernanza",
        "desc": "Mención al candidato o persona llamada Juan Carlos.",
    },
    "alcaldia_santa_ana_centro": {
        "label": "Alcaldía de Santa Ana Centro",
        "tema_englobante": "gobernanza",
        "desc": "La institución municipal de Santa Ana Centro.",
    },
    "alcaldia": {
        "label": "La Alcaldía",
        "tema_englobante": "gobernanza",
        "desc": "Referencia genérica a la alcaldía o al alcalde en funciones.",
    },
    "concejales": {
        "label": "Concejales",
        "tema_englobante": "gobernanza",
        "desc": "El corpo concejal o algún concejal específico.",
    },
    # --- Proyectos / Obras ---
    "parque_morazan": {
        "label": "Parque Morazán",
        "tema_englobante": "obras_servicios",
        "desc": "El parque Morazán y su estado o mantenimiento.",
    },
    "mercado_central": {
        "label": "Mercado Central",
        "tema_englobante": "obras_servicios",
        "desc": "El mercado central y su infraestructura.",
    },
    "calle_principal": {
        "label": "Calle Principal",
        "tema_englobante": "movilidad",
        "desc": "La calle principal o avenida principal de la ciudad.",
    },
    # --- Zonas / Barrios ---
    "barrio_este": {
        "label": "Barrio Este",
        "tema_englobante": "obras_servicios",
        "desc": "El barrio o zona este de la ciudad.",
    },
    "centro_ciudad": {
        "label": "Centro de la ciudad",
        "tema_englobante": "obras_servicios",
        "desc": "El casco urbano o zona central.",
    },
}

ENTIDADES_VALIDAS = set(ENTIDADES.keys())
ENTIDAD_LABELS = {k: v["label"] for k, v in ENTIDADES.items()}

# Todas las claves, incluyendo "no_aplica" implícito (sin entidad)
ENTIDADES_VISIBLES = list(ENTIDADES.keys())


def etiqueta_entidad(clave):
    """Etiqueta legible para una clave de entidad."""
    if not clave:
        return "— Sin entidad específica —"
    return ENTIDAD_LABELS.get(clave, clave.replace("_", " ").capitalize())


def tema_de_entidad(clave):
    """Tema englobante asociado a una entidad (si existe)."""
    return ENTIDADES.get(clave, {}).get("tema_englobante", "")
