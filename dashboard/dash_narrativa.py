"""Narrativa ejecutiva del memo (Bloque IV).

Construye textos en lenguaje claro y profesional que responden, en cada
estación, las preguntas concretas que el usuario final necesita (qué ocurre,
por qué y qué conviene hacer). Reutiliza el cliente de texto ya configurado por
el entorno (dashboard.llm_groq). El usuario NUNCA ve cómo se generó el análisis:
si la generación no está disponible, se devuelve un mensaje neutro, sin
mencionar ninguna tecnología.
"""

import hashlib
import json
import logging
import os
import re
import threading
import time

try:
    from dashboard.llm_groq import chat_texto, groq_disponible, VERIFIER_MODEL
except Exception:  # pragma: no cover - entorno sin cliente configurado
    chat_texto = None
    VERIFIER_MODEL = None

    def groq_disponible():
        return False


_FALLBACK = (
    "Síntesis no disponible por el momento. Revisa los indicadores de los "
    "bloques anteriores para esta conclusión."
)

_REGLAS = (
    " REGLAS DE SALIDA OBLIGATORIAS: "
    "(1) Escribe en español claro y directo para un lector sin formación "
    "técnica: frases cortas, sin jerga ni fórmulas. Si usas un término técnico, "
    "explícalo en pocas palabras. "
    "(2) Nunca menciones ni insinües cómo se generó este texto, ni uses palabras "
    "como 'IA', 'inteligencia artificial', 'modelo', 'algoritmo' o 'análisis "
    "automático'. El lector solo ve la conclusión. "
    "(3) PROHIBIDO hablar de 'reelección', 'campaña', 'voto', 'candidato' o "
    "estrategia electoral: esto es análisis de gestión y percepción ciudadana. "
    "(4) Cada afirmación se apoya en una cifra concreta de los datos (porcentaje, "
    "conteo, interacciones). Nada de generalidades sin un número detrás. "
    "(5) Cuando exista el dato, nombra el tema o la zona concreta. NUNCA inventes "
    "cifras, temas ni hechos que no estén en los datos; si falta evidencia, dilo. "
    "(6) El 'índice de enojo' es la fracción de las REACCIONES (clics 'Me enoja') "
    "que son de enojo (0.004 = 0.4% de las reacciones); es un eje DISTINTO del "
    "porcentaje de comentarios críticos (texto), con volúmenes muy dispares, así "
    "que NUNCA lo compares ni lo presentes como si midiera lo mismo que la crítica "
    "en los comentarios. Tradúcelo siempre a lenguaje simple. "
    "(7) Responde en 2 a 4 frases, sin viñetas ni encabezados. "
    "(8) Escribe en TERCERA PERSONA, en tono crudo, objetivo y directo. NO te "
    "dirijas a ninguna persona ni uses vocativos ni saludos (NUNCA empieces con "
    "'Alcalde' ni similares) y NO uses lenguaje adulador, cortés ni de cortejo "
    "(nada de felicitar ni suavizar). Arranca SIEMPRE directamente con el "
    "hallazgo o la cifra (por ejemplo: 'El 24.3% de los 382 comentarios fue "
    "favorable, pero el 37.4% fue crítico...'). "
    "(9) Respeta SIEMPRE el signo del saldo (favorables menos críticos): si el "
    "saldo es negativo, NUNCA presentes la situación como positiva ni como 'apoyo "
    "mayoritario'. Si los críticos superan a los favorables, el texto debe reflejar "
    "ese predominio crítico. "
    "(10) Si faltan temas con rechazo, focos o cifras para sostener una conclusión, "
    "dilo de forma explícita ('no hay datos suficientes para atribuir un foco "
    "concreto') y NO inventes un veredicto, una causa ni un tema."
)

