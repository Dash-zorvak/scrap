"""Detección de zona/ubicación por gazetteer de nombres conocidos.

Coincidencia por substring/palabra en el texto. Nombres frecuentes no
reconocidos se registran como propuesta (tipo="zona"), nunca se fuerza
una zona por defecto ni se descarta.
"""
import re
import unicodedata


# ── Gazetteer: zonas conocidas de Guatemala ──

# Departamentos de Guatemala
DEPARTAMENTOS: set[str] = {
    "guatemala", "sacatepequez", "chimaltenango", "solola", "totonicapan",
    "quetzaltenango", "retalhuleu", "suchitepequez", "escuintla",
    "santa rosa", "jutiapa", "jalapa", "chiquimula", "zacapa",
    "izabal", "peten", "bahia de izabal", "coban", "alta verapaz",
    "baja verapaz", "quiche", "huehuetenango", "san marcos",
    "san luis peteni", "el progreso", "el progresso", "jirón",
}

# Municipios principales (muestra)
MUNICIPIOS: set[str] = {
    "guatemala", "mixco", "villa nueva", "coban", "quetzaltenango",
    "escuintla", "petapa", "villa canales", "san juan sacatepequez",
    "san josé pinula", "santa catarina pinula", "fraijanes",
    "palencia", "chinautla", "san pedro ayampuc", "san pedro sacatepequez",
    "san juan zapotitlan", "san raymundo", "chuarrancho",
    "mazatenango", "retalhuleu", "coatepeque", "tonala",
    "antigua guatemala", "ciudad vieja", "jocotenango", "santa apolonia",
    "san antonio aguas calientes", "san bartolo aguas calientes",
    "san lucas sacatepequez", "san miguelDueñas", "santiago sacatepequez",
    "santo domingo xenacoj", "san andres itzapa", "parramos",
    "tejar", "chimaltenango", "san juan comalapa", "san andrés xecul",
    "san francisco el alto", "totonicapan", "san cristóbal totocostepec",
    "malacatán", "san marcos", "tajumulco", "coatepeque",
    "huehuetenango", "san ildefonso ixtahuacan", "san pedro necta",
    "la libertad", "chiantla", "cuilapa", "barberena",
    "jutiapa", "el adelanto", "zapotitlan", "san josé acatempa",
    "jalapa", "san pedro pinula", "san luis jilotepeque",
    "chiquimula", "esquipulas", "copán", "copan",
}

# Zonas de la Ciudad de Guatemala
ZONAS_GT: set[str] = {
    "zona 1", "zona 2", "zona 3", "zona 4", "zona 5", "zona 6",
    "zona 7", "zona 8", "zona 9", "zona 10", "zona 11", "zona 12",
    "zona 13", "zona 14", "zona 15", "zona 16", "zona 17", "zona 18",
    "zona 19", "zona 20", "zona 21",
    "ciudad de guatemala", "guatemala capital",
    "centro historico", "zona 1 centro",
}

# Barrios / colonias comunes
BARRIOS: set[str] = {
    "zona 1", "zona 4", "zona 7", "zona 10", "zona 13", "zona 14",
    "la aurora", "vista hermosa", "el naranjo", "jardines de la finca",
    "residenciales", "condado el naranjo", "club campos de quetzaltenango",
    "el mirador", "lomas de san francisco", "san nicolas",
    "las americas", "vista al lago", "balcones de san antonio",
    "zona libre", "zona 4 industrial", "zona 10 industriales",
    "colonia 10 de octubre", "colonia jose clemencia rojas",
    "colonia santa fe", "colonia bello aires", "colonia la floresta",
    "colonia las palmas", "colonia los robles", "colonia reforma",
    "colonia mariscal", "colonia guerrero", "colonia la conventional",
    "colonia escuintla", "colonia el rosario", "colonia progreso",
}

# Unir todo el gazetteer
ZONAS_CONOCIDAS: set[str] = DEPARTAMENTOS | MUNICIPIOS | ZONAS_GT | BARRIOS


# ── Normalización ──

def _normalize(text: str) -> str:
    text = text.lower()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ── Result type ──

from dataclasses import dataclass, field as dc_field


@dataclass
class ZonaResult:
    zona: str = ""
    tipo: str = ""  # "departamento", "municipio", "zona_gt", "barrio", "propuesta"
    evidencia: str = ""
    es_propuesta: bool = False


