"""Helper para registrar propuestas nuevas en taxonomias_pendientes.json.

Usado por emotion.py, topic.py y zona.py cuando detectan una categoría o zona
que no existe en el catálogo actual.
"""
import json
import os
from datetime import datetime, timezone


_TAXONOMIAS_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir, "data", "taxonomias_pendientes.json"
)


def _registrar_propuesta(
    clave_propuesta: str,
    ejemplo_texto: str,
    tipo: str,
    familia_mas_cercana: str = "",
) -> None:
    """Append una propuesta a taxonomias_pendientes.json.

    Si ya existe una entrada pendiente con la misma clave+tipo, incrementa
    n_ocurrencias y actualiza fecha en vez de crear entrada duplicada.

    Args:
        clave_propuesta: nombre propuesto (ej. "nueva_emocion" o "zona_xyz")
        ejemplo_texto: fragmento del texto que motivó la propuesta
        tipo: "emocion", "tema", o "zona"
        familia_mas_cercana: familia o categoría más cercana (vacío si no aplica)
    """
    path = os.path.normpath(_TAXONOMIAS_PATH)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    # Deduplicar: buscar entrada pendiente con misma clave+tipo
    for entry in data:
        if (entry.get("clave_propuesta") == clave_propuesta
                and entry.get("tipo") == tipo
                and entry.get("estado") == "pendiente"):
            entry["n_ocurrencias"] = entry.get("n_ocurrencias", 1) + 1
            entry["fecha"] = datetime.now(timezone.utc).isoformat()
            break
    else:
        data.append({
            "clave_propuesta": clave_propuesta,
            "ejemplo_texto": ejemplo_texto[:200],
            "tipo": tipo,
            "familia_mas_cercana": familia_mas_cercana,
            "fecha": datetime.now(timezone.utc).isoformat(),
            "estado": "pendiente",
            "n_ocurrencias": 1,
        })

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
