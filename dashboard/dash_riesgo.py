"""Bloque III - Riesgo y autenticidad: cálculos puros (sin Streamlit ni IO).

Provee la lógica de los cuatro índices del bloque:
  - calcular_autenticidad: orgánico vs coordinado/sospechoso (mensajes repetidos).
  - calcular_nivel_alerta: necesidad de respuesta institucional (semáforo).
  - calcular_propagacion_24_48: proyección de la conversación a 24-48h.
  - agrupar_fricciones: 2-3 temas con más reacción negativa, con cita.
"""

import re
from collections import Counter

import pandas as pd


def _norm(texto):
    t = str(texto).lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    return t.strip()


def calcular_autenticidad(mensajes, min_repeticiones=2, min_len=4):
    """Proporción orgánico vs sospechoso a partir de la repetición de mensajes.

    Un comentario es \"sospechoso\" si su texto normalizado aparece repetido
    (>= min_repeticiones) -> patrón de copia-pega / coordinación. El resto se
    considera orgánico. Devuelve proporciones, grupos repetidos y ejemplos.
    None si no hay datos utilizables.
    """
    if mensajes is None:
        return None
    norm = [_norm(m) for m in list(mensajes)]
    norm = [m for m in norm if len(m) >= min_len]
    n_total = len(norm)
    if n_total == 0:
        return None
    cont = Counter(norm)
    n_sosp = sum(c for c in cont.values() if c >= min_repeticiones)
    n_org = n_total - n_sosp
    pct_sosp = n_sosp / n_total * 100
    pct_org = 100 - pct_sosp
    grupos = sorted(
        ((c, m) for m, c in cont.items() if c >= min_repeticiones),
        reverse=True,
    )
    ejemplos = [{"texto": m, "veces": int(c)} for c, m in grupos[:3]]
    if pct_sosp < 10:
        nivel = "organico"
        estado = "Conversación mayoritariamente orgánica"
    elif pct_sosp < 30:
        nivel = "mixto"
        estado = "Señales mixtas: hay algo de repetición"
    else:
        nivel = "coordinado"
        estado = "Posible coordinación: alta repetición de mensajes"
    return {
        "n_total": int(n_total), "n_sospechoso": int(n_sosp), "n_organico": int(n_org),
        "pct_sospechoso": round(pct_sosp, 1), "pct_organico": round(pct_org, 1),
        "n_grupos": len(grupos), "ejemplos": ejemplos,
        "nivel": nivel, "estado": estado,
    }


def calcular_nivel_alerta(pct_negativo=0.0, indice_enojo=0.0,
                          balance_confrontacion=None, n_fricciones=0):
    """Necesidad de respuesta institucional, como semáforo verde/amarillo/rojo.

    Combina señales de riesgo: % de comentarios negativos, enojo en reacciones,
    nivel de confrontación (balance de polarización) y cantidad de temas de
    fricción. Devuelve un índice 0-100 y el color/acción recomendada.
    """
    neg = max(0.0, float(pct_negativo or 0))
    eno = max(0.0, float(indice_enojo or 0)) * 100
    conf = (float(balance_confrontacion) * 100) if balance_confrontacion is not None else 0.0
    riesgo = 0.45 * neg + 0.35 * eno + 0.20 * conf
    riesgo = min(100.0, riesgo + min(int(n_fricciones or 0), 3) * 3)
    if riesgo < 20:
        color, nivel = "verde", "bajo"
        titular = "Sin necesidad de respuesta institucional"
        accion = "Mantener monitoreo de rutina."
    elif riesgo < 45:
        color, nivel = "amarillo", "medio"
        titular = "Atención: preparar respuesta preventiva"
        accion = "Monitorear de cerca y tener mensajes listos por si escala."
    else:
        color, nivel = "rojo", "alto"
        titular = "Requiere respuesta institucional activa"
        accion = "Definir vocería y responder los temas que generan rechazo."
    return {
        "riesgo": round(riesgo, 1), "color": color, "nivel": nivel,
        "titular": titular, "accion": accion,
    }


