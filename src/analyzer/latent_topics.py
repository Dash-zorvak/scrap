import logging
import re
from collections import Counter
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    HAS_LDA = True
except ImportError:
    HAS_LDA = False


# Etiquetas legibles para cada categoria tematica (alineadas con topic_detection)
TOPIC_LABELS = {
    "obras_publicas": "Obras públicas",
    "seguridad": "Seguridad",
    "servicios_publicos": "Servicios básicos (agua, luz, basura)",
    "empleo": "Empleo y economía",
    "salud": "Salud",
    "educacion": "Educación",
    "movilidad": "Movilidad y transporte",
    "corrupcion": "Desconfianza y corrupción",
    "medio_ambiente": "Medio ambiente",
    "transparencia": "Transparencia y gestión",
    "cultura": "Cultura y eventos",
    "deportes": "Deportes",
    "apoyo_generico": "Mensajes de apoyo y felicitaciones",
}


def _etiquetar_tema(words: List[str]) -> str:
    """Convierte una lista de palabras frecuentes en un tema legible.

    Primero intenta mapear las palabras a una categoria tematica real
    (obras, seguridad, servicios, etc.). Si no hay coincidencia clara,
    arma una frase corta con las palabras de mayor contenido.
    """
    if not words:
        return "Tema sin clasificar"
    try:
        from src.analyzer.topic_detection import get_main_topic
        categoria = get_main_topic(" ".join(words))
    except Exception:
        categoria = ""
    if categoria and categoria in TOPIC_LABELS:
        return TOPIC_LABELS[categoria]
    principales = [w.capitalize() for w in words[:3]]
    return ", ".join(principales)


# Palabras de cortesia, saludos y muletillas que NO representan un tema real.
# Se excluyen para que los temas reflejen asuntos de ciudad y no formulas sociales.
_CORTESIA_STOP_WORDS = [
    "felicidades", "felicidad", "felicitaciones", "felicito", "felicita",
    "gracias", "agradezco", "muchas", "mucho", "muchos", "mucha",
    "señor", "señora", "señores", "señorita", "don", "doña",
    "alcalde", "alcaldesa", "alcaldia", "alcaldía", "dios", "diosito",
    "bendiciones", "bendición", "bendicion", "bendiga", "bendice",
    "saludos", "hola", "buenas", "buenos", "buen", "buena",
    "día", "dia", "días", "dias", "noche", "noches", "tarde", "tardes",
    "favor", "porfavor", "gente", "vez", "veces", "ahora",
    "aquí", "aqui", "allí", "alli", "bien", "gran", "grande",
    "amen", "amén", "vamos", "siga", "sigan", "adelante", "excelente",
]

_BASE_STOP_WORDS = [
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se",
    "las", "por", "un", "para", "con", "no", "una", "su", "al",
    "lo", "como", "más", "mas", "pero", "sus", "le", "les", "ya",
    "o", "u", "este", "esta", "estas", "estos", "esto", "entre",
    "porque", "ese", "esa", "esos", "esas", "todo", "toda", "todos",
    "todas", "también", "tambien", "fue", "era", "son", "han", "hay",
    "ser", "muy", "sin", "sobre", "cada", "quien", "donde", "cuando",
    "desde", "luego", "entonces", "después", "despues", "tanto",
    "así", "asi", "solo", "sólo", "hace", "hacen", "ello", "ellos",
    "ellas", "nos", "me", "mi", "mis", "tu", "tus", "te", "ti", "yo",
    "él", "ella", "uno", "dos", "si", "sí", "ni", "ha", "he", "has",
    "hemos", "está", "estan", "están", "estoy", "es", "eso", "va",
    "van", "vas", "voy", "ir", "ver", "hacer", "dar", "decir",
    "puede", "pueden", "debe", "deben", "hasta", "aun", "aún",
    "algo", "alguien", "nada", "nadie",
]

# Lista final sin duplicados, preservando el orden.
SPANISH_STOP_WORDS = list(dict.fromkeys(_BASE_STOP_WORDS + _CORTESIA_STOP_WORDS))


def extract_latent_topics(
    texts: List[str],
    n_topics: int = 8,
    n_top_words: int = 10,
    max_features: int = 1000,
) -> Dict[str, Any]:
    if not texts or len(texts) < 10 or not HAS_LDA:
        return {"topics": [], "error": "insufficient data or sklearn unavailable"}

    cleaned = []
    for t in texts:
        if t:
            t_clean = re.sub(r'[^\w\s]', ' ', t.lower())
            t_clean = re.sub(r'\s+', ' ', t_clean).strip()
            if len(t_clean.split()) >= 3:
                cleaned.append(t_clean)

    if len(cleaned) < 10:
        return {"topics": [], "error": "not enough valid documents (need 10+)"}

    try:
        vec = CountVectorizer(
            max_features=max_features,
            stop_words=SPANISH_STOP_WORDS,
            min_df=2,
            max_df=0.85,
        )
        X = vec.fit_transform(cleaned)
        feature_names = vec.get_feature_names_out()

        lda = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=42,
            learning_method="online",
            max_iter=10,
        )
        lda.fit(X)

        topics = []
        for topic_idx, topic in enumerate(lda.components_):
            top_words = [feature_names[i] for i in topic.argsort()[:-n_top_words - 1:-1]]
            topics.append({
                "id": topic_idx,
                "words": top_words,
                "label": _etiquetar_tema(top_words),
                "weight": float(topic.sum()),
            })

        doc_topic_dist = lda.transform(X)
        topic_dominance = Counter()
        for dist in doc_topic_dist:
            dominant = int(dist.argmax())
            topic_dominance[dominant] += 1

        for t in topics:
            t["doc_count"] = int(topic_dominance.get(t["id"], 0))
            t["pct"] = round(t["doc_count"] / len(cleaned) * 100, 1)

        topics.sort(key=lambda x: -x["doc_count"])

        return {
            "topics": topics,
            "n_docs": len(cleaned),
            "n_topics": n_topics,
            "vocabulary_size": len(feature_names),
        }

    except Exception as e:
        logger.warning(f"Latent topic extraction failed: {e}")
        return {"topics": [], "error": str(e)}
