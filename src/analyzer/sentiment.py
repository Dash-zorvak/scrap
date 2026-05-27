import logging
import signal
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

_INIT_TIMEOUT = 60


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
        from pysentimiento import create_analyzer

        def _load():
            sa = create_analyzer(task="sentiment", lang="es")
            ea = create_analyzer(task="emotion", lang="es")
            return sa, ea

        loaded = _run_with_timeout(_load)
        if loaded is not None:
            _sentiment_analyzer, _emotion_analyzer = loaded
            HAS_PYSENTIMIENTO = True
            logger.info("pysentimiento loaded successfully")
        else:
            logger.warning("pysentimiento initialization timed out — using rule-based")
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

        loaded = _run_with_timeout(_load)
        if loaded is not None:
            _fallback_analyzer = loaded
            HAS_FALLBACK = True
            logger.info("Transformers fallback loaded successfully")
        else:
            logger.warning("Transformers fallback timed out — using rule-based")
            HAS_FALLBACK = False
    except Exception as e:
        logger.debug(f"Transformers fallback not available: {e}")
        HAS_FALLBACK = False


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

            if probs.get("POS", 0) > probs.get("NEG", 0) and probs.get("POS", 0) > probs.get("NEU", 0):
                label = "positive"
                score = probs.get("POS", 0)
            elif probs.get("NEG", 0) > probs.get("NEU", 0):
                label = "negative"
                score = probs.get("NEG", 0)
            else:
                label = "neutral"
                score = probs.get("NEU", 0)

            return (label, round(score, 4))
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
                label = "neutral"

            return (label, round(score, 4))
        except Exception as e:
            logger.warning(f"Transformers analysis failed: {e}")
            return self._analyze_rule_based(text)

    @staticmethod
    def _match_word(word: str, stems: set) -> bool:
        word = word.strip(".,!?;:¡¿\"'()").lower()
        if not word or len(word) < 3:
            return False
        if word in stems:
            return True
        for s in [word[:-1], word.rstrip("s"), word.rstrip("aeo"),
                   word.rstrip("os").rstrip("as")]:
            if len(s) >= 3 and s in stems:
                return True
        for suf in ("ado", "ado", "ido", "ada", "ida", "ando", "iendo",
                     "ción", "sión", "miento", "mente", "ado", "ido"):
            if word.endswith(suf) and len(word) - len(suf) >= 3:
                base = word[: -len(suf)]
                if base in stems:
                    return True
                if base.rstrip("aeo") in stems:
                    return True
        return False

    def _analyze_rule_based(self, text: str) -> tuple[str, float]:
        text_lower = text.lower()

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
            "increíble", "increíbles",
            "fantástico", "fantástica", "fantásticos", "fantásticas",
            "apoyo", "apoyar", "apoyamos", "apoyan",
            "adelante", "avance", "avances", "avanzando", "avanzamos",
            "progreso", "progresando", "progresamos",
            "trabajo", "trabajando", "trabajamos", "trabajar",
            "logro", "logros", "logrado", "logramos",
            "éxito", "exitosa", "exitoso", "exitosos",
            "beneficio", "beneficios", "beneficiando",
            "orgullo", "orgulloso", "orgullosa",
            "bonito", "bonita", "bonitos", "bonitas",
            "contento", "contenta", "contentos", "contentas",
            "alegría", "alegre", "alegres",
            "gusta", "gustan", "gustó",
            "aprecio", "apreciamos",
            "bendición", "bendiciones",
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
            "unidos", "unidas", "unidad", "unión",
            "liderazgo", "líder", "liderando",
            "cumpliendo", "cumplimos", "cumplió",
            "resultados", "resultado",
            "proyecto", "proyectos",
            "recuperación", "recuperando",
        }

        negative_words = {
            "malo", "mala", "malos", "malas", "mal", "males",
            "pésimo", "pésima", "pésimos", "pésimas",
            "horrible", "horribles",
            "triste", "tristes", "tristeza",
            "corrupto", "corrupta", "corruptos", "corruptas",
            "corrupción",
            "fracaso", "fracasos", "fracasado", "fracasó",
            "peor", "peores",
            "deficiente", "deficientes", "deficiencia",
            "incompetente", "incompetentes", "incompetencia",
            "mentira", "mentiras", "miente", "mienten",
            "engaño", "engañando", "engañó",
            "robo", "robos", "robó", "roban", "robar",
            "ladrón", "ladrona", "ladrones",
            "inseguridad", "inseguro", "insegura",
            "delincuencia", "delincuente", "delincuentes",
            "violencia", "violento", "violenta",
            "basura", "desastre", "desastres",
            "vergüenza", "vergonzoso",
            "asqueroso", "asquerosa",
            "odio", "odian", "odiado",
            "detesto", "detestable", "detestan",
            "desempleo", "desempleados",
            "pobreza", "pobre", "pobres",
            "abandono", "abandonado", "abandonó",
            "incumplimiento", "incumplió", "incumplen",
            "promesa", "promesas",
            "falso", "falsa", "falsos", "falsas",
            "ineficiente", "ineficientes", "ineficiencia",
            "inepto", "inepta", "ineptos",
            "crisis", "emergencia", "emergencias",
            "caos", "abusos", "abuso",
            "injusticia", "injusto", "injusta",
            "represión", "represivo",
            "autoritarismo", "autoritario", "autoritaria",
            "dictadura", "oposición",
            "conflicto", "conflictos",
            "problema", "problemas",
            "grave", "graves", "gravedad",
            "preocupante", "preocupantes",
            "deuda", "deudas",
            "impuesto", "impuestos",
            "aumento", "aumentos", "aumentó",
            "recorte", "recortes",
            "gobierno", "gobiernos",
        }

        words = text_lower.split()
        positives = sum(1 for w in words if self._match_word(w, positive_words))
        negatives = sum(1 for w in words if self._match_word(w, negative_words))

        negation_words = {"no", "nunca", "jamás", "tampoco", "ni"}
        for i, word in enumerate(words):
            word_clean = word.strip(".,!?;:¡¿\"'()")
            if word_clean in negation_words:
                for j in range(i + 1, min(i + 4, len(words))):
                    next_clean = words[j].strip(".,!?;:¡¿\"'()")
                    if self._match_word(next_clean, positive_words):
                        negatives += 1
                        positives = max(0, positives - 1)
                        break

        positives = max(0, positives)
        negatives = max(0, negatives)

        total = positives + negatives
        if total == 0:
            return ("neutral", 0.0)

        if positives > negatives:
            score = positives / total
            return ("positive", round(score, 4))
        elif negatives > positives:
            score = negatives / total
            return ("negative", round(score, 4))
        else:
            return ("neutral", round(positives / total, 4) if total > 0 else 0.0)

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

            text_lower = text.lower()
            scores = defaultdict(float)
            words = re.findall(r'\w+', text_lower)
            for emotion, keywords in EMOTION_LEXICON.items():
                score = 0
                for kw in keywords:
                    if kw in text_lower:
                        score += text_lower.count(kw)
                if score > 0:
                    scores[emotion] = score
            total = sum(scores.values()) or 1
            if not scores:
                return {"neutral": 1.0}
            return {k: round(v / total, 4) for k, v in sorted(scores.items(), key=lambda x: -x[1])}
        except Exception as e:
            logger.warning(f"Lexicon emotion analysis failed: {e}")
            return {}
