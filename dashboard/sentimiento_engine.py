"""Motor de sentimiento enchufable: BERT (pysentimiento) → Groq → reglas."""

import logging
import os
import threading
import time
import unicodedata
import re

from dashboard.llm_groq import chat_texto, groq_disponible

logger = logging.getLogger("sentimiento")

ULTIMO_ERROR_BERT = None
ULTIMO_ERROR_GROQ = None
_BERT_FALLO = False
_BERT_FALLO_TS = 0.0
BERT_RETRY_COOLDOWN_S = int(os.environ.get("BERT_RETRY_COOLDOWN_S", "600"))

BERT_LOAD_TIMEOUT_S = int(os.environ.get("BERT_LOAD_TIMEOUT_S", "120"))

POSITIVE_WORDS = {
    "buen", "buena", "bueno", "buenos", "buenas",
    "excelente", "excelentes", "genial", "geniales",
    "feliz", "felices", "felicidad", "gracias",
    "agradecido", "agradecida", "bien", "mejor", "mejores",
    "perfecto", "perfecta", "hermoso", "hermosa",
    "maravilloso", "maravillosa", "increible", "increibles",
    "fantastico", "fantastica", "apoyo", "apoyar",
    "adelante", "avance", "avances", "progreso",
    "trabajo", "trabajando", "logro", "logros",
    "exito", "exitosa", "exitoso",
    "beneficio", "beneficios", "orgullo", "orgulloso",
    "bonito", "bonita", "contento", "contenta",
    "alegria", "alegre", "gusta", "aprecio",
    "bendicion", "bendiciones", "seguridad", "seguro",
    "desarrollo", "crecimiento", "oportunidad",
    "transparencia", "honestidad", "eficiente",
    "victoria", "triunfo", "esperanza",
    "unidos", "unidad", "liderazgo",
    "magnifico", "espectacular", "brillante", "impresionante",
    "fenomenal", "estupendo",
}

NEGATIVE_WORDS = {
    "malo", "mala", "malos", "mal", "pesimo", "pesima",
    "horrible", "horribles",
    "triste", "tristes", "tristeza",
    "corrupto", "corrupta", "corrupcion",
    "fracaso", "fracasos", "peor", "peores",
    "deficiente", "incompetente", "mentira", "mentiras",
    "engano", "robo", "robos", "ladron", "ladrones",
    "inseguridad", "delincuencia", "violencia",
    "basura", "desastre", "verguenza", "vergonzoso",
    "odio", "detesto",
    "desempleo", "pobreza", "pobre", "pobres",
    "abandono", "abandonado", "incumplimiento",
    "falso", "falsa", "ineficiente",
    "crisis", "emergencia", "caos", "abusos",
    "injusticia", "injusto",
    "conflicto", "problema", "problemas",
    "grave", "graves", "preocupante",
    "deuda", "deudas", "aumento", "recorte",
    "lamentable", "deplorable", "desastroso",
    "intolerable", "insoportable", "nefasto",
}

NEGATION_WORDS = {"no", "nunca", "jamas", "tampoco", "ni"}


def _normalize(word):
    return unicodedata.normalize('NFKD', word).encode('ascii', 'ignore').decode('ascii')


def _match_word(word, stems):
    word = word.strip(".,!?;:¿¡\"'()").lower()
    word = _normalize(word)
    if not word or len(word) < 3:
        return False
    if word in stems:
        return True
    for s in [word[:-1], word.rstrip("s"), word.rstrip("aeo"),
               word.rstrip("os").rstrip("as")]:
        if len(s) >= 3 and s in stems:
            return True
    for suf in ("ado", "ido", "ada", "ida", "ando", "iendo",
                 "cion", "sion", "miento", "mente"):
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            base = word[:-len(suf)]
            if base in stems:
                return True
            if base.rstrip("aeo") in stems:
                return True
    return False


def analizar_sentimiento_rapido(texto):
    if not texto:
        return ("NEU", 0.0)
    text_norm = _normalize(texto.lower())
    words = text_norm.split()

    positives = sum(1 for w in words if _match_word(w, POSITIVE_WORDS))
    negatives = sum(1 for w in words if _match_word(w, NEGATIVE_WORDS))

    for i, word in enumerate(words):
        wc = word.strip(".,!?;:¿¡\"'()")
        if wc in NEGATION_WORDS:
            for j in range(i + 1, min(i + 4, len(words))):
                nw = words[j].strip(".,!?;:¿¡\"'()")
                if _match_word(nw, POSITIVE_WORDS):
                    negatives += 1
                    positives = max(0, positives - 1)
                    break

    positives = max(0, positives)
    negatives = max(0, negatives)
    total = positives + negatives

    if total == 0:
        return ("NEU", 0.0)

    if positives > 0 and negatives == 0:
        return ("POS", round(min(positives / 5, 0.95), 4))
    elif negatives > 0 and positives == 0:
        return ("NEG", round(min(negatives / 5, 0.95), 4))

    ratio = positives / total
    if ratio >= 0.66:
        return ("POS", round(ratio, 4))
    elif ratio <= 0.33:
        return ("NEG", round(1 - ratio, 4))
    return ("NEU", round(ratio, 4))


_bert_analyzer = None
_bert_lock = threading.Lock()


def _cargar_bert():
    global _bert_analyzer
    if _bert_analyzer is not None:
        return _bert_analyzer
    from pysentimiento import create_analyzer
    _bert_analyzer = create_analyzer(task="sentiment", lang="es")
    return _bert_analyzer


