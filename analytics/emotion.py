"""Clasificación de emoción por reglas léxicas (31 categorías Plutchik).

Sin modelos entrenados, sin llamadas a APIs. Léxico semilla por categoría
con detección de intensificadores y regla "me divierte" para publicaciones
oficiales.
"""
import re
import unicodedata
from dataclasses import dataclass, field

from analytics._propuestas import _registrar_propuesta


# ── Normalización (reutiliza patron de sentiment.py) ──

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def _normalize(text: str) -> str:
    text = text.lower()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(_normalize(text))


def _raw_lower(text: str) -> str:
    """Lowercase sin quitar acentos (para frases multi-palabra)."""
    return (text or "").lower().strip()


# ── Intensificadores ──

INTENSIFICADORES: set[str] = {
    "muy", "bastante", "totalmente", "completamente", "extremadamente",
    "sumamente", "increiblemente", "demasiado", "enormemente", "absolutamente",
    "mucho", "muchisimo", "horriblemente", "altamente",
}

# Signos de exclamación/repetición que indican intensidad
_EXCLAMATION_RE = re.compile(r"[!¡]{2,}")
_QUESTION_RE = re.compile(r"[?¿]{2,}")


def _detectar_intensidad_texto(text: str) -> bool:
    """True si el texto tiene marcadores de alta intensidad."""
    if _EXCLAMATION_RE.search(text):
        return True
    if _QUESTION_RE.search(text):
        return True
    tokens = _tokenize(text)
    for t in tokens:
        if t in INTENSIFICADORES:
            return True
    # 3+ mayúsculas seguidas (palabra EN ÉNFASIS)
    if re.search(r"\b[A-ZÁÉÍÓÚ]{3,}\b", text):
        return True
    return False


# ── Heurística de familia para textos sin match en léxico ──

_FAMILIA_KEYWORDS: dict[str, list[str]] = {
    "joy": ["bien", "bueno", "bonito", "gracias", "apoyo", "me gusta"],
    "trust": ["confianza", "respaldo", "apoyo", "creo", "fe"],
    "fear": ["miedo", "preocupa", "peligro", "riesgo", "amenaza", "cuidado"],
    "surprise": ["sorprendido", "increible", "no esperaba", "inesperado", "vaya"],
    "sadness": ["triste", "pena", "llorar", "deprimir", "dolor", "sufrir"],
    "disgust": ["asco", "asco", "feo", "repugnante", "indignacion"],
    "anger": ["enojado", "furioso", "rabia", "irritado", "molesto", "harto"],
    "anticipation": ["espero", "pendiente", "seguimiento", "proximo", "cuando"],
    "diada": ["esperanza", "amor", "solidaridad", "resignado"],
    "civica": ["exijo", "reclamo", "queja", "satisfecho", "agradezco", "normal"],
}


def _detectar_familia_emocion(text: str) -> str:
    """Intenta detectar la familia emocional por palabras clave del texto.

    Retorna una familia de Plutchik o "civica" si no detecta nada.
    """
    low = (text or "").lower()
    for familia, keywords in _FAMILIA_KEYWORDS.items():
        for kw in keywords:
            if kw in low:
                return familia
    return "civica"


# ── Léxico por emoción (31 categorías) ──
# Cada emoción tiene un set de palabras/frases semilla normalizadas (sin acentos).

