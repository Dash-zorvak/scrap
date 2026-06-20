import re
import unicodedata
from src.analyzer.gazetteer import GAZETTEER

_PRIORITY_ORDER = [
    "lugares_emblematicos",
    "caserios",
    "cantones",
    "colonias",
    "municipios",
]

_TIPO_SINGULAR = {
    "lugares_emblematicos": "lugar_emblematico",
    "caserios": "caserio",
    "cantones": "canton",
    "colonias": "colonia",
    "municipios": "municipio",
}

_ENTITY_PATTERNS = [
    (r"\bcalle\s+([a-z0-9 ]{3,40})", "calle"),
    (r"\bavenida\s+([a-z0-9 ]{3,40})", "avenida"),
    (r"\bpasaje\s+([a-z0-9 ]{3,40})", "pasaje"),
    (r"\bbulevar\s+([a-z0-9 ]{3,40})", "bulevar"),
    (r"\bpuente\s+([a-z0-9 ]{3,40})", "puente"),
]

_RUN_ON_MAP = {
    "lapanades": "la panades",
}


def _normalizar(t: str) -> str:
    if not t:
        return ""
    t = t.lower().strip()
    t = unicodedata.normalize("NFKD", t)
    t = t.encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"\s+", " ", t)
    for runon, fixed in _RUN_ON_MAP.items():
        if runon in t:
            t = t.replace(runon, fixed)
    return t.strip()


def _build_gazetteer_flat() -> dict:
    flat = {}
    for tipo, nombres in GAZETTEER.items():
        for nombre in nombres:
            key = _normalizar(nombre)
            flat[key] = (nombre, tipo)
    return flat


GAZETTEER_FLAT = _build_gazetteer_flat()


def _extraer_entidad(texto: str) -> tuple[str | None, str | None]:
    texto_normalizado = _normalizar(texto)
    for pat, tipo_ent in _ENTITY_PATTERNS:
        m = re.search(pat, texto_normalizado)
        if m:
            return m.group(1).strip(), tipo_ent
    return None, None


def detectar_zona(texto: str) -> dict:
    if not texto:
        return {"zona": None, "zona_tipo": None, "entidad": None, "match": None}

    texto_norm = _normalizar(texto)

    entidad_nombre, entidad_tipo = _extraer_entidad(texto_norm)
    entidad = None
    if entidad_nombre:
        entidad = f"{entidad_tipo}: {entidad_nombre}"

    mejor_zona = None
    mejor_tipo = None
    mejor_match = None

    for tipo in _PRIORITY_ORDER:
        for nombre_raw in GAZETTEER.get(tipo, []):
            key = _normalizar(nombre_raw)
            if key in texto_norm:
                mejor_zona = nombre_raw
                mejor_tipo = _TIPO_SINGULAR.get(tipo, tipo)
                mejor_match = nombre_raw
                break
        if mejor_zona:
            break

    if not mejor_zona and not entidad:
        return {"zona": None, "zona_tipo": None, "entidad": None, "match": None}

    if mejor_zona and entidad:
        return {
            "zona": mejor_zona,
            "zona_tipo": mejor_tipo,
            "entidad": entidad,
            "match": mejor_match,
        }
    if mejor_zona:
        return {
            "zona": mejor_zona,
            "zona_tipo": mejor_tipo,
            "entidad": None,
            "match": mejor_match,
        }
    return {
        "zona": entidad,
        "zona_tipo": "entidad",
        "entidad": entidad,
        "match": entidad_nombre,
    }


def taggear_serie(textos: list[str]) -> list[dict]:
    return [detectar_zona(t) for t in textos]
