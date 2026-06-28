"""Narrativa ejecutiva del memo (Bloque IV).

Construye textos en el lenguaje del alcalde que responden, en cada estación,
las preguntas concretas que el usuario final necesita (qué ocurre, por qué y
qué hacer). Reutiliza el cliente de texto ya configurado por el entorno
(dashboard.llm_groq). El usuario NUNCA ve cómo se generó el análisis: si la
generación no está disponible, se devuelve un mensaje neutro, sin mencionar
ninguna tecnología.
"""

import json
import logging
import re

try:
    from dashboard.llm_groq import chat_texto, groq_disponible, VERIFIER_MODEL
except Exception:  # pragma: no cover - entorno sin cliente configurado
    chat_texto = None
    VERIFIER_MODEL = None

    def groq_disponible():
        return False


_FALLBACK = (
    "Síntesis no disponible por el momento. Revía los indicadores de los "
    "bloques anteriores para esta conclusión."
)

_REGLAS = (
    " REGLAS DE SALIDA OBLIGATORIAS: "
    "(1) Escribe en español claro y directo para un alcalde sin formación "
    "técnica: frases cortas, sin jerga ni fórmulas. Si usas un término técnico, "
    "explícalo en pocas palabras. "
    "(2) Nunca menciones ni insinúes cómo se generó este texto, ni uses palabras "
    "como 'IA', 'inteligencia artificial', 'modelo', 'algoritmo' o 'análisis "
    "automático'. El lector solo ve la conclusión. "
    "(3) PROHIBIDO hablar de 'reelección', 'campaña', 'voto', 'candidato' o "
    "estrategia electoral: esto es análisis de gestión y percepción ciudadana. "
    "(4) Cada afirmación se apoya en una cifra concreta de los datos (porcentaje, "
    "conteo, interacciones). Nada de generalidades sin un número detrás. "
    "(5) Cuando exista el dato, nombra el tema o la zona concreta. NUNCA inventes "
    "cifras, temas ni hechos que no estén en los datos; si falta evidencia, dilo. "
    "(6) El 'índice de enojo' es la fracción de reacciones que son de enojo "
    "(0.004 = 0.4% de las reacciones). Traddcelo siempre a lenguaje simple. "
    "(7) Responde en 2 a 4 frases, sin viñetas ni encabezados."
)

_PROMPTS = {
    "eco_historico": (
        "Eres el asesor político del alcalde de Santa Ana. Explica si la situación "
        "actual ya se vivió antes según los datos (un patrón de enojo, de apoyo o "
        "un tema que reaparece) y cómo evolucionó entonces. Responde qué está "
        "ocurriendo, por qué y qué debería tener presente el alcalde. Si no hay un "
        "precedente claro en los datos, dilo sin inventarlo."
    ),
    "leccion": (
        "Eres el asesor político del alcalde de Santa Ana. Da la lección del "
        "período respondiendo de forma EXPLÍCITA: qué temas funcionaron (los que "
        "tienen más comentarios favorables) y conviene repetir; qué temas generan "
        "rechazo y por qué; qué debería reforzar el alcalde. Si los datos sugieren "
        "'margen de mejora', explica en qué exactamente. Traduce el índice de enojo "
        "a lenguaje simple. Cierra con qué debería hacer el alcalde."
    ),
    "brecha": (
        "Eres el asesor político del alcalde de Santa Ana. Señala 'lo que no se ve "
        "a simple vista': un dato que contradice la lectura superficial (por "
        "ejemplo, apoyo alto pero concentrado en un solo tema, calma aparente con "
        "un foco de enojo, o un promedio neutro que esconde dos posturas opuestas). "
        "Di qué parece a primera vista, qué muestran realmente las cifras y qué "
        "implica para el alcalde. Usa solo los datos disponibles."
    ),
    "contexto": (
        "Eres el asesor político del alcalde de Santa Ana. Explica qué factores "
        "fuera de las redes podrían estar detrás del sentimiento detectado (temas "
        "dominantes, zonas con más enojo, picos de actividad), usando SOLO las "
        "señales presentes en los datos. Di qué ocurre, por qué podría estar "
        "pasando y qué conviene vigilar. No inventes noticias ni fechas."
    ),
    "correlacion": (
        "Eres el asesor político del alcalde de Santa Ana. Explica qué tipo de "
        "publicaciones conectó mejor con la ciudadanía y cuál generó rechazo. "
        "Responde: qué publicación o tema generó mejor respuesta y por qué; cuál "
        "generó rechazo; qué tenían en común; y qué conviene repetir. Usa cifras "
        "claras (por ejemplo, 'de X publicaciones, Y conectaron bien'); nunca dejes "
        "un número suelto sin explicar qué representa."
    ),
    "proyeccion": (
        "Eres el asesor político del alcalde de Santa Ana. Proyecta el escenario de "
        "las próximas 24 a 48 horas si la tendencia de interacción y sentimiento se "
        "mantiene. Di hacia dónde va la conversación, qué señal concreta vigilar y "
        "qué debería preparar el alcalde. Aclara que es una estimación por tendencia, "
        "no una certeza."
    ),
    "recomendacion": (
        "Eres el asesor político del alcalde de Santa Ana. Entrega UNA recomendación "
        "de gestión y comunicación priorizada por los datos. Responde de forma "
        "EXPLÍCITA: cuál es la principal fricción; qué problema concreto genera "
        "rechazo; dónde o en qué tema ocurre; qué comentarios lo provocan; qué "
        "evidencia lo respalda (con la cifra); y qué solución concreta debería "
        "aplicar el alcalde primero. Sé accionable, no genérico ni ambiguo."
    ),
}

_PROHIBIDAS = [
    "análisis ia", "analisis ia", "generado por ia", "inteligencia artificial",
    "ia detect", "como ia", "modelo de lenguaje", "por la ia", "la ia ",
]


def _limpiar(texto):
    if not texto:
        return ""
    t = str(texto).strip()
    for frag in _PROHIBIDAS:
        t = re.sub(re.escape(frag), "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def generar_narrativa(tipo: str, contexto: dict) -> str:
    """Devuelve una conclusión ejecutiva para la estación `tipo`.

    Tipos: eco_historico, leccion, brecha, contexto, correlacion, proyeccion,
    recomendacion. Si la generación no está disponible, devuelve un mensaje
    neutro (sin mencionar ninguna tecnología).
    """
    if chat_texto is None or not groq_disponible():
        return _FALLBACK
    base = _PROMPTS.get(tipo, _PROMPTS["recomendacion"]) + _REGLAS
    ctx_str = json.dumps(contexto, ensure_ascii=False, default=str)[:3500]
    prompt = f"{base}\n\nDATOS DEL PERÍODO (JSON):\n{ctx_str}"
    modelos = [None]
    if VERIFIER_MODEL:
        modelos.append(VERIFIER_MODEL)
    for modelo in modelos:
        try:
            salida = chat_texto(prompt, max_tokens=600, temperature=0.5, json=False, model=modelo)
            salida = _limpiar(salida)
            if salida:
                return salida
        except Exception as e:  # pragma: no cover
            logging.warning("generar_narrativa(%s) falló: %r", tipo, e)
            continue
    return _FALLBACK
