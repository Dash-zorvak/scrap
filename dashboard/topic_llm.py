"""Clasificacion de temas ciudadanos con IA (contexto + tono + postura).

Un modelo de lenguaje lee cada comentario completo y decide:
  - categoria: uno de los temas ENGLOBANTES (ver dashboard/tema_taxonomia.py) o
    'no_aplica' si el comentario no habla de ningun asunto municipal.
  - tono: 'literal' o 'sarcastico'.
  - postura: 'apoyo', 'critica' o 'neutral' (polaridad hacia la gestion). Es un
    eje SEPARADO del tema: el tema dice DE QUE habla; la postura dice COMO lo
    dice. Asi una queja sobre un tema NO infla ese tema como impulso positivo.
  - confianza: 0.0 a 1.0.

Si el proveedor no esta disponible o el modelo falla, se cae con elegancia al
detector por palabras clave (get_main_topic), remapeando sus claves historicas a
las englobantes. El modelo se configura via llm_groq y es compatible con OpenAI.

Aprendizaje (few-shot, sin reentrenar y a costo 0): clasificar_temas_lote acepta
`ejemplos` (lista de {texto, tema} ya aprobados por el usuario) que se inyectan
al prompt para alinear las sugerencias con el criterio humano.

Cascada de verificacion cruzada: el modelo primario clasifica todo; los casos
dudosos (baja confianza o sarcasmo) se re-evaluan con un segundo modelo distinto
(VERIFIER_MODEL) y se reconcilian. Ver dashboard/llm_cascade.py. Se desactiva
con LLM_CASCADA_ACTIVA=0.

Control de ritmo (pacing): se espacian las llamadas para no superar
TOPIC_LLM_TPM y, si llega un 429, se espera lo que indique el proveedor y se
reintenta.
"""

import functools
import json
import logging
import os
import re
import time

from dashboard.tema_taxonomia import (
    CATEGORIAS_VALIDAS,
    TEMAS as _TEMAS,
    normalizar_postura as _normalizar_postura,
    remapear as _remapear,
)

logger = logging.getLogger("topic_llm")

TONOS_VALIDOS = {"literal", "sarcastico"}

# Cuantos comentarios se mandan por llamada al modelo (controla costo/latencia).
LOTE_LLM = int(os.environ.get("TOPIC_LLM_LOTE", "40"))

# Cuantos caracteres por comentario se envian (evita prompts gigantes).
MAX_CHARS_COMENTARIO = int(os.environ.get("TOPIC_LLM_MAX_CHARS", "300"))

# Presupuesto de tokens por minuto. 0 desactiva el pacing.
TPM_BUDGET = int(os.environ.get("TOPIC_LLM_TPM", "10000"))

# Reintentos ante un 429 antes de caer al respaldo por reglas.
MAX_REINTENTOS_429 = int(os.environ.get("TOPIC_LLM_REINTENTOS", "5"))

# Espera por defecto (segundos) si el 429 no dice cuanto esperar.
ESPERA_429_DEFAULT = float(os.environ.get("TOPIC_LLM_ESPERA_429", "16"))

# Cascada de verificacion cruzada. 0 la desactiva.
CASCADA_ACTIVA = os.environ.get("LLM_CASCADA_ACTIVA", "1") not in ("0", "false", "False", "")

# Historial de consumo para el pacing: list[(timestamp, tokens_estimados)].
_historial_tokens = []


