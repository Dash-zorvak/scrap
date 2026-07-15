"""Clasificación de sentimiento por reglas léxicas en español.

Sin modelos entrenados, sin llamadas a APIs de inferencia.
Diccionario de datos plano (lista de palabras + polaridad) + reglas de negación.
"""
import re
import unicodedata
from dataclasses import dataclass, field


# ── Escala numérica para promedios ──

SENTIMENT_ORDER = {
    "muy_positivo": 2,
    "positivo": 1,
    "neutral": 0,
    "negativo": -1,
    "muy_negativo": -2,
}


# ── Léxico ──

POSITIVE_WORDS: set[str] = {
    # Aprobación / satisfacción
    "excelente", "bueno", "buena", "bien", "buen", "genial", "perfecto",
    "increible", "maravilloso", "maravillosa", "fantastico", "fantastica",
    "brillante", "optimo", "optima", "magnifico", "magnifica", "espectacular",
    # Agradecimiento
    "gracias", "agradezco", "agradecido", "agradecida", "reconocimiento",
    "reconozco", "aprecio", "apreciado", "apreciada", "bendicion",
    # Felicitación / elogio
    "felicitaciones", "felicidades", "bravo", "enhorabuena", "aplauso",
    "aplausos", "elogio", "felicitacion",
    # Apoyo
    "apoyo", "apoyamos", "respaldo", "respaldamos", "acompañamos",
    "solidaridad", "compromiso", "comprometido", "comprometida",
    "defender", "defiendo",
    # Progreso / mejora
    "progreso", "avance", "avances", "mejora", "mejoras", "mejorar",
    "avanzar", "crecimiento", "desarrollo", "innovacion", "innovar",
    "transformacion", "transformar", "modernizacion", "modernizar",
    "solucion", "resolver", "resuelto", "resuelta",
    # Calidad
    "eficiente", "eficiencia", "eficaz", "calidad", "funciona",
    "funcional", "operativo", "operativa",
    # Emoción positiva
    "alegre", "alegria", "felicidad", "orgullo", "orgullosa",
    "esperanza", "optimismo", "optimista", "entusiasmo", "entusiasmado",
    "entusiasmada", "satisfecho", "satisfecha", "contento", "contenta",
    "tranquilo", "tranquila", "sereno", "serena", "calma",
    # Valoración positiva
    "bonito", "bonita", "lindo", "linda", "hermoso", "hermosa",
    "limpio", "limpia", "ordenado", "ordenada", "seguro", "segura",
    "confiable", "responsable", "honesto", "honesta", "transparente",
    "transparentes", "justo", "justa", "digno", "digna",
    # Acciones positivas
    "reparar", "reparado", "reparada", "construir", "construido",
    "construida", "inaugurar", "inaugurado", "inaugurada", "entregar",
    "entregado", "entregada", "cumplir", "cumplido", "cumplida",
    "atender", "atendido", "atendida", "servir", "servicio",
    # Saludo / cierre positivo
    "exitos", "éxitos",
}

NEGATIVE_WORDS: set[str] = {
    # Crítica / rechazo
    "malo", "mala", "mal", "terrible", "pésimo", "pesimo", "horrible",
    "desastroso", "desastrosa", "deplorable", "lamentable",
    # Problemas
    "problema", "problemas", "crisis", "caos", "colapso", "colapsado",
    "colapsada", "deficiente", "insuficiente", "limitado", "limitada",
    "escaso", "escasa", "fallo", "falla", "fallas", "averia", "averiado",
    "roto", "rota", "destruido", "destruida",
    # Incumplimiento
    "incumplimiento", "incumplir", "incumplido", "incumplida",
    "promesa", "promesas", "abandono", "abandonado", "abandonada",
    "olvidado", "olvidada", "desatendido", "desatendida",
    # Corrupción / fraude
    "corrupto", "corrupta", "corrupcion", "fraude", "robo", "robar",
    "malversacion", "malversar", "desfalco", "desfalcar", "soborno",
    "sobornar", "cohecho", "prevaricato",
    # Abuso
    "abuso", "abusar", "abusado", "abusada", "arbitrario", "arbitraria",
    "abusivo", "abusiva", "exceso", "excesivo", "excesiva",
    # Emoción negativa
    "indignacion", "indignado", "indignada", "furioso", "furiosa",
    "enojado", "enojada", "molesto", "molesta", "hartado", "hartada",
    "cansado", "cansada", "frustrado", "frustrada", "decepcionado",
    "decepcionada", "triste", "tristeza", "dolor", "doloroso", "dolorosa",
    "lamentable", "lamento",
    # Rechazo explícito
    "rechazo", "rechazar", "rechazado", "rechazada", "objecion",
    "objeto", "protesta", "protestar", "exigir", "exigencia",
    "queja", "quejarse", "inconformidad", "inconforme", "insatisfecho",
    "insatisfecha",
    # Negatividad general
    "inaceptable", "intolerable", "vergüenza", "verguenza",
    "escandalo", "escándalo", "atropello", "injusticia", "injusto",
    "injusta", "abusador", "abusadora",
    # Desastre / deterioro
    "deterioro", "deteriorado", "deteriorada", "degradacion",
    "degradado", "degradada", "ruina", "arruinado", "arruinada",
    "caido", "caida", "hundido", "hundida",
    # Mentira / engaño
    "mentira", "mentiras", "mentir", "mentirle", "engano", "engañar",
    "engañado", "engañada", "embustero", "embustera", "farsa",
    "farsante", "simulacion", "simular",
    # Inseguridad
    "inseguridad", "inseguro", "insegura", "peligro", "peligroso",
    "peligrosa", "violencia", "violento", "violenta", "agresion",
    "agresivo", "agresiva", "hostil", "hostilidad", "amenaza",
    "amenazar", "aterrorizar",
    # Servicio deficiente
    "demora", "demorado", "demorada", "tardado", "tardada", "lento",
    "lenta", "lentitud", "atraso", "atrasado", "atrasada",
    "espera", "esperar", "colarse", "fila",
}


