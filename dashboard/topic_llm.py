"""Clasificacion de temas ciudadanos con IA (contexto + tono).

Capa mas relevante del robustecimiento de temas: en lugar de buscar palabras
clave literales (que confunde dichos como "panchito el rio estaba" con medio
ambiente), un modelo de lenguaje lee cada comentario completo y decide:

  - "categoria": el asunto ciudadano (mismas claves que TEMA_LABELS /
    topic_detection), o "no_aplica" si el comentario no habla de ningun asunto
    municipal (dicho, broma, saludo, sarcasmo sin tema, spam).
  - "tono": "literal" o "sarcastico".
  - "confianza": 0.0 a 1.0.

Si Groq no esta disponible o el modelo falla, se cae con elegancia al detector
por palabras clave (get_main_topic), de modo que el dashboard nunca se queda sin
clasificacion. El modelo se configura via GROQ_TEXT_MODEL (hoy Llama 3.3 70B) y
es compatible con OpenAI, por lo que migrar a NVIDIA NIM solo requiere cambiar
GROQ_BASE_URL / GROQ_API_KEY / GROQ_TEXT_MODEL.

Control de ritmo (pacing): el plan gratis de Groq limita los tokens por minuto
(TPM). Para no chocar con el 429 y caer al respaldo por reglas, se espacian las
llamadas para mantenerse bajo TOPIC_LLM_TPM y, si aun asi llega un 429, se espera
el tiempo que indique el proveedor y se reintenta.
"""

import json
import logging
import os
import re
import time

logger = logging.getLogger("topic_llm")

# Claves validas: deben coincidir con TOPIC_KEYWORDS (topic_detection) y
# TEMA_LABELS (dash_inteligencia). "no_aplica" es nueva: marca comentarios que
# no hablan de ningun asunto municipal.
CATEGORIAS_VALIDAS = {
    "obras_publicas", "seguridad", "servicios_publicos", "empleo", "salud",
    "educacion", "movilidad", "corrupcion", "medio_ambiente", "transparencia",
    "cultura", "deportes", "apoyo_generico", "no_aplica",
}

TONOS_VALIDOS = {"literal", "sarcastico"}

# Cuantos comentarios se mandan por llamada al modelo (controla costo/latencia).
# Lotes mas grandes = menos llamadas = menos veces se repite el prompt fijo.
LOTE_LLM = int(os.environ.get("TOPIC_LLM_LOTE", "40"))

# Cuantos caracteres por comentario se envian (evita prompts gigantes).
MAX_CHARS_COMENTARIO = int(os.environ.get("TOPIC_LLM_MAX_CHARS", "300"))

# Presupuesto de tokens por minuto. Groq free tier = 12000 TPM para
# llama-3.3-70b-versatile; dejamos margen. 0 desactiva el pacing.
TPM_BUDGET = int(os.environ.get("TOPIC_LLM_TPM", "10000"))

# Reintentos ante un 429 antes de caer al respaldo por reglas.
MAX_REINTENTOS_429 = int(os.environ.get("TOPIC_LLM_REINTENTOS", "5"))

# Espera por defecto (segundos) si el 429 no dice cuanto esperar.
ESPERA_429_DEFAULT = float(os.environ.get("TOPIC_LLM_ESPERA_429", "16"))

# Historial de consumo para el pacing: list[(timestamp, tokens_estimados)].
_historial_tokens = []


