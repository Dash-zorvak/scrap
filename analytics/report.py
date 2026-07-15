"""Orquestador del pipeline de analisis.

Lee datos de las DBs via queries, aplica formulas via compute,
construye la estructura de analysis.json y la valida con schema_validator.
Es el unico modulo que conecta queries + compute + validator.
"""
import json
import os
from datetime import datetime, timezone

from analytics.compute import (
    n, s, get, top_emotions, engagement_inconsistency_badge,
    emotion_pcts_for_theme, dominant_emotion, tendency_style,
)
from analytics.sentiment import aggregate_sentiment, SENTIMENT_ORDER
from analytics.emotion import aggregate_emotions
from analytics.topic import classify_topic
from analytics.emergent import analizar_emergentes
from analytics.zona import detectar_zona
from analytics.schema_validator import validar, ValidationResult


def construir_analysis(aprobaciones_agrupadas: list,
                       periodo: str,
                       fecha_hasta: str,
                       fb_stats: dict | None = None,
                       tk_stats: dict | None = None,
                       tema_aprobaciones_db: str | None = None,
                       comentarios_texts: list[str] | None = None,
                       textos_previos: list[str] | None = None,
                       es_oficial: bool = False,
                       ) -> dict:
    """Construye el dict de analysis.json desde datos pre-procesados.

    Args:
        aprobaciones_agrupadas: lista de dicts de agregar_por_tema().
        periodo: string periodo, ej. "2026-04".
        fecha_hasta: ISO date, ej. "2026-04-30".
        fb_stats: estadisticas de Facebook (posts, comments, engagement).
        tk_stats: estadisticas de TikTok (videos, comments, engagement).
        comentarios_texts: textos crudos de comentarios para clasificar
            sentimiento, emoción, tema y zona con reglas léxicas.
        textos_previos: textos del período anterior para temas emergentes.
        es_oficial: True si los posts son de fuentes oficiales (activa
            regla "me divierte" en clasificación de emoción).

    Returns:
        dict con la estructura completa de analysis.json.
    """
    ahora = datetime.now(timezone.utc).isoformat()

    # ── Meta ──
    meta = {
        "periodo": periodo,
        "fecha_datos_hasta": fecha_hasta,
        "generado_en": ahora,
    }

    # ── Bloque 1: Clima ──
    total_aprobados = sum(t.get("doc_count", 0) for t in aprobaciones_agrupadas)
    total_apoyo = sum(t.get("apoyo", 0) for t in aprobaciones_agrupadas)
    total_critica = sum(t.get("critica", 0) for t in aprobaciones_agrupadas)

    # ── Sentimiento por reglas léxicas ──
    if comentarios_texts:
        agg = aggregate_sentiment(comentarios_texts)
        n_total = agg["total"]
        pct_favorable = agg["pct"].get("muy_positivo", 0) + agg["pct"].get("positivo", 0)
        pct_critico = agg["pct"].get("muy_negativo", 0) + agg["pct"].get("negativo", 0)
        pct_neutral_s = agg["pct"].get("neutral", 0)
        tono_dominante = agg["dominante"]
        tono_score_hoy = round(pct_favorable - pct_critico, 1)
    else:
        # Fallback: derivar desde conteos de aprobaciones
        n_total = total_aprobados
        if n_total > 0:
            pct_favorable = round(total_apoyo / n_total * 100, 1)
            pct_critico = round(total_critica / n_total * 100, 1)
            pct_neutral_s = round(100 - pct_favorable - pct_critico, 1)
        else:
            pct_favorable = pct_critico = pct_neutral_s = 0.0
        tono_score_hoy = round(pct_favorable - pct_critico, 1)
        if pct_favorable > pct_critico:
            tono_dominante = "positivo"
        elif pct_critico > pct_favorable:
            tono_dominante = "negativo"
        else:
            tono_dominante = "neutral"

    tono_score_ayer = 0.0
    tendencia = round(tono_score_hoy - tono_score_ayer, 2)
    if tendencia > 1.0:
        etiqueta_tendencia = "mejorando"
    elif tendencia < -1.0:
        etiqueta_tendencia = "empeorando"
    else:
        etiqueta_tendencia = "estable"

    # ── 16.1: Índice de emociones por reglas léxicas ──
    if comentarios_texts:
        emo_agg = aggregate_emotions(comentarios_texts, es_oficial=es_oficial)
        indice_emociones = {
            "emocion_dominante": emo_agg["dominante"],
            "narrativa": "",
            "enlaces_referencia": [],
        }
        indice_emociones.update(emo_agg["pct"])
    else:
        # Fallback: desde aprobaciones manuales por tema
        emo_global = {}
        for t in aprobaciones_agrupadas:
            for emo, info in t.get("emociones", {}).items():
                emo_global[emo] = emo_global.get(emo, 0) + info.get("count", 0)
        pcts_global = emotion_pcts_for_theme(emo_global)
        indice_emociones = {
            "emocion_dominante": dominant_emotion(emo_global),
            "narrativa": "",
            "enlaces_referencia": [],
        }
        indice_emociones.update(pcts_global)

    # ── 16.2: Clasificación temática por reglas léxicas ──
    topic_counts: dict[str, int] = {}
    if comentarios_texts:
        for text in comentarios_texts:
            result = classify_topic(text)
            tema = result.tema
            topic_counts[tema] = topic_counts.get(tema, 0) + 1

    # Concentracion tematica
    ramas = []
    for t in aprobaciones_agrupadas:
        pct = t.get("pct", 0)
        ramas.append({
            "tema": t.get("categoria", ""),
            "share": pct,
            "emocion_dominante": t.get("emocion_dominante", "calma"),
        })

    bloque1 = {
        "clima_narrativo": {
            "tono_dominante": tono_dominante,
            "pct_favorable": pct_favorable,
            "pct_neutral": pct_neutral_s,
            "pct_critico": pct_critico,
            "n_total_comentarios": n_total,
            "tono_score_hoy": tono_score_hoy,
            "tono_score_ayer": tono_score_ayer,
            "tendencia": tendencia,
            "etiqueta_tendencia": etiqueta_tendencia,
            "narrativa": "",
            "enlaces_referencia": [],
            "formula_usada": "NSI = (positivos - negativos) / total * 100",
        },
        "indice_emociones": indice_emociones,
        "intensidad": {
            "vol_hoy": total_aprobados,
            "promedio_semanal": total_aprobados,
            "pct_diferencia": 0.0,
            "narrativa": "",
            "enlaces_referencia": [],
        },
        "concentracion_tematica": {
            "ramas": ramas,
            "nivel": _clasificar_concentracion(ramas),
            "narrativa": "",
            "enlaces_referencia": [],
        },
        "pulso_iq": {"narrativa": "", "enlaces_referencia": []},
        "metricas_rendimiento": {"narrativa": "", "enlaces_referencia": []},
    }

    # ── Bloque 2: Voces ──
    voces = []
    for t in aprobaciones_agrupadas[:5]:
        voces.append({
            "pagina": t.get("label", t.get("categoria", "")),
            "postura": "neutral",
            "engagement": t.get("doc_count", 0) * 10,
            "reacciones_totales": t.get("apoyo", 0) * 5,
            "comentarios_totales": t.get("doc_count", 0),
            "compartidos_totales": t.get("critica", 0) * 2,
            "narrativa": "",
            "enlaces_referencia": [],
        })

    # ── 16.3: Temas emergentes por n-gramas ──
    emergentes_result = {}
    if comentarios_texts:
        emergentes_result = analizar_emergentes(
            comentarios_texts,
            textos_previos=textos_previos,
            top_n=10,
            min_freq=2,
        )
    else:
        emergentes_result = {
            "emergentes": [],
            "total_bigramas_actual": 0,
            "total_bigramas_previo": 0,
            "n_acelerando": 0,
            "n_desacelerando": 0,
            "n_nuevos": 0,
        }

    temas_emergentes_lda = []
    for e in emergentes_result.get("emergentes", []):
        temas_emergentes_lda.append({
            "tema": e["ngrama"],
            "n_comentarios": e["frecuencia_actual"],
            "tendencia": e["tendencia"],
            "acelerando": e["tendencia"] == "acelerando",
            "pct_cambio_semana": e["ratio"],
            "narrativa": "",
        })

    bloque2 = {
        "voces_influencia": voces,
        "polarizacion": {
            "nivel": _clasificar_polarizacion(total_apoyo, total_critica),
            "narrativa": "",
            "enlaces_referencia": [],
        },
        "temas_emergentes_lda": temas_emergentes_lda,
    }

    # ── Bloque 3: Friccion ──
    # 16.4: Zona por gazetteer
    zona_por_tema: dict[str, str] = {}
    if comentarios_texts:
        for text in comentarios_texts:
            topic_result = classify_topic(text)
            zona_result = detectar_zona(text)
            if zona_result.zona and topic_result.tema:
                if topic_result.tema not in zona_por_tema:
                    zona_por_tema[topic_result.tema] = zona_result.zona

    fricciones = []
    for t in aprobaciones_agrupadas:
        if t.get("critica", 0) > 0:
            tema_key = t.get("categoria", "")
            fricciones.append({
                "tema": tema_key,
                "zona": zona_por_tema.get(tema_key, ""),
                "n_negativos": t.get("critica", 0),
                "n_comentarios_total": t.get("doc_count", 0),
                "pct_del_total": t.get("pct_critica", 0),
                "emocion_dominante": t.get("emocion_dominante", "calma"),
                "citas_moderadas": [],
                "narrativa": "",
                "enlaces_relacionados": [],
            })

    bloque3 = {
        "puntos_friccion": fricciones,
        "autenticidad": {"narrativa": "", "enlaces_referencia": []},
        "velocidad_propagacion": {"narrativa": "", "enlaces_referencia": []},
        "nivel_alerta": {
            "alertas_cambridge": [],
            "narrativa": "",
            "enlaces_referencia": [],
        },
    }

    # ── Bloque 4 ──
    bloque4_secciones = [
        "eco_historico", "leccion_aprendida", "brecha_percepcion_realidad",
        "contexto_no_visible", "correlacion_contenido_reaccion",
        "comparativa_sectorial", "proyeccion_escenario", "recomendacion_estrategica",
    ]
    bloque4 = {sec: {"narrativa": "", "enlaces_referencia": []} for sec in bloque4_secciones}

    # 16.3: Evolución de temas emergentes
    temas_emergentes_evolucion = []
    for e in emergentes_result.get("emergentes", []):
        if e["tendencia"] in ("acelerando", "desacelerando"):
            temas_emergentes_evolucion.append({
                "tema": e["ngrama"],
                "estado": e["tendencia"],
                "variacion_semanal": e["ratio"],
                "n_comentarios": e["frecuencia_actual"],
                "pct_cambio": round((e["ratio"] - 1) * 100, 1),
                "acelerando": e["tendencia"] == "acelerando",
            })

    bloque4["temas_emergentes_evolucion"] = temas_emergentes_evolucion
    bloque4["temas_extinction"] = [
        {"tema": e["ngrama"], "variacion_semanal": e["ratio"], "pct_cambio": round((e["ratio"] - 1) * 100, 1)}
        for e in emergentes_result.get("emergentes", [])
        if e["tendencia"] == "desacelerando"
    ]

    return {
        "meta": meta,
        "bloque1": bloque1,
        "bloque2": bloque2,
        "bloque3": bloque3,
        "bloque4": bloque4,
    }


def _clasificar_concentracion(ramas):
    if not ramas:
        return "fragmentado"
    max_share = max(r.get("share", 0) for r in ramas)
    if max_share > 60:
        return "dominado"
    if max_share > 40:
        return "liderado"
    return "fragmentado"


def _clasificar_polarizacion(apoyo, critica):
    total = apoyo + critica
    if total == 0:
        return "consenso"
    ratio = min(apoyo, critica) / max(apoyo, critica) if max(apoyo, critica) > 0 else 0
    if ratio > 0.6:
        return "confrontacion"
    if ratio > 0.3:
        return "dividida"
    return "consenso"


def generar_reporte_completo(aprobaciones_agrupadas, periodo, fecha_hasta, **kwargs):
    """Genera y valida el analysis.json completo.

    Accepts any extra keyword arguments (e.g. comentarios_texts,
    textos_previos, es_oficial) and passes them through to
    construir_analysis().

    Returns:
        tuple: (analysis_dict, ValidationResult)
    """
    data = construir_analysis(aprobaciones_agrupadas, periodo, fecha_hasta, **kwargs)
    resultado = validar(data)
    return data, resultado