EMOTION_LEXICON: dict[str, set[str]] = {
    # ── ALEGRÍA (joy) ──
    "serenidad": {
        "tranquilo", "tranquila", "calma", "paz", "sereno", "serena",
        "relajado", "relajada", "en paz", "armonia", "armonioso",
        "apacible", "sosegado", "placido",
    },
    "alegria": {
        "alegre", "alegria", "feliz", "contento", "contenta", "gozo",
        "encantado", "encantada", "disfruto", "gustoso", "gustosa",
        "satisfecho", "satisfecha", "bienestar", "regocijo",
        "sonrisa", "divertido", "divertida",
    },
    "euforia": {
        "euforico", "euforia", "increible", "emocionado", "emocionada",
        "espectacular", "brutal", "brutalisimo", "desbordado", "desbordada",
        "extremo", "extrema", "gloria", "triple", "wow", "wao",
        "genialisimo", "fantastico",
    },
    # ── CONFIANZA (trust) ──
    "aceptacion": {
        "acepto", "de acuerdo", "bien", "correcto", "esta bien",
        "se acepta", "conforme", "aprobado", "valido",
    },
    "confianza": {
        "confio", "confianza", "respaldo", "seguro", "segura",
        "confiable", "apoyo", "apoyamos", "fiel", "leal",
        "creo en", "deposito", "fe",
    },
    "admiracion": {
        "admiro", "admiracion", "bravo", "bravísimo", "excelente",
        "brillante", "extraordinario", "extraordinaria", "heroico",
        "heroica", "ejemplar", "inigualable", "elogio", "magnifico",
        "magnifica", "notable", "sobresaliente",
    },
    # ── MIEDO (fear) ──
    "aprension": {
        "inquietud", "duda", "temor", "desconfianza", "recelo",
        "reserva", "prevencion", "cautela", "desconfio",
    },
    "preocupacion": {
        "preocupado", "preocupada", "me preocupa", "riesgo", "peligro",
        "alerta", "amenaza", "atencion", "cuidado", "vigilancia",
        "emergencia", "alarmado", "alarmada", "preocupacion",
    },
    "terror": {
        "miedo", "panico", "terror", "aterrador", "aterradora",
        "horror", "horrible", "pavor", "espanto", "desesperacion",
        "socorro", "auxilio", "grito", "asustado", "asustada",
    },
    # ── SORPRESA (surprise) ──
    "distraccion": {
        "oh", "ah", "mira", "curioso", "curiosa", "interesante",
        "llamativo", "llamativa", "raro", "rara",
    },
    "sorpresa": {
        "sorprendido", "sorprendida", "increible", "no esperaba",
        "inesperado", "inesperada", "sorpresa", "imprevisto",
        "imprevista", "vaya", "uy", "wow", "no puedo creer",
    },
    "asombro": {
        "asombroso", "asombrosa", "impresionante", "extraordinario",
        "extraordinaria", "estupendo", "estupenda", "alucinante",
        "alucinado", "alucinada", "deslumbrante", "deslumbrado",
    },
    # ── TRISTEZA (sadness) ──
    "melancolia": {
        "melancolia", "melancolico", "melancolica", "apagado", "apagada",
        "nostalgia", "añoranza", "sueno", "remembranza",
    },
    "tristeza": {
        "triste", "tristeza", "pena", "llorar", "lloro", "pesar",
        "deprimir", "deprimido", "deprimida", "abatido", "abatida",
        "desolacion", "desanimado", "desanimada",
    },
    "dolor": {
        "dolor", "doloroso", "dolorosa", "sufrimiento", "luto",
        "tragedia", "muerte", "perdida", "perdido", "desgarra",
        "desgarrador", "hundir", "agonia", "padecer",
    },
    # ── DESAGRADO / ASCO (disgust) ──
    "aburrimiento": {
        "aburrido", "aburrida", "sin gracia", "me da igual",
        "pereza", "tedio", "monotonia", "insulso", "insulsa",
        "sin novedad", "comun", "mediocre",
    },
    "desagrado": {
        "desagrado", "desagradable", "feo", "fea", "no me gusta",
        "disgusto", "molestia", "molesto", "molesta", "antipatico",
        "antipatica", "fastidioso", "fastidiosa",
    },
    "repulsion": {
        "asco", "repulsion", "repugnante", "repugna", "indignacion",
        "indignado", "indignada", "vergüenza", "verguenza",
        "indignacion moral", "inmoral", "corrupto", "corrupta",
        "depravado", "depravada",
    },
    # ── ENOJO (anger) ──
    "fastidio": {
        "molesto", "molesta", "cansado", "cansada", "hartado", "hartada",
        "fastidio", "fastidioso", "fastidiosa", "harto", "harta",
        "cansancio", "fatiga", "agobio",
    },
    "enojo": {
        "enojado", "enojada", "furioso", "furiosa", "rabia", "indignado",
        "indignada", "irritado", "irritada", "encabritado", "encabritada",
        "molestia fuerte", "cabreo",
    },
    "furia": {
        "furia", "ira", "odio", "odioso", "odiosa", "amenaza",
        "amenazar", "destruir", "venganza", "castigo", "insulto",
        "insultar", "basura", "maldito", "maldita", "carajo",
        "puta", "hijo de",
    },
    # ── ANTICIPACIÓN (anticipation) ──
    "interes": {
        "curioso", "curiosa", "me interesa", "interesante",
        "pregunta", "consultar", "saber mas", "informacion",
    },
    "expectativa": {
        "espero que", "a ver si", "pendiente", "seguimiento",
        "proximo", "proxima", "cuando", "toca", "va a salir",
        "estreno", "lanzamiento",
    },
    "vigilancia": {
        "vigilo", "atento a", "no me pierdo", "seguir", "seguimiento",
        "monitoreo", "control", "supervision", "observar",
    },
    # ── DÍADAS ──
    "optimismo": {
        "esperanza", "mejorara", "saldra adelante", "habra futuro",
        "buen futuro", "optimismo", "optimista", "confianza en el futuro",
        "se puede", "todo sale bien",
    },
    "amor_civico": {
        "amor", "cariño", "cariño", "aprecio", "comunidad",
        "hermanos", "hermandad", "patria", "tierra", "queremos",
        "unidos", "solidaridad", "fraternidad",
    },
    "sumision": {
        "resignado", "resignada", "toca aceptar", "no hay opcion",
        "no queda mas", "aguantar", "soportar", "aguante",
        "ni modo", "que se le va a hacer",
    },
    "asombro_temeroso": {
        "sobrecogido", "sobrecogida", "horrorizado", "horrorizada",
        "impactado", "impactada", "aterrorizado", "aterrorizada",
        "conmocion", "miedo y sorpresa",
    },
    "desaprobacion": {
        "decepcionado", "decepcionada", "no puedo creer",
        "decepcion", "decepcionante", "lamentable",
        "lamentablemente", "infelizmente",
    },
    "remordimiento": {
        "lamento", "me arrepiento", "perdon", "disculpa",
        "fue un error", "me equivoque", "culpa", "remordimiento",
    },
    "desprecio": {
        "desprecio", "menosprecio", "basura", "inutil", "inservible",
        "no vale", "nada sirve", "humillacion", "humillar",
    },
    "agresividad": {
        "amenaza", "confrontacion", "voy a", "te voy a",
        "vas a ver", "cuidado que", "te tengo", "revancha",
        "represalia", "venganza activa",
    },
    # ── POSTURAS CÍVICAS ──
    "reclamo": {
        "exijo", "exigimos", "demanda", "reclamo", "reclamos",
        "queja", "quejas", "presentar queja", "denuncia",
        "acta", "se solucione", "respondan",
    },
    "objecion": {
        "objecion", "cuestiono", "no estoy de acuerdo", "discrepo",
        "me opongo", "no apoya", "critica constructiva",
        "no comparto", "diferente opinion",
    },
    "satisfaccion": {
        "satisfecho", "satisfecha", "conforme", "contento con",
        "contenta con", "bien hecho", "cumplido", "cumplida",
        "funciona bien", "excelente trabajo",
    },
    "calma": {
        "normal", "informativo", "sin carga", "neutro", "neutra",
        "para informar", " dato ", "referencia", "solo preguntar",
    },
    "reconocimiento": {
        "agradezco", "gracias", "felicito", "bravo", "buen trabajo",
        "reconocimiento", "aprecio", "bendiciones", "excelente",
        "gracias por", "mi agradecimiento",
    },
    "ironia": {
        "claro que si", "que bueno", "bravo pero", "seguro que",
        "ya veremos", "sarcastico", "burla", "ironia",
        "que bonito", "ay que bueno",
    },
}