_PROMPT = (
    "Eres un analista que clasifica comentarios ciudadanos de las redes "
    "sociales de una alcaldia de El Salvador (Santa Ana). Para CADA comentario "
    "decide tres cosas.\n\n"
    "1) \"categoria\": el asunto ciudadano del que habla. Usa UNA de estas "
    "claves EXACTAS:\n"
    "   - obras_publicas: calles, baches, parques, puentes, construccion.\n"
    "   - seguridad: delincuencia, robos, policia, pandillas, violencia.\n"
    "   - servicios_publicos: agua, luz, basura, alcantarillado, tramites.\n"
    "   - empleo: trabajo, empleo, negocios, economia.\n"
    "   - salud: hospitales, clinicas, medicinas, enfermedades.\n"
    "   - educacion: escuelas, maestros, becas, estudiantes.\n"
    "   - movilidad: transporte, trafico, buses, semaforos, accidentes.\n"
    "   - corrupcion: corrupcion, fraude, mal gobierno, abuso de poder.\n"
    "   - medio_ambiente: contaminacion, rios, arboles, reforestacion.\n"
    "   - transparencia: presupuesto, gastos, rendicion de cuentas.\n"
    "   - cultura: eventos, fiestas, festivales, tradiciones.\n"
    "   - deportes: futbol, canchas, torneos, deportistas.\n"
    "   - apoyo_generico: felicitaciones, bendiciones, 'buen trabajo' SIN un "
    "tema concreto.\n"
    "   - no_aplica: NO habla de ningun asunto municipal. Usalo para dichos, "
    "refranes, bromas, sarcasmo sin tema, saludos, etiquetar a alguien, spam o "
    "texto sin sentido.\n\n"
    "MUY IMPORTANTE - dichos y sarcasmo salvadorenos: muchos comentarios usan "
    "frases hechas que NO hablan del tema literal. Por ejemplo 'panchito el rio "
    "estaba' es un dicho burlon (alguien se siente aludido sin que lo nombren); "
    "NO habla de un rio ni de medio ambiente, asi que su categoria es "
    "'no_aplica'. No te dejes enganar por una sola palabra: clasifica por el "
    "SENTIDO real del comentario completo.\n\n"
    "2) \"tono\": \"literal\" si dice lo que parece; \"sarcastico\" si es "
    "ironico o burla (por ejemplo 'excelente trabajo, lo que faltaba').\n\n"
    "3) \"confianza\": numero de 0.0 a 1.0 de que tan seguro estas.\n\n"
    "Devuelve SOLO un JSON object con la clave \"resultados\": un array en el "
    "MISMO orden y con la MISMA cantidad de elementos que los comentarios. Cada "
    "elemento debe ser: {\"categoria\": \"<clave>\", \"tono\": "
    "\"literal|sarcastico\", \"confianza\": 0.0}. NO devuelvas markdown ni "
    "texto adicional.\n\n"
    "Comentarios:\n"
)


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
        cat = entry.get("categoria", "no_aplica")
        if cat not in CATEGORIAS_VALIDAS:
            cat = "no_aplica"
        tono = entry.get("tono", "literal")
        if tono not in TONOS_VALIDOS:
            tono = "literal"
        try:
            conf = float(entry.get("confianza", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        conf = max(0.0, min(1.0, conf))
        salida.append({
            "categoria": cat,
            "tono": tono,
            "confianza": round(conf, 3),
            "motor": "llm",
        })
    return salida


def _fallback_keyword(textos):
    """Clasificacion de respaldo por palabras clave (sin IA)."""
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
        if cat not in CATEGORIAS_VALIDAS:
            cat = "no_aplica"
        salida.append({
            "categoria": cat,
            "tono": "literal",
            "confianza": 0.3,
            "motor": "reglas",
        })
    return salida


def _clasificar_bloque_llm(textos):
    """Clasifica un bloque de comentarios con el modelo de texto Groq.

    Respeta el limite de tokens por minuto (pacing) y, si aun asi recibe un 429,
    espera lo que indique el proveedor y reintenta antes de propagar el error.
    """
    from dashboard.llm_groq import chat_texto

    items = []
    for idx, t in enumerate(textos):
        limpio = " ".join(str(t or "").split())[:MAX_CHARS_COMENTARIO]
        items.append(f"{idx}. {limpio}")
    prompt = _PROMPT + "\n".join(items)

    tokens_est = _estimar_tokens(prompt) + len(textos) * 15

    ultimo_error = None
    for intento in range(MAX_REINTENTOS_429 + 1):
        _esperar_presupuesto(tokens_est)
        try:
            raw = chat_texto(prompt, json=True, temperature=0, max_tokens=4096)
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


def clasificar_temas_lote(textos, lote=None):
    """Clasifica una lista de comentarios devolviendo un dict por comentario.

    Cada dict: {"categoria", "tono", "confianza", "motor"}. La lista de salida
    queda alineada 1 a 1 con `textos`. Usa el modelo de lenguaje si Groq esta
    disponible; si no, cae a palabras clave.
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

    salida = []
    for i in range(0, len(textos), tam):
        bloque = textos[i:i + tam]
        try:
            salida.extend(_clasificar_bloque_llm(bloque))
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
