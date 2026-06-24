"""Carga de dichos y modismos desde idioms_sv_global.json (Capa 3).

Este modulo lee el archivo `idioms_sv_global.json` ubicado en la raiz del
repositorio y extrae las frases hechas idiomaticas multi-palabra. Sirve para
AMPLIAR la lista `DICHOS_LOCALES` del respaldo por palabras clave en
`topic_detection.py`, de modo que un comentario que sea un dicho / refran /
modismo no se clasifique como un tema literal.

Diseno defensivo: cualquier problema al localizar o parsear el archivo se
traduce en una lista vacia, para que el sistema siga funcionando con la lista
base hardcodeada (nunca rompe el pipeline ni el CI).

Solo se incluyen frases de >= 2 palabras: las palabras sueltas (caliche como
\"chivo\" o \"yuca\", o exclamaciones de una sola palabra) bloquearian la
deteccion de temas por coincidencia de substring, asi que se excluyen a
proposito.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# (grupo, seccion, clave_de_la_frase): secciones cuyas entradas son frases
# hechas que NO denotan un tema literal. Se omiten a proposito:
#   - salvadoreno.exclamaciones                  -> intensidad, no tema
#   - salvadoreno.caliche_palabras               -> palabras sueltas
#   - global_espanol.expresiones_redes_sociales  -> ambiguas / cortas / riesgosas
_SECCIONES = (
    ("salvadoreno", "dichos_idiomaticos", "expresion"),
    ("salvadoreno", "refranes", "refran"),
    ("global_espanol", "modismos_universales", "expresion"),
    ("global_espanol", "modismos_latinoamerica", "expresion"),
)

# Signos que se recortan de los bordes de cada frase (apertura/cierre de
# exclamacion e interrogacion, comillas y puntuacion final).
_CARACTERES_BORDE = " \t\n\u00a1!\u00bf?.,;:\"'\u00ab\u00bb\u201c\u201d"


def _ruta_idioms() -> Path:
    """Ruta al archivo idioms_sv_global.json.

    Permite sobrescribir con la variable de entorno IDIOMS_SV_PATH (util en
    pruebas o despliegues con otro layout). Por defecto apunta a la raiz del
    repo: src/analyzer/idioms_loader.py -> parents[2].
    """
    env = os.environ.get("IDIOMS_SV_PATH")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "idioms_sv_global.json"


def cargar_idioms_raw(ruta: Optional[os.PathLike] = None) -> dict:
    """Lee y parsea el JSON. Devuelve {} ante cualquier error."""
    ruta_final = Path(ruta) if ruta is not None else _ruta_idioms()
    try:
        with open(ruta_final, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        logger.info(
            "idioms_sv_global.json no encontrado en %s; se usa la lista base.",
            ruta_final,
        )
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("No se pudo leer idioms_sv_global.json: %r", exc)
        return {}
    return data if isinstance(data, dict) else {}


def extraer_dichos(data: Optional[dict] = None, min_palabras: int = 2) -> list:
    """Extrae frases hechas multi-palabra (texto original, con tildes).

    - ``data``: dict ya cargado; si es None se lee el archivo por defecto.
    - ``min_palabras``: minimo de palabras para incluir una frase. Con >= 2 se
      evita bloquear temas por una sola palabra ambigua.

    El resultado conserva mayusculas/tildes; la normalizacion para el match la
    realiza topic_detection.
    """
    if data is None:
        data = cargar_idioms_raw()
    if not isinstance(data, dict):
        return []

    vistos: set = set()
    salida: list = []
    for grupo, seccion, clave in _SECCIONES:
        grupo_obj = data.get(grupo)
        if not isinstance(grupo_obj, dict):
            continue
        seccion_obj = grupo_obj.get(seccion)
        if not isinstance(seccion_obj, dict):
            continue
        entradas = seccion_obj.get("entradas")
        if not isinstance(entradas, list):
            continue
        for entrada in entradas:
            if not isinstance(entrada, dict):
                continue
            frase = entrada.get(clave)
            if not isinstance(frase, str):
                continue
            frase = frase.strip().strip(_CARACTERES_BORDE).strip()
            if len(frase.split()) < min_palabras:
                continue
            clave_dedup = frase.lower()
            if clave_dedup in vistos:
                continue
            vistos.add(clave_dedup)
            salida.append(frase)
    return salida