# ── Regla "me divierte" = negativa en publicaciones oficiales ──

_IRONY_NEUTRALIZERS: set[str] = {
    "divierte", "divertido", "divertida", "reir", "me rio",
    "jaja", "jajaja", "jajajaja", "jajajajaja", "xd",
    "lol", "rae", "funny",
}


def _es_ironia_oficial(text: str, es_oficial: bool = False) -> bool:
    """True si el texto contiene marcadores de ironía/burla."""
    if not es_oficial:
        return False
    low = _raw_lower(text)
    tokens = _tokenize(text)
    for t in tokens:
        if t in _IRONY_NEUTRALIZERS:
            return True
    return False


# ── Result type ──

@dataclass
class EmotionResult:
    emocion: str = "calma"
    familia: str = "civica"
    intensidad: str = "media"
    evidence: list[str] = field(default_factory=list)
    scores: dict = field(default_factory=dict)


# ── Core classifier ──

def classify_emotion(text: str, es_oficial: bool = False) -> EmotionResult:
    """Clasifica la emoción de un texto usando léxico semilla.

    El resultado final pasa por normalizar_emocion() del catálogo abierto.
    Si el léxico no matchea y hay texto, se intenta detectar la familia y
    proponer una hoja nueva en taxonomias_pendientes.json.

    Args:
        text: texto del comentario
        es_oficial: True si el post es de una fuente oficial (activa regla "me divierte")

    Returns:
        EmotionResult con emoción canónica, familia, intensidad, evidencia y scores.
    """
    if not text or not text.strip():
        return EmotionResult(emocion="calma", familia="civica", intensidad="media")

    from dashboard.tema_taxonomia import EMOCIONES, EMOCIONES_VALIDAS, familia_de

    low = _raw_lower(text)
    tokens = set(_tokenize(text))

    # Score por emoción
    scores: dict[str, int] = {}
    evidence_map: dict[str, list[str]] = {}

    for emo, lexicon in EMOTION_LEXICON.items():
        score = 0
        evi = []
        for seed in lexicon:
            seed_norm = _normalize(seed)
            if " " in seed_norm:
                # Frase multi-palabra: buscar en texto normalizado
                if seed_norm in low:
                    score += 1
                    evi.append(seed)
            else:
                # Palabra individual: buscar en tokens
                if seed_norm in tokens:
                    score += 1
                    evi.append(seed)
        if score > 0:
            scores[emo] = score
            evidence_map[emo] = evi

    # Regla "me divierte" en publicaciones oficiales
    if _es_ironia_oficial(text, es_oficial):
        return EmotionResult(
            emocion="ironia",
            familia="civica",
            intensidad="media",
            evidence=["me_divierte_oficial"],
            scores={"ironia": 1},
        )

    if not scores:
        # Sin match en léxico: detectar familia y proponer hoja nueva
        familia = _detectar_familia_emocion(text)
        from dashboard.tema_taxonomia import normalizar_emocion
        try:
            emocion_norm = normalizar_emocion(familia)
        except (ValueError, KeyError):
            # La familia no es una emoción válida directamente; proponer
            propuesta = f"{familia}_nueva"
            _registrar_propuesta(
                clave_propuesta=propuesta,
                ejemplo_texto=text[:200],
                tipo="emocion",
                familia_mas_cercana=familia,
            )
            emocion_norm = "calma"
            familia = "civica"
        else:
            # La normalización funcionó; si la emoción no estaba en el lexicon,
            # registrar como propuesta
            if emocion_norm not in EMOTION_LEXICON:
                _registrar_propuesta(
                    clave_propuesta=emocion_norm,
                    ejemplo_texto=text[:200],
                    tipo="emocion",
                    familia_mas_cercana=familia,
                )
            familia = familia_de(emocion_norm)

        return EmotionResult(
            emocion=emocion_norm,
            familia=familia,
            intensidad="media",
            evidence=[],
            scores=scores,
        )

    # Emoción con mayor score
    best_emo = max(scores, key=lambda k: scores[k])
    best_score = scores[best_emo]

    # Intensidad base de la emoción
    meta = EMOCIONES.get(best_emo, {})
    intensidad = meta.get("intensidad", "media")
    familia = meta.get("familia", "civica")

    # Detectar intensificadores en el texto
    high_intensity = _detectar_intensidad_texto(text)

    # Si la emoción ya es intensa, mantener; si es leve/media y hay intensificador, subir
    if high_intensity and intensidad == "leve":
        # Buscar versión "media" de la misma familia
        for candidate, cmeta in EMOCIONES.items():
            if cmeta.get("familia") == familia and cmeta.get("intensidad") == "media":
                best_emo = candidate
                intensidad = "media"
                break
    elif high_intensity and intensidad == "media":
        # Buscar versión "intensa" de la misma familia
        for candidate, cmeta in EMOCIONES.items():
            if cmeta.get("familia") == familia and cmeta.get("intensidad") == "intensa":
                best_emo = candidate
                intensidad = "intensa"
                break

    # Normalizar con el catálogo abierto
    from dashboard.tema_taxonomia import normalizar_emocion
    try:
        best_emo = normalizar_emocion(best_emo)
    except (ValueError, KeyError):
        _registrar_propuesta(
            clave_propuesta=best_emo,
            ejemplo_texto=text[:200],
            tipo="emocion",
            familia_mas_cercana=familia,
        )

    return EmotionResult(
        emocion=best_emo,
        familia=familia,
        intensidad=intensidad,
        evidence=evidence_map.get(best_emo, []),
        scores=scores,
    )


