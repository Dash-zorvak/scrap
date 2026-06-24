"""Bloque IV — Memoria e Inteligencia Aplicada (funciones puras y testeables).

Evolución temática semana a semana (emergentes / en auge / en declive / en extinción /
estables) y reframe narrativo de la comparativa sectorial (conversación propia vs
fuentes externas). Sin Streamlit ni acceso a BD: reciben estructuras simples y
devuelven dicts/listas, de modo que la lógica es verificable con tests.
"""

from __future__ import annotations


def clasificar_evolucion_temas(conteo_actual, conteo_previo,
                               umbral_auge=0.4, umbral_declive=-0.4):
    """Clasifica temas comparando su frecuencia de la semana actual vs la previa.

    Args:
        conteo_actual: dict {tema: n} de la semana más reciente.
        conteo_previo: dict {tema: n} de la semana anterior.
        umbral_auge: alza relativa mínima para 'en auge' (0.4 = +40%).
        umbral_declive: caída relativa máxima para 'en declive' (-0.4 = -40%).

    Returns:
        dict con listas ordenadas de items {tema, n_actual, n_previo, cambio_pct}:
          - emergentes: nuevos (no existían la semana previa).
          - en_auge: presentes en ambas, crecimiento >= umbral_auge.
          - en_declive: presentes en ambas, caída <= umbral_declive.
          - en_extincion: desaparecieron (n_actual == 0, n_previo > 0).
          - estables: el resto presentes en ambas semanas.
    """
    conteo_actual = conteo_actual or {}
    conteo_previo = conteo_previo or {}
    emergentes, en_auge, en_declive, en_extincion, estables = [], [], [], [], []
    temas = set(conteo_actual) | set(conteo_previo)
    for tema in temas:
        n_act = int(conteo_actual.get(tema, 0) or 0)
        n_prev = int(conteo_previo.get(tema, 0) or 0)
        if n_act <= 0 and n_prev <= 0:
            continue
        if n_prev == 0:
            cambio = 1.0
        elif n_act == 0:
            cambio = -1.0
        else:
            cambio = (n_act - n_prev) / n_prev
        item = {
            "tema": tema,
            "n_actual": n_act,
            "n_previo": n_prev,
            "cambio_pct": round(cambio * 100, 1),
        }
        if n_prev == 0 and n_act > 0:
            emergentes.append(item)
        elif n_act == 0 and n_prev > 0:
            en_extincion.append(item)
        elif cambio >= umbral_auge:
            en_auge.append(item)
        elif cambio <= umbral_declive:
            en_declive.append(item)
        else:
            estables.append(item)

    emergentes.sort(key=lambda x: x["n_actual"], reverse=True)
    en_auge.sort(key=lambda x: x["cambio_pct"], reverse=True)
    en_declive.sort(key=lambda x: x["cambio_pct"])
    en_extincion.sort(key=lambda x: x["n_previo"], reverse=True)
    estables.sort(key=lambda x: x["n_actual"], reverse=True)

    return {
        "emergentes": emergentes,
        "en_auge": en_auge,
        "en_declive": en_declive,
        "en_extincion": en_extincion,
        "estables": estables,
    }


def _tono(score, pos=0.1, neg=-0.1):
    if score > pos:
        return "favorable"
    if score < neg:
        return "crítico"
    return "mixto"


def comparar_sectorial(score_interno, score_externo, n_fuentes, n_menciones):
    """Reframe narrativo: tono de la conversación propia vs el de fuentes externas.

    Args:
        score_interno: índice de sentimiento (-1..1) de las páginas propias.
        score_externo: índice de sentimiento (-1..1) de las fuentes externas.
        n_fuentes: número de fuentes externas distintas.
        n_menciones: número total de menciones externas.

    Returns:
        dict con tonos, brecha y una lectura en lenguaje llano, o None si no hay
        datos externos suficientes (n_menciones<=0 o n_fuentes<=0).
    """
    if not n_menciones or not n_fuentes or n_menciones <= 0 or n_fuentes <= 0:
        return None
    score_interno = float(score_interno)
    score_externo = float(score_externo)
    brecha = round(score_externo - score_interno, 3)
    if brecha <= -0.15:
        lectura = (
            "El tono en fuentes externas es más negativo que en las páginas propias: "
            "la crítica más dura vive afuera, no en la conversación que administras."
        )
    elif brecha >= 0.15:
        lectura = (
            "El tono en fuentes externas es más positivo que en las páginas propias: "
            "la conversación más tensa ocurre dentro de tus propios canales."
        )
    else:
        lectura = (
            "El tono externo y el de las páginas propias se mueven en línea: "
            "no hay una brecha marcada entre ambos."
        )
    return {
        "n_fuentes": int(n_fuentes),
        "n_menciones": int(n_menciones),
        "score_interno": round(score_interno, 3),
        "score_externo": round(score_externo, 3),
        "brecha": brecha,
        "tono_interno": _tono(score_interno),
        "tono_externo": _tono(score_externo),
        "lectura": lectura,
    }