def _construir_prompt_base(ejemplos=None):
    """Arma el prompt fijo a partir de la taxonomia englobante.

    Si se pasan `ejemplos` (few-shot validados por el usuario), se inyectan como
    guia de criterio.
    """
    lineas = [
        "Eres un analista que clasifica comentarios ciudadanos de las redes "
        "sociales de una alcaldia de El Salvador (Santa Ana). Para CADA "
        "comentario decide cuatro cosas.",
        "",
        "1) \"categoria\": el asunto ciudadano del que habla. Usa UNA de estas "
        "claves EXACTAS:",
    ]
    for clave, info in _TEMAS.items():
        lineas.append(f"   - {clave}: {info.get('desc', '')}")
    lineas += [
        "",
        "MUY IMPORTANTE - el tema es NEUTRAL: describe el ASUNTO, no si el "
        "comentario es bueno o malo. Una queja, un reclamo, un reproche o una "
        "burla sobre un asunto municipal SI tienen tema: van en la categoria de "
        "ese asunto (por ejemplo, una critica sobre la honestidad o el manejo "
        "del gobierno local va en 'gobernanza'), NO en 'no_aplica'. Solo usa "
        "'no_aplica' cuando de plano no se habla de ningun asunto municipal.",
        "",
        "MUY IMPORTANTE - dichos y sarcasmo salvadorenos: muchos comentarios "
        "usan frases hechas que NO hablan del tema literal. Por ejemplo "
        "'panchito el rio estaba' es un dicho burlon; NO habla de un rio ni de "
        "medio ambiente, asi que su categoria es 'no_aplica'. No te dejes "
        "enganar por una sola palabra: clasifica por el SENTIDO real del "
        "comentario completo.",
        "",
        "2) \"tono\": \"literal\" si dice lo que parece; \"sarcastico\" si es "
        "ironico o burla (por ejemplo 'excelente trabajo, lo que faltaba').",
        "",
        "3) \"postura\": la actitud del comentario hacia la gestion municipal. "
        "Usa UNA de estas claves EXACTAS:",
        "   - apoyo: felicita, agradece, respalda o defiende.",
        "   - critica: reclama, se queja, expresa enojo, reprocha o se burla.",
        "   - neutral: pregunta o comenta sin una postura clara a favor o en contra.",
        "   La postura es INDEPENDIENTE del tema y del tono: un comentario "
        "sarcastico suele ser 'critica'. Para 'no_aplica' usa normalmente "
        "'neutral' salvo que sea una burla clara ('critica').",
        "",
        "4) \"confianza\": numero de 0.0 a 1.0 de que tan seguro estas.",
        "",
    ]
    if ejemplos:
        lineas.append(
            "EJEMPLOS YA VALIDADOS POR UN HUMANO (usalos como guia de criterio e "
            "imita estas decisiones en casos parecidos):"
        )
        for ej in ejemplos:
            t = " ".join(str(ej.get("texto", "")).split())[:200]
            tema = ej.get("tema", "")
            if t and tema:
                lineas.append(f"   - \"{t}\" => {tema}")
        lineas.append("")
    lineas += [
        "Devuelve SOLO un JSON object con la clave \"resultados\": un array en el "
        "MISMO orden y con la MISMA cantidad de elementos que los comentarios. "
        "Cada elemento debe ser: {\"categoria\": \"<clave>\", \"tono\": "
        "\"literal|sarcastico\", \"postura\": \"apoyo|critica|neutral\", "
        "\"confianza\": 0.0}. NO devuelvas markdown ni texto adicional.",
        "",
        "Comentarios:",
    ]
    return "\n".join(lineas) + "\n"


