"""Detección de temas emergentes por frecuencia de n-gramas.

Extrae bigramas y trigramas de textos, compara frecuencia entre períodos.
frecuencia_actual / max(frecuencia_previa, 1) ≥ 1.5 → "acelerando"
frecuencia_actual / max(frecuencia_previa, 1) ≤ 0.67 → "desacelerando"
Sin historial previo suficiente → "sin_comparacion".
"""
import re
import unicodedata
from collections import Counter


# ── Normalización ──

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)
_STOP_ES: set[str] = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "a", "en", "con", "por", "para", "sin",
    "que", "se", "es", "lo", "su", "sus", "este", "esta", "ese",
    "esa", "esto", "eso", "como", "mas", "pero", "si", "no",
    "ya", "ni", "o", "y", "e", "muy", "más", "les", "le",
    "me", "te", "nos", "mi", "tu", "hay", "fue", "ser", "estar",
    "haber", "hacer", "tener", "ir", "poder", "decir", "ver",
    "dar", "saber", "querer", "llegar", "poner", "creer",
    "había", "hace", "desde", "todo", "toda", "todos", "todas",
    "otro", "otra", "otros", "otras", "cada", "algo", "nada",
    "siempre", "nunca", "aquí", "ahí", "allí", "donde", "cuando",
}


def _normalize(text: str) -> str:
    text = text.lower()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(_normalize(text))


def _filtrar_stopwords(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in _STOP_ES and len(t) > 2]


# ── Extracción de n-gramas ──

def extract_bigrams(texts: list[str]) -> Counter:
    """Extrae bigramas de una lista de textos (sin stopwords)."""
    counter: Counter = Counter()
    for text in texts:
        tokens = _filtrar_stopwords(_tokenize(text))
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            counter[bigram] += 1
    return counter


def extract_trigrams(texts: list[str]) -> Counter:
    """Extrae trigramas de una lista de textos (sin stopwords)."""
    counter: Counter = Counter()
    for text in texts:
        tokens = _filtrar_stopwords(_tokenize(text))
        for i in range(len(tokens) - 2):
            trigram = f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}"
            counter[trigram] += 1
    return counter


# ── Clasificación de tendencia ──

def clasificar_tendencia(freq_actual: int, freq_previa: int) -> str:
    """Determina la tendencia de un n-grama entre períodos.

    - freq_actual / max(freq_previa, 1) >= 1.5 → "acelerando"
    - freq_actual / max(freq_previa, 1) <= 0.67 → "desacelerando"
    - freq_previa == 0 y freq_actual > 0 → "nuevo"
    - otherwise → "estable"
    """
    if freq_previa == 0 and freq_actual > 0:
        return "nuevo"
    if freq_previa == 0 and freq_actual == 0:
        return "sin_comparacion"

    ratio = freq_actual / max(freq_previa, 1)
    if ratio >= 1.5:
        return "acelerando"
    if ratio <= 0.67:
        return "desacelerando"
    return "estable"


# ── Detección de temas emergentes ──

def detectar_emergentes(
    textos_actuales: list[str],
    textos_previos: list[str] | None = None,
    top_n: int = 10,
    min_freq: int = 2,
) -> list[dict]:
    """Detecta temas emergentes comparando n-gramas entre períodos.

    Args:
        textos_actuales: textos del período actual
        textos_previos: textos del período anterior (None o vacío = sin comparación)
        top_n: número máximo de temas emergentes a retornar
        min_freq: frecuencia mínima en el período actual para considerar un n-grama

    Returns:
        Lista de dicts ordenados por frecuencia descendente:
        {ngrama, frecuencia_actual, frecuencia_previa, tendencia, ratio}
    """
    if not textos_actuales:
        return []

    # Extraer n-gramas del período actual
    bigramas_act = extract_bigrams(textos_actuales)
    trigramas_act = extract_trigrams(textos_actuales)

    # Combinar bigramas y trigramas
    ngramas_act: Counter = bigramas_act + trigramas_act

    # Filtrar por frecuencia mínima
    candidatos = {
        ng: freq for ng, freq in ngramas_act.items()
        if freq >= min_freq
    }

    if not candidatos:
        return []

    # Extraer n-gramas del período previo
    ngramas_prev: Counter = Counter()
    if textos_previos:
        bigramas_prev = extract_bigrams(textos_previos)
        trigramas_prev = extract_trigrams(textos_previos)
        ngramas_prev = bigramas_prev + trigramas_prev

    # Calcular tendencia para cada candidato
    emergentes = []
    for ng, freq_act in candidatos.items():
        freq_prev = ngramas_prev.get(ng, 0)
        tendencia = clasificar_tendencia(freq_act, freq_prev)
        ratio = round(freq_act / max(freq_prev, 1), 2)

        emergentes.append({
            "ngrama": ng,
            "frecuencia_actual": freq_act,
            "frecuencia_previa": freq_prev,
            "tendencia": tendencia,
            "ratio": ratio,
        })

    # Ordenar por frecuencia descendente, priorizando acelerando
    emergentes.sort(key=lambda x: (-x["frecuencia_actual"], x["tendencia"] != "acelerando"))

    return emergentes[:top_n]


# ── Análisis completo ──

def analizar_emergentes(
    textos_actuales: list[str],
    textos_previos: list[str] | None = None,
    top_n: int = 10,
    min_freq: int = 2,
) -> dict:
    """Análisis completo de temas emergentes.

    Returns dict con:
        - emergentes: lista de temas emergentes detectados
        - total_bigramas_actual: total de bigramas extraídos del actual
        - total_bigramas_previo: total del período previo (0 si no hay)
        - n_acelerando: count de temas acelerando
        - n_desacelerando: count de temas desacelerando
        - n_nuevos: count de temas nuevos
    """
    emergentes = detectar_emergentes(
        textos_actuales, textos_previos, top_n, min_freq
    )

    bigramas_act = extract_bigrams(textos_actuales)
    total_bigramas_actual = sum(bigramas_act.values())

    total_bigramas_previo = 0
    if textos_previos:
        bigramas_prev = extract_bigrams(textos_previos)
        total_bigramas_previo = sum(bigramas_prev.values())

    return {
        "emergentes": emergentes,
        "total_bigramas_actual": total_bigramas_actual,
        "total_bigramas_previo": total_bigramas_previo,
        "n_acelerando": sum(1 for e in emergentes if e["tendencia"] == "acelerando"),
        "n_desacelerando": sum(1 for e in emergentes if e["tendencia"] == "desacelerando"),
        "n_nuevos": sum(1 for e in emergentes if e["tendencia"] == "nuevo"),
    }
