DIMENSION_WEIGHTS = {
    "aprobacion": 1.0,
    "conexion": 1.0,
    "tranquilidad": 1.0,
    "diversidad_temas": 0.8,
    "presencia_zonas": 0.7,
    "consistencia": 0.9,
    "atencion": 0.6,
}

DIMENSION_LABELS = {
    "aprobacion": {
        "label": "Aprobación Ciudadana",
        "description": "Sentimiento neto de la población",
        "unit": "%",
        "higher_is_better": True,
    },
    "conexion": {
        "label": "Conexión con la Gente",
        "description": "Nivel de engagement e interacción",
        "unit": "%",
        "higher_is_better": True,
    },
    "tranquilidad": {
        "label": "Tranquilidad",
        "description": "Ausencia de controversia y enojo",
        "unit": "%",
        "higher_is_better": True,
    },
    "diversidad_temas": {
        "label": "Diversidad de Temas",
        "description": "Variedad de tópicos gestionados",
        "unit": "%",
        "higher_is_better": True,
    },
    "presencia_zonas": {
        "label": "Presencia en Zonas",
        "description": "Cobertura territorial de los mensajes",
        "unit": "%",
        "higher_is_better": True,
    },
    "consistencia": {
        "label": "Consistencia",
        "description": "Estabilidad emocional de la audiencia",
        "unit": "%",
        "higher_is_better": True,
    },
    "atencion": {
        "label": "Atención a la Comunidad",
        "description": "Capacidad de generar conversación",
        "unit": "%",
        "higher_is_better": True,
    },
}
