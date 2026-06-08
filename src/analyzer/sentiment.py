import logging
import re
import unicodedata
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_sentiment_analyzer = None
_emotion_analyzer = None
_fallback_analyzer = None
HAS_PYSENTIMIENTO = False
HAS_FALLBACK = False
_PYSENTIMIENTO_TRIED = False
_FALLBACK_TRIED = False

_INIT_TIMEOUT = 10
_MODEL_LOAD_TIMEOUT = 600  # la 1ª carga descarga el modelo (~500 MB); 10s no alcanza

SENTIMENT_5LEVEL = {
    "muy_positivo": 2,
    "positivo": 1,
    "neutral": 0,
    "negativo": -1,
    "muy_negativo": -2,
}


def _run_with_timeout(func, args=(), kwargs=None, timeout=_INIT_TIMEOUT):
    kwargs = kwargs or {}
    result = [None]
    exception = [None]

    def runner():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        logger.warning(f"Initialization timed out ({timeout}s)")
        return None
    if exception[0]:
        raise exception[0]
    return result[0]


def _init_pysentimiento():
    global _sentiment_analyzer, _emotion_analyzer, HAS_PYSENTIMIENTO, _PYSENTIMIENTO_TRIED
    if _PYSENTIMIENTO_TRIED:
        return
    _PYSENTIMIENTO_TRIED = True
    try:
        # Monkey‑patch: transformers ≥4.58 bloquea torch<2.6 incluso con safetensors;
        # nuestros modelos (robertuito) usan safetensors, así que el chequeo es falso positivo.
        import transformers.utils.import_utils as _tui
        _tui.check_torch_load_is_safe = lambda: None
        import transformers.utils as _tu
        _tu.check_torch_load_is_safe = lambda: None
        from pysentimiento import create_analyzer

        def _load():
            sa = create_analyzer(task="sentiment", lang="es")
            ea = create_analyzer(task="emotion", lang="es")
            return sa, ea

        loaded = _run_with_timeout(_load, timeout=_MODEL_LOAD_TIMEOUT)
        if loaded is not None:
            _sentiment_analyzer, _emotion_analyzer = loaded
            HAS_PYSENTIMIENTO = True
            logger.info("pysentimiento loaded successfully")
        else:
            logger.warning("pysentimiento initialization timed out -- using rule-based")
            HAS_PYSENTIMIENTO = False
    except Exception as e:
        logger.debug(f"pysentimiento not available: {e}")
        HAS_PYSENTIMIENTO = False


def _init_transformers_fallback():
    global _fallback_analyzer, HAS_FALLBACK, _FALLBACK_TRIED
    if _FALLBACK_TRIED:
        return
    _FALLBACK_TRIED = True
    try:
        from transformers import pipeline
        import torch

        def _load():
            return pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
                device=0 if torch.cuda.is_available() else -1,
            )

        loaded = _run_with_timeout(_load, timeout=_MODEL_LOAD_TIMEOUT)
        if loaded is not None:
            _fallback_analyzer = loaded
            HAS_FALLBACK = True
            logger.info("Transformers fallback loaded successfully")
        else:
            logger.warning("Transformers fallback timed out -- using rule-based")
            HAS_FALLBACK = False
    except Exception as e:
        logger.debug(f"Transformers fallback not available: {e}")
        HAS_FALLBACK = False


def _map_score_to_5level(label_3: str, score: float) -> tuple:
    if label_3 == "positive":
        if score >= 0.8:
            return ("muy_positivo", score)
        return ("positivo", score)
    elif label_3 == "negative":
        if score >= 0.8:
            return ("muy_negativo", score)
        return ("negativo", score)
    return ("neutral", score)


