"""Capa 4 — Honestidad: traduce el resumen de calidad de la clasificación de temas.

Toma el dict ``resumen`` que produce ``cargar_temas_latentes_detallado`` y lo
convierte en una lectura honesta y en lenguaje llano de qué tan confiable es la
clasificación de temas: cuántos comentarios se clasificaron con confianza,
cuántos no hablaban de ningún asunto municipal (``no_aplica``) y cuántos
quedaron marcados como dudosos o con posible ironía.

Es un módulo puro (sin Streamlit ni base de datos) para que la lógica sea
verificable en CI. No emite juicios: solo describe la calidad de los datos con
cifras.
"""

from __future__ import annotations


def _pct(n: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(n / total * 100, 1)


def resumen_honestidad(resumen: dict | None) -> dict | None:
    """Convierte el ``resumen`` de calidad en métricas honestas y legibles.

    Espera las claves que entrega ``cargar_temas_latentes_detallado``:
    ``total``, ``clasificados``, ``no_aplica``, ``dudosos``, ``sarcasticos``,
    ``por_reglas`` y ``umbral_dudoso``.

    Devuelve ``None`` si no hay comentarios analizados (no hay nada que mostrar
    honestamente).

    Notas de honestidad:
      - ``con_confianza`` = clasificados cuya confianza supera el umbral, es
        decir ``clasificados - dudosos``. El sarcasmo se reporta aparte porque
        es otra dimensión de calidad (un comentario irónico puede tener un tema
        claro).
      - Todos los conteos se acotan para no producir porcentajes imposibles si
        el ``resumen`` viniera inconsistente.
    """
    resumen = resumen or {}

    def _int(clave: str) -> int:
        try:
            return int(resumen.get(clave, 0) or 0)
        except (TypeError, ValueError):
            return 0

    total = _int("total")
    if total <= 0:
        return None

    clasificados = max(0, min(_int("clasificados"), total))
    no_aplica = max(0, min(_int("no_aplica"), total))
    dudosos = max(0, min(_int("dudosos"), clasificados))
    sarcasticos = max(0, min(_int("sarcasticos"), clasificados))
    por_reglas = max(0, min(_int("por_reglas"), total))
    try:
        umbral = float(resumen.get("umbral_dudoso", 0.55) or 0.55)
    except (TypeError, ValueError):
        umbral = 0.55

    con_confianza = max(0, clasificados - dudosos)
    pct_con_confianza = _pct(con_confianza, total)

    if pct_con_confianza >= 60:
        nivel = "alta"
    elif pct_con_confianza >= 35:
        nivel = "media"
    else:
        nivel = "baja"

    # Lectura en lenguaje llano ("con peras y manzanas"), solo describe cifras.
    partes = [
        f"De los {total:,} comentarios analizados, {con_confianza:,} "
        f"({pct_con_confianza:.0f}%) se clasificaron en un asunto municipal "
        f"con buena confianza."
    ]
    if no_aplica:
        partes.append(
            f"{no_aplica:,} ({_pct(no_aplica, total):.0f}%) no hablaban de "
            f"ningún tema municipal (saludos, bromas o etiquetas a otras personas)."
        )
    detalle = []
    if dudosos:
        detalle.append(f"{dudosos:,} dudosos")
    if sarcasticos:
        detalle.append(f"{sarcasticos:,} con posible ironía")
    if detalle:
        partes.append(
            f"{' y '.join(detalle)} quedaron marcados para revisión y no se "
            f"toman como base firme."
        )
    if por_reglas:
        partes.append(
            f"{por_reglas:,} se asignaron por palabras clave, sin IA contextual."
        )
    lectura = " ".join(partes)

    return {
        "total": total,
        "clasificados": clasificados,
        "pct_clasificados": _pct(clasificados, total),
        "con_confianza": con_confianza,
        "pct_con_confianza": pct_con_confianza,
        "no_aplica": no_aplica,
        "pct_no_aplica": _pct(no_aplica, total),
        "dudosos": dudosos,
        "pct_dudosos": _pct(dudosos, total),
        "sarcasticos": sarcasticos,
        "pct_sarcasticos": _pct(sarcasticos, total),
        "por_reglas": por_reglas,
        "pct_por_reglas": _pct(por_reglas, total),
        "umbral_dudoso": umbral,
        "nivel_confiabilidad": nivel,
        "lectura": lectura,
    }
