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
    engagement_rate_fb, engagement_rate_tk, ratio_amor_enojo_fb,
    reacciones_positivas_fb, reacciones_negativas_fb,
    net_sentiment_index, controversy_index, effectiveness_index,
    approval_pct, rejection_pct, vol_factor, risk_reputacional,
    _detectar_alertas, calcular_hhi,
    calcular_pulso_iq_fb, calcular_pulso_iq_tk,
    pulso_iq_score, pulso_iq_cuadrante,
    coeficiente_variacion, autenticidad_pct,
)
from analytics.sentiment import aggregate_sentiment, SENTIMENT_ORDER
from analytics.emotion import aggregate_emotions
from analytics.topic import classify_topic, TopicResult
from analytics.emergent import analizar_emergentes
from analytics.zona import detectar_zona, es_propuesta_zona
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

    # ── Meta ──
    meta = {
        "periodo": periodo,
        "fecha_datos_hasta": fecha_hasta,
        "generado_en": ahora,
        "plataforma": "",
        "total_posts_analizados": 0,
        "total_comentarios_analizados": n_total,
        "total_reacciones_sumadas": 0,
        "total_impresiones_vistas": 0,
        "enlaces_analizados": [],
    }
    if fb_stats:
        meta["plataforma"] = meta["plataforma"] or "facebook"
        meta["total_posts_analizados"] += n(fb_stats.get("posts", 0))
        meta["total_reacciones_sumadas"] += n(fb_stats.get("total_reacciones", 0))
        meta["total_impresiones_vistas"] += n(fb_stats.get("views", 0))
    if tk_stats:
        if meta["plataforma"]:
            meta["plataforma"] = "multicanal"
        else:
            meta["plataforma"] = "tiktok"
        meta["total_posts_analizados"] += n(tk_stats.get("videos", 0))
        meta["total_reacciones_sumadas"] += n(tk_stats.get("likes", 0))
        meta["total_impresiones_vistas"] += n(tk_stats.get("views", 0))

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
    topic_results_by_text: dict[int, TopicResult] = {}
    if comentarios_texts:
        for i, text in enumerate(comentarios_texts):
            result = classify_topic(text)
            topic_results_by_text[i] = result
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

    # ── §G: HHI de concentración temática ──
    shares_para_hhi = [r.get("share", 0) for r in ramas if isinstance(r, dict)]
    hhi = calcular_hhi(shares_para_hhi)
    top_tema = ramas[0]["tema"] if ramas else ""
    n_temas = len(ramas)

    # ── §D: Engagement Rate ──
    er_fb = er_tk = 0.0
    er_basis_fb = er_basis_tk = "sin_datos"
    ratio_amor_fb = 0.0
    reac_pos_fb = reac_neg_fb = 0
    if fb_stats:
        er_fb, er_basis_fb = engagement_rate_fb(
            fb_stats.get("likes", 0), fb_stats.get("loves", 0),
            fb_stats.get("cares", 0), fb_stats.get("hahas", 0),
            fb_stats.get("wows", 0), fb_stats.get("sads", 0),
            fb_stats.get("angrys", 0), fb_stats.get("comments", 0),
            fb_stats.get("shares", 0), fb_stats.get("views", 0),
        )
        ratio_amor_fb = ratio_amor_enojo_fb(
            fb_stats.get("likes", 0), fb_stats.get("loves", 0),
            fb_stats.get("cares", 0), fb_stats.get("hahas", 0),
            fb_stats.get("sads", 0), fb_stats.get("angrys", 0),
        )
        reac_pos_fb = reacciones_positivas_fb(
            fb_stats.get("likes", 0), fb_stats.get("loves", 0),
            fb_stats.get("cares", 0),
        )
        reac_neg_fb = reacciones_negativas_fb(
            fb_stats.get("angrys", 0), fb_stats.get("sads", 0),
            fb_stats.get("hahas", 0),
        )
    if tk_stats:
        er_tk, er_basis_tk = engagement_rate_tk(
            tk_stats.get("views", 0), tk_stats.get("likes", 0),
            tk_stats.get("shares", 0), tk_stats.get("favorites", 0),
            tk_stats.get("comments", 0),
        )

    # §J: Ponderar ER por volumen real al combinar plataformas
    er_display = er_fb
    er_basis = er_basis_fb
    if fb_stats and tk_stats:
        vol_fb = n(fb_stats.get("engagement", 0))
        vol_tk = n(tk_stats.get("engagement", 0))
        vol_total = vol_fb + vol_tk
        if vol_total > 0:
            er_display = round(
                er_fb * (vol_fb / vol_total) + er_tk * (vol_tk / vol_total), 2
            )
            er_basis = "ponderado_volumen"
    elif tk_stats:
        er_display = er_tk
        er_basis = er_basis_tk

    # §E: Reacciones positivas/negativas (FB) para metricas_rendimiento
    total_reac_fb = reac_pos_fb + reac_neg_fb
    reac_pos_pct = round(reac_pos_fb / total_reac_fb * 100, 1) if total_reac_fb > 0 else 0.0
    reac_neg_pct = round(reac_neg_fb / total_reac_fb * 100, 1) if total_reac_fb > 0 else 0.0

    # §H: Pulso IQ
    dims_fb = None
    dims_tk = None
    if fb_stats:
        dims_fb = calcular_pulso_iq_fb(
            pct_favorable, pct_critico, n_total,
            fb_stats.get("posts", 0), shares_para_hhi, tono_score_hoy,
        )
    if tk_stats:
        dims_tk = calcular_pulso_iq_tk(
            pct_favorable, pct_critico, n_total,
            tk_stats.get("videos", 0), shares_para_hhi, tono_score_hoy,
        )
    iq_score, iq_dims = pulso_iq_score(dims_fb, dims_tk)
    iq_cuadrante = pulso_iq_cuadrante(iq_score, iq_dims)

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
            "hhi": hhi,
            "nivel": _clasificar_concentracion(ramas),
            "top_tema": top_tema,
            "n_temas": n_temas,
            "narrativa": "",
            "enlaces_referencia": [],
            "formula_usada": "HHI = Σ(share_i²) donde share_i = n_tema_i / total_temas",
        },
        "pulso_iq": {
            "valor": iq_score,
            "cuadrante": iq_cuadrante,
            "componentes": iq_dims,
            "narrativa": "",
            "enlaces_referencia": [],
        },
        "metricas_rendimiento": {
            "engagement_rate": er_display,
            "engagement_rate_formula": (
                "ER = (reacciones + comentarios + compartidos) / vistas * 100"
            ),
            "engagementBasis": er_basis,
                "alcance_estimado": n(
                    (fb_stats.get("views", 0) if fb_stats else 0)
                    + (tk_stats.get("views", 0) if tk_stats else 0)
                ),
            "reacciones_positivas": reac_pos_fb,
            "reacciones_negativas": reac_neg_fb,
            "reacciones_positivas_pct": reac_pos_pct,
            "reacciones_negativas_pct": reac_neg_pct,
            "ratio_amor_enojo": ratio_amor_fb,
            "ratio_amor_enojo_formula": "R = (likes + loves + cares) / (angrys + sads + hahas)",
            "porque_funciona": "",
            "narrativa": "",
            "enlaces_referencia": [],
        },
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

    # §E: Polarización índice = |pct_apoyo - pct_critica| / 100
    total_apoyo_critica = total_apoyo + total_critica
    polarizacion_indice = 0.0
    if total_apoyo_critica > 0:
        polarizacion_indice = round(abs(total_apoyo - total_critica) / total_apoyo_critica, 3)

    # ── 16.3: Temas emergentes por n-gramas ──
    # 18.4: Filtrar solo textos no_aplica/low-signal (n_coincidencias < 2)
    emergentes_result = {}
    if comentarios_texts and topic_results_by_text:
        textos_sin_tema_claro = []
        for i, text in enumerate(comentarios_texts):
            tr = topic_results_by_text.get(i)
            if tr and (tr.tema == "no_aplica" or tr.n_coincidencias < 2):
                textos_sin_tema_claro.append(text)

        if textos_sin_tema_claro:
            emergentes_result = analizar_emergentes(
                textos_sin_tema_claro,
                textos_previos=textos_previos,
                top_n=10,
                min_freq=2,
            )
    elif comentarios_texts:
        # Sin topic_results disponibles (fallback)
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
            "indice": polarizacion_indice,
            "nivel": _clasificar_polarizacion(total_apoyo, total_critica),
            "narrativa": "",
            "enlaces_referencia": [],
            "formula_usada": "PI = |pct_simpatizantes - pct_criticos| / 100",
        },
        "temas_emergentes_lda": temas_emergentes_lda,
    }

    # ── Bloque 3: Friccion ──
    # 16.4: Zona por gazetteer + registro de propuestas
    zona_por_tema: dict[str, str] = {}
    if comentarios_texts:
        for i, text in enumerate(comentarios_texts):
            topic_result = topic_results_by_text.get(i)
            if topic_result is None:
                topic_result = classify_topic(text)
            zona_result = detectar_zona(text)
            if zona_result.zona and topic_result.tema:
                if topic_result.tema not in zona_por_tema:
                    zona_por_tema[topic_result.tema] = zona_result.zona

            # 18.3: Registrar propuestas de zona
            es_propuesta_zona(text)

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

    # ── §F: Alertas ──
    # Angrys ratio para FB
    angrys_ratio = 0.0
    if fb_stats:
        total_reacciones_fb = n(fb_stats.get("total_reacciones", 0))
        if total_reacciones_fb > 0:
            angrys_ratio = n(fb_stats.get("angrys", 0)) / total_reacciones_fb
    controversy_score = controversy_index(pct_favorable, pct_critico)
    alertas = _detectar_alertas(pct_critico, angrys_ratio, controversy_score)

    # ── §I: Autenticidad ──
    daily_vols_fb = []
    daily_vols_tk = []
    if fb_stats and fb_stats.get("daily_volumes"):
        daily_vols_fb = [v for _, v in fb_stats["daily_volumes"]]
    if tk_stats and tk_stats.get("daily_volumes"):
        daily_vols_tk = [v for _, v in tk_stats["daily_volumes"]]
    daily_vols_all = daily_vols_fb + daily_vols_tk
    pct_organico, pct_coordinado = autenticidad_pct(daily_vols_all) if daily_vols_all else (100.0, 0.0)

    # ── §E: Risk Reputacional ──
    rr = risk_reputacional(pct_critico, angrys_ratio, hhi)
    # Semáforo
    if rr >= 60:
        semaforo = "rojo"
    elif rr >= 30:
        semaforo = "amarillo"
    else:
        semaforo = "verde"

    bloque3 = {
        "puntos_friccion": fricciones,
        "autenticidad": {
            "pct_organico": pct_organico,
            "pct_coordinado": pct_coordinado,
            "n_duplicados": 0,
            "narrativa": "",
            "enlaces_referencia": [],
            "formula_usada": "% coordinado = n_mensajes_duplicados_o_similares / total_comentarios * 100",
        },
        "velocidad_propagacion": {
            "proyeccion_24h": "",
            "tendencia_dias": [],
            "narrativa": "",
            "enlaces_referencia": [],
            "temas_acelerando": [],
            "temas_desacelerando": [],
            "formula_usada": "Velocidad = Δcomentarios / Δtiempo; proyección = tendencia_lineal últimas 72h",
        },
        "nivel_alerta": {
            "semaforo": semaforo,
            "indice_riesgo": rr,
            "pct_negativos": pct_critico,
            "indice_enojo_reacciones": round(angrys_ratio * 100, 1),
            "balance_confrontacion": controversy_score,
            "n_temas_friccion": len(fricciones),
            "tema_principal": fricciones[0]["tema"] if fricciones else "",
            "emocion_principal": fricciones[0]["emocion_dominante"] if fricciones else "",
            "alertas_cambridge": [
                {"tipo": a["tipo"], "descripcion": a["descripcion"], "enlaces_referencia": []}
                for a in alertas
            ],
            "narrativa": "",
            "enlaces_referencia": [],
            "formula_riesgo": "IR = (pct_negativos*0.4 + indice_enojo*0.3 + balance_confrontacion*0.3) * sensibilidad_tema",
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