# ── Agregación batch ──

def aggregate_emotions(texts: list[str], es_oficial: bool = False) -> dict:
    """Clasifica una lista de textos y retorna conteos y porcentajes.

    Returns dict con:
        - total: total de textos
        - conteo: {emocion: count} para cada una de las 31 categorías
        - pct: {emocion: pct} para cada una
        - dominante: emoción con mayor frecuencia
        - familias: {familia: count} agrupado por familia
        - evidencia_muestra: hasta 3 ejemplos por familia
    """
    from dashboard.tema_taxonomia import EMOCIONES_VALIDAS

    if not texts:
        return _empty_emotion_aggregate()

    conteo = {e: 0 for e in EMOCIONES_VALIDAS}
    familias: dict[str, int] = {}
    evidencias: dict[str, list[str]] = {}

    for text in texts:
        result = classify_emotion(text, es_oficial=es_oficial)
        if result.emocion in conteo:
            conteo[result.emocion] += 1
        fam = result.familia
        familias[fam] = familias.get(fam, 0) + 1
        # Guardar evidencia
        if result.evidence and fam not in evidencias:
            evidencias[fam] = result.evidence[:3]

    total = len(texts)
    pct = {
        e: round(conteo.get(e, 0) / total * 100, 1)
        for e in EMOCIONES_VALIDAS
    }

    dominante = max(EMOCIONES_VALIDAS, key=lambda e: conteo.get(e, 0))
    if conteo.get(dominante, 0) == 0:
        dominante = "calma"

    return {
        "total": total,
        "conteo": conteo,
        "pct": pct,
        "dominante": dominante,
        "familias": familias,
        "evidencia_muestra": evidencias,
    }


def _empty_emotion_aggregate() -> dict:
    from dashboard.tema_taxonomia import EMOCIONES_VALIDAS
    return {
        "total": 0,
        "conteo": {e: 0 for e in EMOCIONES_VALIDAS},
        "pct": {e: 0.0 for e in EMOCIONES_VALIDAS},
        "dominante": "calma",
        "familias": {},
        "evidencia_muestra": {},
    }