def _estimar_tokens(texto):
    """Estimacion barata de tokens (~4 caracteres por token)."""
    return max(1, len(texto) // 4)


def _purgar_historial(ahora):
    global _historial_tokens
    _historial_tokens = [(t, n) for (t, n) in _historial_tokens if ahora - t < 60.0]


def _esperar_presupuesto(tokens_estimados):
    """Pausa hasta que `tokens_estimados` quepa en el presupuesto del minuto."""
    if TPM_BUDGET <= 0:
        return
    ahora = time.time()
    _purgar_historial(ahora)
    espera_acumulada = 0.0
    while _historial_tokens:
        usados = sum(n for _, n in _historial_tokens)
        if usados + tokens_estimados <= TPM_BUDGET:
            break
        ts_viejo = _historial_tokens[0][0]
        dormir = max(0.0, 60.0 - (ahora - ts_viejo)) + 0.3
        if dormir <= 0:
            break
        logger.info("Pacing IA: esperando %.1fs para no superar %d TPM", dormir, TPM_BUDGET)
        time.sleep(min(dormir, 20.0))
        espera_acumulada += dormir
        if espera_acumulada > 180:
            break
        ahora = time.time()
        _purgar_historial(ahora)


def _registrar_tokens(tokens):
    _historial_tokens.append((time.time(), tokens))


def _es_rate_limit(msg):
    m = msg.lower()
    return "429" in msg or "rate_limit" in m or "rate limit" in m


def _segundos_espera_429(msg):
    encontrado = re.search("try again in ([0-9.]+)", msg)
    if encontrado:
        try:
            return float(encontrado.group(1)) + 0.8
        except (TypeError, ValueError):
            pass
    return ESPERA_429_DEFAULT


def _parsear_respuesta(raw, textos):
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        arr = parsed
    else:
        arr = parsed.get("resultados", [])

    salida = []
    for idx in range(len(textos)):
        entry = arr[idx] if idx < len(arr) and isinstance(arr[idx], dict) else {}
        cat = _remapear(entry.get("categoria", "no_aplica"))
        if cat not in CATEGORIAS_VALIDAS:
            cat = "no_aplica"
        tono = entry.get("tono", "literal")
        if tono not in TONOS_VALIDOS:
            tono = "literal"
        postura = _normalizar_postura(entry.get("postura"))
        try:
            conf = float(entry.get("confianza", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        conf = max(0.0, min(1.0, conf))
        salida.append({
            "categoria": cat,
            "tono": tono,
            "postura": postura,
            "confianza": round(conf, 3),
            "motor": "llm",
        })
    return salida


def _fallback_keyword(textos):
    """Clasificacion de respaldo por palabras clave (sin IA).

    get_main_topic devuelve claves historicas; se remapean a las englobantes.
    Sin IA no se infiere polaridad: la postura queda 'neutral'.
    """
    try:
        from src.analyzer.topic_detection import get_main_topic
    except Exception:
        get_main_topic = None
    salida = []
    for t in textos:
        cat = ""
        if get_main_topic is not None:
            try:
                cat = get_main_topic(t) or ""
            except Exception:
                cat = ""
        cat = _remapear(cat)
        if cat not in CATEGORIAS_VALIDAS:
            cat = "no_aplica"
        salida.append({
            "categoria": cat,
            "tono": "literal",
            "postura": "neutral",
            "confianza": 0.3,
            "motor": "reglas",
        })
    return salida


def _verifier_model():
    """Modelo verificador de la cascada (None si no esta configurado)."""
    try:
        from dashboard.llm_groq import VERIFIER_MODEL
        return VERIFIER_MODEL or None
    except Exception:
        return None


def _clasificar_bloque_llm(textos, model=None, ejemplos=None):
    """Clasifica un bloque de comentarios con el modelo de texto.

    `model` permite usar el verificador de la cascada en vez del primario.
    `ejemplos` (few-shot) se inyectan al prompt para guiar el criterio.
    Respeta el pacing y reintenta ante 429 antes de propagar el error.
    """
    from dashboard.llm_groq import chat_texto

    items = []
    for idx, t in enumerate(textos):
        limpio = " ".join(str(t or "").split())[:MAX_CHARS_COMENTARIO]
        items.append(f"{idx}. {limpio}")
    prompt = _construir_prompt_base(ejemplos) + "\n".join(items)

    tokens_est = _estimar_tokens(prompt) + len(textos) * 15

    ultimo_error = None
    for intento in range(MAX_REINTENTOS_429 + 1):
        _esperar_presupuesto(tokens_est)
        try:
            raw = chat_texto(prompt, json=True, temperature=0, max_tokens=4096, model=model)
            _registrar_tokens(tokens_est)
            return _parsear_respuesta(raw, textos)
        except Exception as e:
            _registrar_tokens(tokens_est)
            msg = str(e)
            if _es_rate_limit(msg) and intento < MAX_REINTENTOS_429:
                espera = _segundos_espera_429(msg)
                logger.warning(
                    "Rate limit IA (intento %d/%d); esperando %.1fs antes de reintentar",
                    intento + 1, MAX_REINTENTOS_429, espera,
                )
                time.sleep(espera)
                ultimo_error = e
                continue
            raise
    if ultimo_error:
        raise ultimo_error
    return _fallback_keyword(textos)


def clasificar_temas_lote(textos, lote=None, ejemplos=None):
    """Clasifica una lista de comentarios devolviendo un dict por comentario.

    Cada dict: {categoria, tono, postura, confianza, motor, ...}, alineado 1 a 1
    con `textos`. Usa el modelo (con cascada si esta activa) si el proveedor
    esta disponible; si no, cae a palabras clave. `ejemplos` (few-shot) afina la
    sugerencia con el criterio aprobado por el usuario.
    """
    if not textos:
        return []

    try:
        from dashboard.llm_groq import groq_disponible
        usar_llm = groq_disponible()
    except Exception:
        usar_llm = False

    if not usar_llm:
        return _fallback_keyword(textos)

    tam = lote or LOTE_LLM
    if tam < 1:
        tam = 40

    verif = _verifier_model() if CASCADA_ACTIVA else None

    # Referencia al global (monkeypatchable en tests). Si hay ejemplos, se
    # enlazan via partial para no alterar la firma que espera la cascada.
    base_fn = _clasificar_bloque_llm
    clasif = functools.partial(base_fn, ejemplos=ejemplos) if ejemplos else base_fn

    salida = []
    for i in range(0, len(textos), tam):
        bloque = textos[i:i + tam]
        try:
            if verif:
                from dashboard.llm_cascade import clasificar_con_cascada
                salida.extend(clasificar_con_cascada(
                    bloque, clasif, verificador_model=verif,
                ))
            else:
                salida.extend(clasif(bloque))
        except Exception as e:
            logger.warning(
                "Clasificacion IA fallo en bloque %d (%d items): %r; usando reglas",
                i, len(bloque), e,
            )
            salida.extend(_fallback_keyword(bloque))

    # Por seguridad, alinear longitud exacta con la entrada.
    if len(salida) < len(textos):
        salida.extend(_fallback_keyword(textos[len(salida):]))
    elif len(salida) > len(textos):
        salida = salida[:len(textos)]

    return salida