def _clasificar_bert(textos):
    analyzer = _cargar_bert()
    resultados = []
    for output in analyzer.predict(textos):
        label = output.output
        score = output.probas.get(label, 0.0)
        resultados.append((label, round(float(score), 4)))
    return resultados


_PROMPT_SENTIMIENTO = (
    "Eres un clasificador de sentimiento en español. "
    "Clasifica cada texto como POS (positivo), NEG (negativo) o NEU (neutral). "
    "Devuelve SOLO un JSON object con una clave 'resultados' que sea un array de objetos, "
    "cada uno con 'label' (POS|NEG|NEU) y 'confianza' (número decimal entre 0 y 1 que refleje "
    "qué tan seguro estás de esa clasificación). "
    "NO devuelvas markdown ni texto adicional.\n\n"
    "Textos:\n"
)


_SCORE_RESPALDO_GROQ = 0.7

def _clasificar_groq_lote(textos):
    import json
    items = "\n".join(f"{i}. {t}" for i, t in enumerate(textos))
    try:
        raw_resp, _, _ = chat_texto(_PROMPT_SENTIMIENTO + items, json=True, temperature=0, max_tokens=4096)
        parsed = json.loads(raw_resp)
    except Exception as e:
        raise e
    raw = parsed.get("resultados", parsed if isinstance(parsed, list) else [])
    if len(raw) != len(textos):
        logger.warning(
            "Groq devolvió %d resultados de sentimiento pero se esperaban %d; "
            "los faltantes se completan como NEU con score de respaldo %.1f",
            len(raw), len(textos), _SCORE_RESPALDO_GROQ,
        )
    resultados = []
    confianzas_invalidas = 0
    for i, texto in enumerate(textos):
        entry = raw[i] if i < len(raw) else {}
        label = entry.get("label", "NEU")
        if label not in ("POS", "NEG", "NEU"):
            label = "NEU"
        confianza = entry.get("confianza")
        if isinstance(confianza, (int, float)) and not isinstance(confianza, bool) and 0.0 <= confianza <= 1.0:
            score = round(float(confianza), 4)
        else:
            score = _SCORE_RESPALDO_GROQ
            confianzas_invalidas += 1
        resultados.append((label, score))
    if confianzas_invalidas:
        logger.warning(
            "Groq no devolvió una 'confianza' válida para %d de %d textos; "
            "se usó el score de respaldo %.1f para esos casos",
            confianzas_invalidas, len(textos), _SCORE_RESPALDO_GROQ,
        )
    return resultados


def _clasificar_reglas(textos):
    return [analizar_sentimiento_rapido(t) for t in textos]


def clasificar_lote(textos):
    global ULTIMO_ERROR_BERT, ULTIMO_ERROR_GROQ, _BERT_FALLO

    if not textos:
        return [], "reglas"
    empty_mask = [not t or not t.strip() for t in textos]
    non_empty_texts = [t for t, is_empty in zip(textos, empty_mask) if not is_empty]

    if not non_empty_texts:
        return [("NEU", 0.0)] * len(textos), "reglas"

    motor_forzado = os.environ.get("MOTOR_SENTIMIENTO", "auto")

    motor = "reglas"
    resultados_non_empty = None

    def _intentar_bert():
        nonlocal motor, resultados_non_empty
        global _BERT_FALLO, _BERT_FALLO_TS, ULTIMO_ERROR_BERT
        bert_ok = False
        bert_resultados = None
        carga_ok = [False]
        carga_exception = [None]
        cooldown_pasado = (time.time() - _BERT_FALLO_TS) >= BERT_RETRY_COOLDOWN_S
        timeout = BERT_LOAD_TIMEOUT_S if (not _BERT_FALLO or cooldown_pasado) else 1

        def _load_bert():
            try:
                _cargar_bert()
                carga_ok[0] = True
            except Exception as e:
                carga_exception[0] = e

        t = threading.Thread(target=_load_bert, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if not carga_ok[0]:
            _BERT_FALLO = True
            _BERT_FALLO_TS = time.time()
            exc = carga_exception[0]
            ULTIMO_ERROR_BERT = repr(exc) if exc else "timeout"
            logger.warning("BERT carga falló: %s", ULTIMO_ERROR_BERT)
            return False

        _BERT_FALLO = False
        try:
            bert_resultados = _clasificar_bert(non_empty_texts)
            bert_ok = True
        except Exception as e:
            ULTIMO_ERROR_BERT = repr(e)
            logger.warning("BERT predicción falló: %r", e)
            bert_ok = False

        if bert_ok:
            motor = "bert"
            resultados_non_empty = bert_resultados
            return True
        return False

    def _intentar_groq():
        nonlocal motor, resultados_non_empty
        global ULTIMO_ERROR_GROQ
        try:
            if groq_disponible():
                groq_resultados = _clasificar_groq_lote(non_empty_texts)
                resultados_non_empty = groq_resultados
                motor = "groq"
                return True
        except Exception as e:
            ULTIMO_ERROR_GROQ = repr(e)
            logger.warning("Groq sentiment falló: %r", e)
        return False

    if motor_forzado == "bert":
        _intentar_bert()
    elif motor_forzado == "groq":
        _intentar_groq()
    elif motor_forzado == "reglas":
        pass
    else:
        if not _intentar_bert():
            _intentar_groq()

    if resultados_non_empty is None:
        motor = "reglas"
        resultados_non_empty = _clasificar_reglas(non_empty_texts)

    resultados = []
    idx = 0
    for is_empty in empty_mask:
        if is_empty:
            resultados.append(("NEU", 0.0))
        else:
            resultados.append(resultados_non_empty[idx])
            idx += 1

    return resultados, motor