# ── Negación ──

NEGATION_WORDS: set[str] = {"no", "nunca", "jamas", "tampoco", "ni"}
NEGATION_WINDOW = 3


# ── Tokenizer ──

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def _normalize(text: str) -> str:
    """Lowercase + strip accents for matching."""
    text = text.lower()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(_normalize(text))


# ── Result type ──

@dataclass
class SentimentResult:
    label: str = "neutral"
    score: float = 0.0
    evidence: list[str] = field(default_factory=list)
    counts: dict = field(default_factory=lambda: {
        "positivo": 0, "negativo": 0, "inverted": 0,
    })


# ── Core classifier ──

def classify_sentiment(text: str) -> SentimentResult:
    """Clasifica sentimiento de un texto usando léxico + negación.

    Retorna SentimentResult con label (5 niveles), score numérico,
    evidencia textual y conteos internos.
    """
    if not text or not text.strip():
        return SentimentResult(label="neutral", score=0.0)

    tokens = _tokenize(text)
    if not tokens:
        return SentimentResult(label="neutral", score=0.0)

    positive_hits = 0
    negative_hits = 0
    inverted = 0
    evidence: list[str] = []
    negation_active = False
    negation_countdown = 0

    for token in tokens:
        if token in NEGATION_WORDS:
            negation_active = True
            negation_countdown = NEGATION_WINDOW
            continue

        is_pos = token in POSITIVE_WORDS
        is_neg = token in NEGATIVE_WORDS

        if negation_active and negation_countdown > 0:
            if is_pos:
                negative_hits += 1
                inverted += 1
                evidence.append(f"~~{token}~~(inv)")
                negation_active = False
                negation_countdown = 0
                continue
            elif is_neg:
                positive_hits += 1
                inverted += 1
                evidence.append(f"~~{token}~~(inv)")
                negation_active = False
                negation_countdown = 0
                continue

        if is_pos:
            positive_hits += 1
            evidence.append(token)
        elif is_neg:
            negative_hits += 1
            evidence.append(token)

        if negation_active:
            negation_countdown -= 1
            if negation_countdown <= 0:
                negation_active = False

    total_hits = positive_hits + negative_hits
    if total_hits == 0:
        return SentimentResult(
            label="neutral", score=0.0,
            counts={"positivo": 0, "negativo": 0, "inverted": inverted},
        )

    pos_ratio = positive_hits / total_hits
    neg_ratio = negative_hits / total_hits

    if pos_ratio >= 0.8:
        label = "muy_positivo"
    elif pos_ratio > neg_ratio:
        label = "positivo"
    elif neg_ratio >= 0.8:
        label = "muy_negativo"
    elif neg_ratio > pos_ratio:
        label = "negativo"
    else:
        label = "neutral"

    score = SENTIMENT_ORDER[label]

    return SentimentResult(
        label=label,
        score=float(score),
        evidence=evidence,
        counts={
            "positivo": positive_hits,
            "negativo": negative_hits,
            "inverted": inverted,
        },
    )


# ── Agregación batch ──

def aggregate_sentiment(texts: list[str]) -> dict:
    """Clasifica una lista de textos y retorna estadísticas agregadas.

    Returns dict con:
        - total: total de textos procesados
        - conteo: {label: count} para cada nivel
        - pct: {label: pct} para cada nivel
        - score_promedio: promedio de SENTIMENT_ORDER
        - dominante: label con mayor proporción
        - evidence_muestra: hasta 5 evidencias de ejemplo
    """
    if not texts:
        return _empty_aggregate()

    labels_count = {k: 0 for k in SENTIMENT_ORDER}
    all_scores = []
    sample_evidence: list[str] = []

    for text in texts:
        result = classify_sentiment(text)
        labels_count[result.label] += 1
        all_scores.append(result.score)
        if result.evidence and len(sample_evidence) < 5:
            sample_evidence.extend(result.evidence[:2])

    total = len(texts)
    pct = {
        label: round(count / total * 100, 1)
        for label, count in labels_count.items()
    }
    score_avg = round(sum(all_scores) / total, 2) if total else 0.0

    dominante = max(labels_count, key=lambda k: labels_count[k])
    if labels_count[dominante] == 0:
        dominante = "neutral"

    return {
        "total": total,
        "conteo": labels_count,
        "pct": pct,
        "score_promedio": score_avg,
        "dominante": dominante,
        "evidence_muestra": sample_evidence[:5],
    }


def _empty_aggregate() -> dict:
    return {
        "total": 0,
        "conteo": {k: 0 for k in SENTIMENT_ORDER},
        "pct": {k: 0.0 for k in SENTIMENT_ORDER},
        "score_promedio": 0.0,
        "dominante": "neutral",
        "evidence_muestra": [],
    }