def calcular_propagacion_24_48(df, col_fecha="created_time",
                               col_eng="engagement_total", n_ventana=7):
    """Proyección de interacción a 24h y 48h por tendencia lineal diaria.

    Agrega la interacción por día y ajusta una recta (mínimos cuadrados) sobre
    los últimos n_ventana días para proyectar el día siguiente (+24h) y el
    subsiguiente (+48h). Requiere al menos 3 días. None si no hay datos.
    """
    if df is None or len(df) == 0:
        return None
    if col_fecha not in df.columns or col_eng not in df.columns:
        return None
    d = df[[col_fecha, col_eng]].copy()
    d[col_fecha] = pd.to_datetime(d[col_fecha], errors="coerce")
    d[col_eng] = pd.to_numeric(d[col_eng], errors="coerce")
    d = d.dropna(subset=[col_fecha, col_eng])
    if d.empty:
        return None
    diario = d.groupby(d[col_fecha].dt.date)[col_eng].sum().sort_index()
    if len(diario) < 3:
        return None
    serie = diario.tail(n_ventana)
    y = [float(v) for v in serie.values]
    n = len(y)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(y) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    slope = (sum((xs[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / denom) if denom else 0.0
    intercept = mean_y - slope * mean_x
    hoy = y[-1]
    proy_24 = max(0.0, intercept + slope * n)
    proy_48 = max(0.0, intercept + slope * (n + 1))
    base = hoy if hoy > 0 else (mean_y if mean_y > 0 else 1.0)
    pct_24 = (proy_24 - hoy) / base * 100
    pct_48 = (proy_48 - hoy) / base * 100
    if slope > 0 and pct_24 > 10:
        tendencia, flecha = "acelerando", "\u25b2"
    elif slope < 0 and pct_24 < -10:
        tendencia, flecha = "desacelerando", "\u25bc"
    else:
        tendencia, flecha = "estable", "\u2192"
    return {
        "hoy": round(hoy, 0), "proy_24h": round(proy_24, 0), "proy_48h": round(proy_48, 0),
        "pct_24h": round(pct_24, 1), "pct_48h": round(pct_48, 1),
        "slope": round(slope, 1), "tendencia": tendencia, "flecha": flecha,
        "n_dias": int(len(diario)),
    }


def agrupar_fricciones(df, top_n=3, umbral_score=-0.1):
    """Agrupa los comentarios negativos por tema y devuelve los 2-3 principales.

    Considera negativo un comentario si su etiqueta sentiment es negativo/
    muy_negativo O si su sentiment_score < umbral_score. Agrupa por
    topic_category y devuelve, por tema, el conteo y una cita representativa
    (el comentario más negativo). Lista vacía si no hay fricción.
    """
    if df is None or len(df) == 0:
        return []
    d = df.copy()
    if "sentiment_score" in d.columns:
        d["_score"] = pd.to_numeric(d["sentiment_score"], errors="coerce")
    else:
        d["_score"] = pd.Series([pd.NA] * len(d), index=d.index)
    if "sentiment" in d.columns:
        sent = d["sentiment"].astype(str).str.lower()
    else:
        sent = pd.Series([""] * len(d), index=d.index)
    es_neg = sent.isin(["negativo", "muy_negativo"]) | (d["_score"] < umbral_score)
    d = d[es_neg.fillna(False)]
    if d.empty:
        return []
    if "topic_category" in d.columns:
        d["_tema"] = d["topic_category"].fillna("General").replace("", "General")
    else:
        d["_tema"] = "General"
    msg_col = "message" if "message" in d.columns else None
    grupos = []
    for tema, g in d.groupby("_tema"):
        n = len(g)
        if g["_score"].notna().any():
            peor = g.sort_values("_score").iloc[0]
            score_prom = float(g["_score"].mean())
        else:
            peor = g.iloc[0]
            score_prom = 0.0
        cita = str(peor[msg_col]) if msg_col else ""
        grupos.append({
            "tema": str(tema), "n": int(n),
            "score_promedio": round(score_prom, 2), "cita": cita[:160],
        })
    grupos.sort(key=lambda x: x["n"], reverse=True)
    return grupos[:top_n]