# ── Core detector ──

def detectar_zona(text: str) -> ZonaResult:
    """Detecta zona/mención geográfica en un texto.

    Prioridad: Zona GT > Barrios > Municipios > Departamentos.
    Si no se reconoce, retorna zona="" (nunca fuerza una zona por defecto).
    """
    if not text or not text.strip():
        return ZonaResult(zona="", tipo="")

    low = _normalize(text)

    # 1. Buscar zonas de la Ciudad de Guatemala (prioridad alta)
    for zona in sorted(ZONAS_GT, key=len, reverse=True):
        zona_norm = _normalize(zona)
        if zona_norm in low:
            return ZonaResult(zona=zona, tipo="zona_gt", evidencia=zona)

    # 2. Buscar barrios
    for barrio in sorted(BARRIOS, key=len, reverse=True):
        barrio_norm = _normalize(barrio)
        if barrio_norm in low:
            return ZonaResult(zona=barrio, tipo="barrio", evidencia=barrio)

    # 3. Buscar municipios
    for municipio in sorted(MUNICIPIOS, key=len, reverse=True):
        municipio_norm = _normalize(municipio)
        # Para municipios multi-palabra, buscar como substring
        if " " in municipio_norm:
            if municipio_norm in low:
                return ZonaResult(zona=municipio, tipo="municipio", evidencia=municipio)
        else:
            # Para municipios de una palabra, buscar como token
            tokens = set(low.split())
            if municipio_norm in tokens:
                return ZonaResult(zona=municipio, tipo="municipio", evidencia=municipio)

    # 4. Buscar departamentos
    for depto in sorted(DEPARTAMENTOS, key=len, reverse=True):
        depto_norm = _normalize(depto)
        if " " in depto_norm:
            if depto_norm in low:
                return ZonaResult(zona=depto, tipo="departamento", evidencia=depto)
        else:
            tokens = set(low.split())
            if depto_norm in tokens:
                return ZonaResult(zona=depto, tipo="departamento", evidencia=depto)

    # 5. No se reconoció → devolver vacío (sin fuerza por defecto)
    return ZonaResult(zona="", tipo="")


def es_propuesta_zona(text: str) -> str | None:
    """Si el texto contiene una palabra que parece nombre de zona pero no
    está en el gazetteer, retorna la palabra candidata para registrar como propuesta.

    Heurística: 3+ palabras capitalizadas al inicio de oración,
    o contenido después de "en ", "de ", "por ", "desde ".
    """
    if not text or not text.strip():
        return None

    # Buscar patrones "en <zona>", "de <zona>", "por <zona>"
    import re
    patrones = re.findall(
        r"(?:en|de|por|desde|hasta|hacia) ([a-záéíóúñ]{3,}(?:\s+[a-záéíóúñ]{3,}){0,2})",
        (text or "").lower().strip(),
    )

    for candidata in patrones:
        candidata_limpia = candidata.strip()
        if len(candidata_limpia) >= 3:
            # Verificar que no esté ya en el gazetteer
            zona = detectar_zona(candidata_limpia)
            if not zona.zona:
                return candidata_limpia

    return None


# ── Agregación batch ──

def aggregate_zonas(texts: list[str]) -> dict:
    """Analiza una lista de textos y retorna distribución de zonas detectadas.

    Returns dict con:
        - total: total de textos
        - conteo: {zona: count}
        - pct: {zona: pct}
        - dominante: zona más mencionada (o "" si ninguna)
        - propuestas: lista de nombres candidatos no reconocidos
    """
    if not texts:
        return {"total": 0, "conteo": {}, "pct": {}, "dominante": "", "propuestas": []}

    conteo: dict[str, int] = {}
    propuestas: list[str] = []

    for text in texts:
        result = detectar_zona(text)
        if result.zona:
            conteo[result.zona] = conteo.get(result.zona, 0) + 1

        # Detectar propuestas
        propuesta = es_propuesta_zona(text)
        if propuesta and propuesta not in propuestas:
            propuestas.append(propuesta)

    total = len(texts)
    pct = {
        zona: round(count / total * 100, 1)
        for zona, count in conteo.items()
    }

    dominante = max(conteo, key=lambda k: conteo[k]) if conteo else ""

    return {
        "total": total,
        "conteo": conteo,
        "pct": pct,
        "dominante": dominante,
        "propuestas": propuestas,
    }
