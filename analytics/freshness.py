"""Deteccion de datos obsoletos en analysis.json.

Verifica que los datos no tengan mas de N dias de antiguedad.
Se usa para mostrar alertas en el dashboard cuando los datos estan frescos.
"""
import json
import os
from datetime import datetime, timezone


def verificar_freshness(path="data/analysis.json", max_dias=7):
    """Verifica si analysis.json tiene datos recientes.

    Args:
        path: ruta al archivo analysis.json.
        max_dias: dias maximos de antiguedad aceptable.

    Returns:
        dict con:
            - fresco: bool (True si es reciente)
            - dias_desde_generacion: int o None
            - fecha_generacion: str o None
            - mensaje: str legible
    """
    if not os.path.exists(path):
        return {
            "fresco": False,
            "dias_desde_generacion": None,
            "fecha_generacion": None,
            "mensaje": "No existe archivo de analisis.",
        }

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {
            "fresco": False,
            "dias_desde_generacion": None,
            "fecha_generacion": None,
            "mensaje": "Error al leer el archivo de analisis.",
        }

    generado_en = data.get("meta", {}).get("generado_en", "")
    if not generado_en:
        return {
            "fresco": False,
            "dias_desde_generacion": None,
            "fecha_generacion": None,
            "mensaje": "El archivo no tiene marca de tiempo de generacion.",
        }

    try:
        dt_gen = datetime.fromisoformat(generado_en)
        ahora = datetime.now(timezone.utc)
        dias = (ahora - dt_gen).days
        fresco = dias <= max_dias

        if fresco:
            msg = f"Datos frescos (generados hace {dias} dia(s))."
        else:
            msg = f"Datos obsoletos (generados hace {dias} dia(s), limite: {max_dias})."

        return {
            "fresco": fresco,
            "dias_desde_generacion": dias,
            "fecha_generacion": generado_en,
            "mensaje": msg,
        }
    except ValueError:
        return {
            "fresco": False,
            "dias_desde_generacion": None,
            "fecha_generacion": generado_en,
            "mensaje": "Formato de fecha de generacion invalido.",
        }