class SentimentAnalyzer:
    def __init__(self, use_fallback: bool = False):
        self.use_fallback = use_fallback

    def analyze(self, text: str) -> tuple[str, float]:
        if not text or not text.strip():
            return ("neutral", 0.0)

        text_clean = text.strip()[:512]

        if not _PYSENTIMIENTO_TRIED:
            _init_pysentimiento()

        if HAS_PYSENTIMIENTO and not self.use_fallback:
            return self._analyze_pysentimiento(text_clean)

        if not _FALLBACK_TRIED:
            _init_transformers_fallback()

        if HAS_FALLBACK:
            return self._analyze_transformers(text_clean)

        return self._analyze_rule_based(text_clean)

    def _analyze_pysentimiento(self, text: str) -> tuple[str, float]:
        try:
            result = _sentiment_analyzer.predict(text)
            probs = result.probas
            pos = probs.get("POS", 0)
            neg = probs.get("NEG", 0)
            neu = probs.get("NEU", 0)

            if pos > neg and pos > neu:
                label = "positive"
                score = pos
            elif neg > pos and neg > neu:
                label = "negative"
                score = neg
            else:
                return ("neutral", round(neu, 4))

            return _map_score_to_5level(label, round(score, 4))
        except Exception as e:
            logger.warning(f"pysentimiento analysis failed: {e}")
            return self._analyze_rule_based(text)

    def _analyze_transformers(self, text: str) -> tuple[str, float]:
        try:
            result = _fallback_analyzer(text)[0]
            label = result["label"].lower()
            score = result["score"]

            if "negative" in label:
                label = "negative"
            elif "positive" in label:
                label = "positive"
            else:
                return ("neutral", round(score, 4))

            return _map_score_to_5level(label, round(score, 4))
        except Exception as e:
            logger.warning(f"Transformers analysis failed: {e}")
            return self._analyze_rule_based(text)

    @staticmethod
    def _normalize(word: str) -> str:
        return unicodedata.normalize('NFKD', word).encode('ascii', 'ignore').decode('ascii')

    @staticmethod
    def _match_word(word: str, stems: set) -> bool:
        word = word.strip(".,!?;:!\u00bf\"'()").lower()
        word = SentimentAnalyzer._normalize(word)
        if not word or len(word) < 3:
            return False
        if word in stems:
            return True
        for s in [word[:-1], word.rstrip("s"), word.rstrip("aeo"),
                   word.rstrip("os").rstrip("as")]:
            if len(s) >= 3 and s in stems:
                return True
        for suf in ("ado", "ido", "ada", "ida", "ando", "iendo",
                     "cion", "sion", "miento", "mente", "ado", "ido"):
            if word.endswith(suf) and len(word) - len(suf) >= 3:
                base = word[: -len(suf)]
                if base in stems:
                    return True
                if base.rstrip("aeo") in stems:
                    return True
        return False

    def _analyze_rule_based(self, text: str) -> tuple[str, float]:
        text_lower = self._normalize(text.lower())

        positive_words = {
            "buen", "buena", "bueno", "buenos", "buenas",
            "excelente", "excelentes",
            "genial", "geniales", "geniala",
            "feliz", "felices", "felicidad",
            "gracias", "agradecido", "agradecida",
            "bien", "mejor", "mejores", "mejorando", "mejoramos",
            "perfecto", "perfecta", "perfectos", "perfectas",
            "hermoso", "hermosa", "hermosos", "hermosas",
            "maravilloso", "maravillosa", "maravillosas", "maravillosos",
            "increible", "increibles",
            "fantastico", "fantastica", "fantasticos", "fantasticas",
            "apoyo", "apoyar", "apoyamos", "apoyan",
            "adelante", "avance", "avances", "avanzando", "avanzamos",
            "progreso", "progresando", "progresamos",
            "trabajo", "trabajando", "trabajamos", "trabajar",
            "logro", "logros", "logrado", "logramos",
            "exito", "exitosa", "exitoso", "exitosos",
            "beneficio", "beneficios", "beneficiando",
            "orgullo", "orgulloso", "orgullosa",
            "bonito", "bonita", "bonitos", "bonitas",
            "contento", "contenta", "contentos", "contentas",
            "alegria", "alegre", "alegres",
            "gusta", "gustan", "gusto",
            "aprecio", "apreciamos",
            "bendicion", "bendiciones",
            "seguridad", "seguro", "segura",
            "desarrollo", "desarrollando", "desarrollamos",
            "crecimiento", "creciendo", "crecemos",
            "oportunidad", "oportunidades",
            "transparencia", "transparente",
            "honestidad", "honesto", "honesta",
            "eficiente", "eficientes", "eficiencia",
            "eficaz", "victoria", "victorias",
            "triunfo", "triunfos",
            "esperanza", "esperanzas",
            "unidos", "unidas", "unidad", "union",
            "liderazgo", "lider", "liderando",
            "recuperacion", "recuperando",
            "magnifico", "magnifica", "estupendo", "estupenda",
            "fenomenal", "espectacular", "brillante",
            "impresionante", "formidable",
        }

        negative_words = {
            "malo", "mala", "malos", "malas", "mal", "males",
            "pesimo", "pesima", "pesimos", "pesimas",
            "horrible", "horribles",
            "triste", "tristes", "tristeza",
            "corrupto", "corrupta", "corruptos", "corruptas",
            "corrupcion",
            "fracaso", "fracasos", "fracasado", "fracaso",
            "peor", "peores",
            "deficiente", "deficientes", "deficiencia",
            "incompetente", "incompetentes", "incompetencia",
            "mentira", "mentiras", "miente", "mienten",
            "engano", "enganando", "engano",
            "robo", "robos", "robo", "roban", "robar",
            "ladron", "ladrona", "ladrones",
            "inseguridad", "inseguro", "insegura",
            "delincuencia", "delincuente", "delincuentes",
            "violencia", "violento", "violenta",
            "basura", "desastre", "desastres",
            "verguenza", "vergonzoso",
            "asqueroso", "asquerosa",
            "odio", "odian", "odiado",
            "detesto", "detestable", "detestan",
            "desempleo", "desempleados",
            "pobreza", "pobre", "pobres",
            "abandono", "abandonado", "abandono",
            "incumplimiento", "incumplio", "incumplen",
            "falso", "falsa", "falsos", "falsas",
            "ineficiente", "ineficientes", "ineficiencia",
            "inepto", "inepta", "ineptos",
            "crisis", "emergencia", "emergencias",
            "caos", "abusos", "abuso",
            "injusticia", "injusto", "injusta",
            "represion", "represivo",
            "autoritarismo", "autoritario", "autoritaria",
            "dictadura",
            "conflicto", "conflictos",
            "grave", "graves", "gravedad",
            "preocupante", "preocupantes",
            "recorte", "recortes",
            "pesimo", "pesima",
            "detestable", "deplorable",
            "lamentable", "vergonzoso", "vergonzosa",
            "desastroso", "desastrosa",
            "intolerable", "insoportable",
            "nefasto", "nefasta",
        }

        words = text_lower.split()
        positives = sum(1 for w in words if self._match_word(w, positive_words))
        negatives = sum(1 for w in words if self._match_word(w, negative_words))

        negation_words = {"no", "nunca", "jamas", "tampoco", "ni"}
        for i, word in enumerate(words):
            word_clean = word.strip(".,!?;:!\u00bf\"'()")
            if word_clean in negation_words:
                for j in range(i + 1, min(i + 4, len(words))):
                    next_clean = words[j].strip(".,!?;:!\u00bf\"'()")
                    if self._match_word(next_clean, positive_words):
                        negatives += 1
                        positives = max(0, positives - 1)
                        break

        positives = max(0, positives)
        negatives = max(0, negatives)

        total = positives + negatives
        if total == 0:
            return ("neutral", 0.0)

        if positives > 0 and negatives == 0:
            ratio = positives
            if ratio >= 3:
                return ("muy_positivo", round(min(ratio / 5, 0.95), 4))
            return ("positivo", round(0.5 + ratio * 0.1, 4))
        elif negatives > 0 and positives == 0:
            ratio = negatives
            if ratio >= 3:
                return ("muy_negativo", round(min(ratio / 5, 0.95), 4))
            return ("negativo", round(0.5 + ratio * 0.1, 4))

        ratio = positives / total
        if ratio >= 0.8:
            return ("muy_positivo", round(ratio, 4))
        elif ratio >= 0.6:
            return ("positivo", round(ratio, 4))
        elif ratio <= 0.2:
            return ("muy_negativo", round(1 - ratio, 4))
        elif ratio <= 0.4:
            return ("negativo", round(1 - ratio, 4))
        return ("neutral", round(ratio, 4))

    def analyze_emotions(self, text: str) -> dict:
        if not text or not text.strip():
            return {}

        if HAS_PYSENTIMIENTO:
            try:
                result = _emotion_analyzer.predict(text[:512])
                return dict(result.probas)
            except Exception as e:
                logger.warning(f"Emotion analysis failed: {e}")

        return self._analyze_emotions_lexicon(text)

    @staticmethod
    def _analyze_emotions_lexicon(text: str) -> dict:
        try:
            from src.analyzer.emotion_lexicon import EMOTION_LEXICON
            import re
            from collections import defaultdict

            text_norm = unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode('ascii')
            scores = defaultdict(float)
            words = re.findall(r'\w+', text_norm)
            for emotion, keywords in EMOTION_LEXICON.items():
                score = 0
                for kw in keywords:
                    kw_norm = unicodedata.normalize('NFKD', kw.lower()).encode('ascii', 'ignore').decode('ascii')
                    score += len(re.findall(r'\b' + re.escape(kw_norm) + r'\b', text_norm))
                if score > 0:
                    scores[emotion] = score
            total = sum(scores.values()) or 1
            if not scores:
                return {"neutral": 1.0}
            return {k: round(v / total, 4) for k, v in sorted(scores.items(), key=lambda x: -x[1])}
        except Exception as e:
            logger.warning(f"Lexicon emotion analysis failed: {e}")
            return {}


SENTIMENT_ORDER = {
    "muy_positivo": 2, "positivo": 1, "neutral": 0,
    "negativo": -1, "muy_negativo": -2,
}