_PROMPTS = {
    "eco_historico": (
        "Eres un analista de inteligencia ciudadana de la gestión municipal de "
        "Santa Ana. Explica si la situación actual ya se vivió antes según los "
        "datos (un patrón de enojo, de apoyo o un tema que reaparece) y cómo "
        "evolucionó entonces. Responde qué está ocurriendo, por qué y qué conviene "
        "tener presente para la gestión. Si no hay un precedente claro en los "
        "datos, dilo sin inventarlo."
    ),
    "leccion": (
        "Eres un analista de inteligencia ciudadana de la gestión municipal de "
        "Santa Ana. Da la lección del período respondiendo de forma EXPLÍCITA: qué "
        "temas funcionaron (los que tienen más comentarios favorables) y conviene "
        "repetir; qué temas generan rechazo y por qué; qué conviene reforzar. Si "
        "los datos sugieren 'margen de mejora', explica en qué exactamente. "
        "Traduce el índice de enojo a lenguaje simple. Cierra con qué conviene "
        "hacer."
    ),
    "brecha": (
        "Eres un analista de inteligencia ciudadana de la gestión municipal de "
        "Santa Ana. Señala 'lo que no se ve a simple vista': un dato que "
        "contradice la lectura superficial (por ejemplo, apoyo alto pero "
        "concentrado en un solo tema, calma aparente con un foco de enojo, o un "
        "promedio neutro que esconde dos posturas opuestas). Di qué parece a "
        "primera vista, qué muestran realmente las cifras y qué implica para la "
        "gestión. Usa solo los datos disponibles."
    ),
    "contexto": (
        "Eres un analista de inteligencia ciudadana de la gestión municipal de "
        "Santa Ana. Explica qué factores fuera de las redes podrían estar detrás "
        "del sentimiento detectado (temas dominantes, zonas con más enojo, picos "
        "de actividad), usando SOLO las señales presentes en los datos. Di qué "
        "ocurre, por qué podría estar pasando y qué conviene vigilar. No inventes "
        "noticias ni fechas."
    ),
    "correlacion": (
        "Eres un analista de inteligencia ciudadana de la gestión municipal de "
        "Santa Ana. Explica qué tipo de publicaciones conectó mejor con la "
        "ciudadanía y cuál generó rechazo. Responde: qué publicación o tema generó "
        "mejor respuesta y por qué; cuál generó rechazo; qué tenían en común; y "
        "qué conviene repetir. Usa cifras claras (por ejemplo, 'de X "
        "publicaciones, Y conectaron bien'); nunca dejes un número suelto sin "
        "explicar qué representa."
    ),
    "proyeccion": (
        "Eres un analista de inteligencia ciudadana de la gestión municipal de "
        "Santa Ana. Proyecta el escenario de las próximas 24 a 48 horas si la "
        "tendencia de interacción y sentimiento se mantiene. Di hacia dónde va la "
        "conversación, qué señal concreta vigilar y qué conviene preparar. Aclara "
        "que es una estimación por tendencia, no una certeza."
    ),
    "recomendacion": (
        "Eres un analista de inteligencia ciudadana de la gestión municipal de "
        "Santa Ana. Entrega UNA recomendación de gestión y comunicación priorizada "
        "por los datos. Responde de forma EXPLÍCITA: cuál es la principal fricción; "
        "qué problema concreto genera rechazo; dónde o en qué tema ocurre; qué "
        "comentarios lo provocan; qué evidencia lo respalda (con la cifra); y qué "
        "solución concreta conviene aplicar primero. Sé accionable, no genérico ni "
        "ambiguo."
    ),
}

_PROHIBIDAS = [
    "análisis ia", "analisis ia", "generado por ia", "inteligencia artificial",
    "ia detect", "como ia", "modelo de lenguaje", "por la ia", "la ia ",
]


# ── Caché + espaciado para no saturar el límite de la API ──
# El Memo genera ~8 textos y Streamlit re-ejecuta el script en CADA interacción.
# Sin caché eso redispara todas las llamadas y agota el tier gratis (~40 req/min
# -> error 429). Cacheamos por (tipo + datos del período): los éxitos se reutilizan
# durante _TTL_OK segundos y, tras un fallo, aplicamos un breve _COOLDOWN_FALLO
# para no reintentar en cada recarga. Además espaciamos las llamadas al menos
# _MIN_INTERVALO segundos. No cambia ningún cálculo: solo evita el bombardeo.
_CACHE: dict = {}
_LOCK = threading.Lock()
_ULTIMA = [0.0]
_TTL_OK = float(os.environ.get("NARRATIVA_TTL_OK", "3600"))
_COOLDOWN_FALLO = float(os.environ.get("NARRATIVA_COOLDOWN", "90"))
_MIN_INTERVALO = float(os.environ.get("NARRATIVA_MIN_INTERVALO", "1.6"))


def _es_rate_limit(exc) -> bool:
    s = str(exc).lower()
    return any(x in s for x in ("429", "rate limit", "ratelimit", "too many", "quota"))


def _throttle():
    """Espacia las llamadas al modelo para respetar el límite por minuto."""
    with _LOCK:
        espera = _MIN_INTERVALO - (time.monotonic() - _ULTIMA[0])
        if espera > 0:
            time.sleep(espera)
        _ULTIMA[0] = time.monotonic()


def _clave_cache(tipo, ctx_str):
    return tipo + ":" + hashlib.sha1(ctx_str.encode("utf-8")).hexdigest()


