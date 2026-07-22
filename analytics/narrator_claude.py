"""Cliente para la API de Anthropic (Claude) — redaccion de narrativas.

Este modulo es independiente de dashboard/llm_groq.py. Usa exclusivamente
Claude (Anthropic) y NO tiene cascada de respaldo silencioso: si Claude
falla, se propaga el error porque el usuario exige un proveedor especifico
y auditable.

Configuracion por entorno:
    ANTHROPIC_API_KEY  (obligatoria)
    CLAUDE_MODEL       (default: "claude-sonnet-4-5")
    CLAUDE_MAX_TOKENS  (default: 1024)
    CLAUDE_TEMPERATURE (default: 0.3, narrativa sobria y determinista)

Uso:
    from analytics.narrator_claude import redactar_narrativa
    texto = redactar_narrativa(system_prompt, contexto_dict)
"""
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

_API_KEY_ENV = "ANTHROPIC_API_KEY"
_MODEL_ENV = "CLAUDE_MODEL"
_MAX_TOKENS_ENV = "CLAUDE_MAX_TOKENS"
_TEMPERATURE_ENV = "CLAUDE_TEMPERATURE"

_DEFAULT_MODEL = "claude-sonnet-4-5"
_DEFAULT_MAX_TOKENS = 1024
_DEFAULT_TEMPERATURE = 0.3
_MAX_REINTENTOS_ENV = "CLAUDE_MAX_REINTENTOS"
_DEFAULT_MAX_REINTENTOS = 3


def _get_config():
    """Lee configuracion de entorno. Lanza ValueError si falta la API key."""
    api_key = os.environ.get(_API_KEY_ENV, "").strip()
    if not api_key:
        raise ValueError(
            f"Variable de entorno {_API_KEY_ENV} no definida. "
            f"Configura tu API key de Anthropic antes de usar el narrador."
        )
    return {
        "api_key": api_key,
        "model": os.environ.get(_MODEL_ENV, _DEFAULT_MODEL).strip(),
        "max_tokens": int(os.environ.get(_MAX_TOKENS_ENV, _DEFAULT_MAX_TOKENS)),
        "temperature": float(os.environ.get(_TEMPERATURE_ENV, _DEFAULT_TEMPERATURE)),
        "max_reintentos": int(os.environ.get(_MAX_REINTENTOS_ENV, _DEFAULT_MAX_REINTENTOS)),
    }


def _retry_with_backoff(func, *args, max_retries=None, **kwargs):
    """Reintenta con backoff solo ante rate-limit/timeout.

    Mismo patron que dashboard/llm_groq.py::_retry_with_backoff pero sin
    cascada de modelos: si Claude falla, se propaga el error.
    """
    if max_retries is None:
        max_retries = _DEFAULT_MAX_REINTENTOS
    last_exc = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            err_str = str(e).lower()
            es_rate = "429" in err_str or "rate" in err_str or "quota" in err_str
            es_timeout = (
                "timed out" in err_str
                or "timeout" in err_str
                or "connection" in err_str
                or e.__class__.__name__ in ("APITimeoutError", "APIConnectionError",
                                             "overloaded_error")
            )
            if (es_rate or es_timeout) and attempt < max_retries - 1:
                dormir = 2 ** (attempt + 1) if es_rate else (attempt + 1) * 2
                logger.info(
                    "Backoff Claude intento %d/%d: durmiendo %.1fs (%s)",
                    attempt + 1, max_retries, dormir,
                    "rate limit" if es_rate else "timeout/connection",
                )
                time.sleep(dormir)
                continue
            raise
    raise last_exc


def redactar_narrativa(system_prompt: str, contexto: dict,
                        max_tokens: int | None = None,
                        section_code: str = "") -> str:
    """Redacta una narrativa usando Claude (Anthropic API).

    Args:
        system_prompt: instrucciones fijas (reglas del ANALYST_GUIDE.md).
        contexto: dict con las cifras ya calculadas y evidencia resuelta.
            Claude NO calcula; solo redacta usando estos datos.
        max_tokens: limite de tokens de respuesta (override de config).
        section_code: codigo de seccion para logging (ej. "b1.clima_narrativo").

    Returns:
        str con la narrativa redactada.

    Raises:
        ValueError: si ANTHROPIC_API_KEY no esta definida.
        Exception: si la llamada a la API falla tras reintentos.
    """
    config = _get_config()

    if Anthropic is None:
        raise ImportError(
            "Paquete 'anthropic' no instalado. "
            "Instala con: pip install anthropic"
        )

    client = Anthropic(api_key=config["api_key"])

    user_message = (
        "Contexto de la seccion (JSON). "
        "Usa SOLO estos datos para redactar la narrativa. "
        "No inventes ni calcules ningun numero adicional.\n\n"
        f"```json\n{json.dumps(contexto, ensure_ascii=False, indent=2)}\n```"
    )

    effective_max_tokens = max_tokens or config["max_tokens"]

    def _llamar():
        response = client.messages.create(
            model=config["model"],
            max_tokens=effective_max_tokens,
            temperature=config["temperature"],
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    logger.info("Claude narrar %s (modelo=%s)", section_code, config["model"])
    resultado = _retry_with_backoff(_llamar, max_retries=config["max_reintentos"])
    logger.info("Claude narrar %s completado (%d chars)", section_code, len(resultado))
    return resultado.strip()