def _limpiar(texto):
    if not texto:
        return ""
    t = str(texto).strip()
    for frag in _PROHIBIDAS:
        t = re.sub(re.escape(frag), "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def _compara_enojo_critico(texto: str) -> bool:
    """Detecta si la misma oración menciona 'enojo'/'enoja' y 'crític'/'critica'.
    
    Tokeniza por oraciones (split por ., !, ?) y usa regex case-insensitive.
    Retorna True si ALGUNA oración contiene AMBOS patrones.
    """
    if not texto:
        return False
    # Split por . ! ? manteniendo el delimitador para reconstruir oraciones
    oraciones = re.split(r'(?<=[.!?])\s+', texto)
    patron_enojo = re.compile(r'\b(enojo|enoja)\b', re.IGNORECASE)
    patron_critico = re.compile(r'\b(crític|critica|crítico|crítica)\b', re.IGNORECASE)
    for oracion in oraciones:
        if patron_enojo.search(oracion) and patron_critico.search(oracion):
            return True
    return False


def generar_narrativa(tipo: str, contexto: dict) -> str:
    """Devuelve una conclusión ejecutiva para la estación `tipo`.

    Tipos: eco_historico, leccion, brecha, contexto, correlacion, proyeccion,
    recomendacion. Cachea el resultado por (tipo + datos del período) para no
    repetir llamadas en cada recarga de Streamlit. Si la generación no está
    disponible, devuelve un mensaje neutro (sin mencionar ninguna tecnología).
    """
    if chat_texto is None or not groq_disponible():
        return _FALLBACK
    base = _PROMPTS.get(tipo, _PROMPTS["recomendacion"]) + _REGLAS
    ctx_str = json.dumps(contexto, ensure_ascii=False, default=str)[:3500]
    clave = _clave_cache(tipo, ctx_str)
    ahora = time.time()
    with _LOCK:
        ent = _CACHE.get(clave)
    if ent:
        texto, es_fallback, ts = ent
        if not es_fallback and (ahora - ts) < _TTL_OK:
            return texto
        if es_fallback and (ahora - ts) < _COOLDOWN_FALLO:
            return texto
    prompt = f"{base}\n\nDATOS DEL PERÍODO (JSON):\n{ctx_str}"
    # Una sola llamada al modelo principal. Solo si el fallo NO es de límite
    # (429) probamos el verificador; ante un 429 reintentar duplicaría la
    # presión sobre la misma cuota y empeoraría el problema.
    for intento in range(2):  # 0 = primer intento, 1 = reintento tras violación
        try:
            _throttle()
            salida_raw, _, _ = chat_texto(prompt, max_tokens=600, temperature=0.5, json=False)
            salida = _limpiar(salida_raw)
            if salida:
                if _compara_enojo_critico(salida):
                    if intento == 0:
                        logging.warning(
                            "generar_narrativa(%s) violó regla enojo/crrojo/crítico, reintentando", tipo
                        )
                        # Añadir advertencia explícita al prompt para el reintento
                        prompt = (
                            prompt
                            + "\n\nADVERTENCIA: tu respuesta anterior comparó el enojo "
                            "de reacciones con el % crítico de comentarios, algo PROHIBIDO "
                            "por la regla 6. Corrige esto."
                        )
                        continue  # reintento con prompt corregido
                    # Segundo intento también viola: caer a fallback
                    logging.warning(
                        "generar_narrativa(%s) reintento violó regla enojo/crítico, usando fallback",
                        tipo,
                    )
                    break
                # Salida válida: cachear y devolver
                with _LOCK:
                    _CACHE[clave] = (salida, False, time.time())
                return salida
        except Exception as e:  # pragma: no cover
            logging.warning("generar_narrativa(%s) falló: %r", tipo, e)
            if not _es_rate_limit(e) and VERIFIER_MODEL and intento == 0:
                try:
                    _throttle()
                    salida_raw, _, _ = chat_texto(
                        prompt, max_tokens=600, temperature=0.5, json=False, model=VERIFIER_MODEL
                    )
                    salida = _limpiar(salida_raw)
                    if salida and not _compara_enojo_critico(salida):
                        with _LOCK:
                            _CACHE[clave] = (salida, False, time.time())
                        return salida
                    if salida and _compara_enojo_critico(salida):
                        logging.warning(
                            "generar_narrativa(%s) verificador violó regla enojo/crítico, usando fallback",
                            tipo,
                        )
                        break
                except Exception as e2:  # pragma: no cover
                    logging.warning(
                        "generar_narrativa(%s) verificador falló: %r", tipo, e2
                    )
            break
    with _LOCK:
        _CACHE[clave] = (_FALLBACK, True, time.time())
    return _FALLBACK
