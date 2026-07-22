"""Orquestador del pipeline de analisis.

Lee datos de las DBs via queries, aplica formulas via compute,
construye la estructura de analysis.json y la valida con schema_validator.
Es el unico modulo que conecta queries + compute + validator.

Bloque 6.1: Wiring de formulas literales §D-I.
"""
import json
import os
from datetime import datetime, timezone

from analytics.compute import (
    n, s, get, top_emotions, engagement_inconsistency_badge,
    emotion_pcts_for_theme, dominant_emotion, tendency_style,
    engagement_rate_fb, engagement_rate_tk, ratio_amor_enojo_fb,
    reacciones_positivas_fb, reacciones_negativas_fb,
    interacciones_fb,
    net_sentiment_reacciones, controversy_reacciones,
    effectiveness_reacciones, approval_pct_reacciones, rejection_pct_reacciones,
    net_sentiment_index, nsi_deviation, vol_factor, risk_reputacional,
    detectar_ici, detectar_sdi, detectar_efi, detectar_tai, detectar_zdi,
    verificar_cooldown, calcular_sensibilidad_tema, calcular_sensibilidad_para_alertas,
    calcular_hhi,
    calcular_pulso_iq_fb, calcular_pulso_iq_tk,
    pulso_iq_score, pulso_iq_cuadrante,
    coeficiente_variacion, autenticidad_pct,
    clamp,
)
from analytics.sentiment import aggregate_sentiment, SENTIMENT_ORDER
from analytics.emotion import aggregate_emotions, classify_emotion
from analytics.topic import classify_topic, TopicResult
from analytics.emergent import analizar_emergentes
from analytics.zona import detectar_zona, es_propuesta_zona
from analytics.schema_validator import validar, ValidationResult


def construir_analysis(aprobaciones_agrupadas: list,
                       periodo: str,
                       fecha_hasta: str,
                       fb_stats: dict | None = None,
                       tk_stats: dict | None = None,
                       externos_stats: dict | None = None,
                       tema_aprobaciones_db: str | None = None,
                       comentarios_texts: list[str] | None = None,
                       comentarios_con_contexto: list[dict] | None = None,
                       textos_previos: list[str] | None = None,
                       es_oficial: bool = False,
                       # Bloque 6.1: historical data
                       fb_monthly_sentiment: list | None = None,
                       fb_per_theme_controversy: list | None = None,
                       fb_posts_with_sentiment: list | None = None,
                       fb_controversial_posts: list | None = None,
                       fb_anger_by_zone: list | None = None,
                       alertas_cooldown_state: dict | None = None,
                       nsi_previo: float | None = None,
                       er_previo: float | None = None,
                       # Bloque 6.2: ICI monthly controversy + sensitivity
                       fb_monthly_controversy: list | None = None,
                       fb_monthly_theme_controversy: list | None = None,
                       # Bloque 6.3: ICI 7-day period controversy
                       fb_period_controversy: tuple | None = None,
                       ) -> dict:
    """Construye el dict de analysis.json desde datos pre-procesados.

    Args:
        aprobaciones_agrupadas: lista de dicts de agregar_por_tema().
        periodo: string periodo, ej. "2026-04".
        fecha_hasta: ISO date, ej. "2026-04-30".
        fb_stats: estadisticas de Facebook (posts, comments, engagement).
        tk_stats: estadisticas de TikTok (videos, comments, engagement).
        externos_stats: estadisticas de Externos (posts, comments, engagement).
        comentarios_texts: textos crudos de comentarios para clasificar
            sentimiento, emoción, tema y zona con reglas léxicas.
        comentarios_con_contexto: lista de dicts con keys "id", "texto",
            "post_id", "plataforma" para preservar trazabilidad
            comentario -> post. Se usa para generar el archivo de
            evidencia (_evidencia_periodo.json) que el paso narrar
            consume para resolver URLs reales. Campo interno no
            incluido en analysis.json; se persiste aparte.
        textos_previos: textos del período anterior para temas emergentes.
        es_oficial: True si los posts son de fuentes oficiales (activa
            regla "me divierte" en clasificación de emoción).
        fb_monthly_sentiment: [(mes, avg_score, n)] para consistencia §H.
        fb_per_theme_controversy: [{tema, controversy, n_posts}] para §E risk.
        fb_posts_with_sentiment: [{created_time, sentiment_score, topic_category, zona}].
        fb_controversial_posts: [{post_id, post_url, ratio, ...}] para alert links.
        fb_anger_by_zone: [{zona, negativos, total, pct_negativos}] para ZDI.
        alertas_cooldown_state: {tipo: last_alert_timestamp_iso} para cooldown §F.
        nsi_previo: NSI del período anterior para SDI.
        er_previo: ER del período anterior para EFI.
        fb_monthly_controversy: [(mes, controversia, n)] para historial ICI.
        fb_monthly_theme_controversy: [{mes, tema, controversy, n_posts}]
            para cv_28d/velocidad en sensibilidad temática de TAI e ICI.
        fb_period_controversy: (controversia, n_posts) resultado de
            get_fb_period_controversy() para ventana de 7 días de ICI.
            Si se provee, se usa como controversia_actual en vez del
            último mes de fb_monthly_controversy.

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
    if externos_stats:
        if meta["plataforma"]:
            meta["plataforma"] = "multicanal"
        else:
            meta["plataforma"] = "externos"
        meta["total_posts_analizados"] += n(externos_stats.get("posts", 0))
        meta["total_reacciones_sumadas"] += n(externos_stats.get("total_reactions", 0))

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

    ramas = []
    for t in aprobaciones_agrupadas:
        pct = t.get("pct", 0)
        ramas.append({
            "tema": t.get("categoria", ""),
            "share": pct,
            "emocion_dominante": t.get("emocion_dominante", "calma"),
        })

    # ── Evidencia: mapear post_id -> tema/emocion para trazabilidad ──
    # Se persiste en _evidencia_periodo.json para que el paso narrar resuelva
    # URLs reales sin volver a tocar las DBs crudas.
    evidencia_por_tema: dict[str, set[str]] = {}
    evidencia_por_emocion: dict[str, set[str]] = {}
    if comentarios_con_contexto and topic_results_by_text:
        for i, ctx in enumerate(comentarios_con_contexto):
            post_id = ctx.get("post_id", "")
            if not post_id:
                continue
            tr = topic_results_by_text.get(i)
            if tr and tr.tema and tr.tema != "no_aplica":
                evidencia_por_tema.setdefault(tr.tema, set()).add(post_id)
        # Clasificar emoción de CADA comentario individualmente para evidencia
        for i, ctx in enumerate(comentarios_con_contexto):
            post_id = ctx.get("post_id", "")
            texto = ctx.get("texto", "")
            if not post_id or not texto:
                continue
            emo_result = classify_emotion(texto, es_oficial=es_oficial)
            if emo_result.emocion and emo_result.emocion != "calma":
                evidencia_por_emocion.setdefault(emo_result.emocion, set()).add(post_id)

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
            n_posts=fb_stats.get("posts", 0),
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
            n_videos=tk_stats.get("videos", 0),
        )

    # §J: Ponderar ER Oficial por volumen real (solo FB+TK, sin Externos)
    er_display = er_fb
    er_basis = er_basis_fb
    vol_fb = n(fb_stats.get("engagement", 0)) if fb_stats else 0
    vol_tk = n(tk_stats.get("engagement", 0)) if tk_stats else 0
    n_plat_oficial = sum(1 for v in (vol_fb, vol_tk) if v > 0)
    if n_plat_oficial >= 2:
        vol_total_oficial = vol_fb + vol_tk
        if vol_total_oficial > 0:
            er_display = round(
                (er_fb * vol_fb + er_tk * vol_tk) / vol_total_oficial, 2
            )
            er_basis = "ponderado_volumen"
    elif tk_stats:
        er_display = er_tk
        er_basis = er_basis_tk

    # §J2: ER Externo (solo datos de Externos, separado del Oficial)
    er_externo = 0.0
    er_ext_basis = "sin_datos"
    if externos_stats:
        from analytics.compute import engagement_rate_externos
        er_externo, er_ext_basis = engagement_rate_externos(
            externos_stats.get("total_reactions", 0),
            externos_stats.get("comments_count", 0),
            n_posts=externos_stats.get("posts", 0),
        )

    # ── §E: Reacciones (FB) ──
    ns_reac = 0.0
    controversy_r = 0.0
    effectiveness_r = 0.0
    approval_r = 0.0
    rejection_r = 0.0
    if fb_stats:
        ns_reac = net_sentiment_reacciones(
            fb_stats.get("likes", 0), fb_stats.get("loves", 0),
            fb_stats.get("cares", 0), fb_stats.get("hahas", 0),
            fb_stats.get("wows", 0), fb_stats.get("sads", 0),
            fb_stats.get("angrys", 0),
        )
        controversy_r = controversy_reacciones(
            fb_stats.get("likes", 0), fb_stats.get("loves", 0),
            fb_stats.get("cares", 0), fb_stats.get("hahas", 0),
            fb_stats.get("wows", 0), fb_stats.get("sads", 0),
            fb_stats.get("angrys", 0),
        )
        effectiveness_r = effectiveness_reacciones(
            fb_stats.get("likes", 0), fb_stats.get("loves", 0),
            fb_stats.get("cares", 0), fb_stats.get("hahas", 0),
            fb_stats.get("wows", 0), fb_stats.get("sads", 0),
            fb_stats.get("angrys", 0),
        )
        approval_r = approval_pct_reacciones(
            fb_stats.get("likes", 0), fb_stats.get("loves", 0),
            fb_stats.get("cares", 0), fb_stats.get("hahas", 0),
            fb_stats.get("wows", 0), fb_stats.get("sads", 0),
            fb_stats.get("angrys", 0),
        )
        rejection_r = rejection_pct_reacciones(
            fb_stats.get("likes", 0), fb_stats.get("loves", 0),
            fb_stats.get("cares", 0), fb_stats.get("hahas", 0),
            fb_stats.get("wows", 0), fb_stats.get("sads", 0),
            fb_stats.get("angrys", 0),
        )

    total_reac_fb = reac_pos_fb + reac_neg_fb
    reac_pos_pct = round(reac_pos_fb / total_reac_fb * 100, 1) if total_reac_fb > 0 else 0.0
    reac_neg_pct = round(reac_neg_fb / total_reac_fb * 100, 1) if total_reac_fb > 0 else 0.0

    # ── §H: Pulso IQ ──
    promedio_so_fb = 0.0
    n_posts_con_tema_fb = 0
    n_posts_con_zona_fb = 0
    if fb_posts_with_sentiment:
        scores = [p.get("sentiment_score", 0) for p in fb_posts_with_sentiment]
        promedio_so_fb = sum(scores) / len(scores) if scores else 0.0
        n_posts_con_tema_fb = sum(1 for p in fb_posts_with_sentiment
                                  if p.get("topic_category", ""))
        n_posts_con_zona_fb = sum(1 for p in fb_posts_with_sentiment
                                   if p.get("zona", ""))

    interacciones_fb_total = 0
    if fb_stats:
        interacciones_fb_total = interacciones_fb(
            fb_stats.get("likes", 0), fb_stats.get("loves", 0),
            fb_stats.get("cares", 0), fb_stats.get("hahas", 0),
            fb_stats.get("wows", 0), fb_stats.get("sads", 0),
            fb_stats.get("angrys", 0), fb_stats.get("comments", 0),
            fb_stats.get("shares", 0),
        )

    promedios_mensuales_fb = []
    if fb_monthly_sentiment:
        promedios_mensuales_fb = [(avg, n_posts) for _, avg, n_posts in fb_monthly_sentiment]

    dims_fb = None
    dims_tk = None
    if fb_stats:
        dims_fb = calcular_pulso_iq_fb(
            promedio_sentiment_order=promedio_so_fb,
            interacciones=interacciones_fb_total,
            vistas=fb_stats.get("views", 0),
            angrys=fb_stats.get("angrys", 0),
            sads=fb_stats.get("sads", 0),
            hahas=fb_stats.get("hahas", 0),
            total_reacciones=fb_stats.get("total_reacciones", 0),
            n_posts_con_tema=n_posts_con_tema_fb,
            n_posts_total=fb_stats.get("posts", 0),
            n_posts_con_zona=n_posts_con_zona_fb,
            total_comentarios=fb_stats.get("comments", 0),
            promedios_mensuales=promedios_mensuales_fb,
        )
    if tk_stats:
        dims_tk = calcular_pulso_iq_tk(
            promedio_sentiment_order=0.0,
            interacciones=n(tk_stats.get("likes", 0)) + n(tk_stats.get("shares", 0))
                         + n(tk_stats.get("favorites", 0)) + n(tk_stats.get("comments", 0)),
            vistas=tk_stats.get("views", 0),
            angrys=0, sads=0, hahas=0,
            total_reacciones=n(tk_stats.get("likes", 0)),
            n_videos_con_tema=0,
            n_videos_total=tk_stats.get("videos", 0),
            n_videos_con_zona=0,
            total_comentarios=tk_stats.get("comments", 0),
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
            "er_externo": er_externo,
            "er_externo_basis": er_ext_basis,
            "alcance_estimado": n(
                (fb_stats.get("views", 0) if fb_stats else 0)
                + (tk_stats.get("views", 0) if tk_stats else 0)
            ),
            "alcance_nota": (
                "Solo incluye FB+TK (vistas). Externos excluido: "
                "la fuente no provee datos de alcance/impresiones."
                if externos_stats and externos_stats.get("posts", 0) > 0
                else ""
            ),
            "reacciones_positivas": reac_pos_fb,
            "reacciones_negativas": reac_neg_fb,
            "reacciones_positivas_pct": reac_pos_pct,
            "reacciones_negativas_pct": reac_neg_pct,
            "ratio_amor_enojo": ratio_amor_fb,
            "ratio_amor_enojo_formula": "R = (likes + loves + cares) / (angrys + sads + hahas)",
            "net_sentiment_reacciones": ns_reac,
            "controversy_reacciones": controversy_r,
            "effectiveness_reacciones": effectiveness_r,
            "aprobacion_pct_reacciones": approval_r,
            "rechazo_pct_reacciones": rejection_r,
            "porque_funciona": "",
            "narrativa": "",
            "enlaces_referencia": [],
        },
    }

    # ── Bloque 2: Voces ──
    # H2: Solo se incluyen voces con datos REALES de engagement.
    # Las voces internas (aprobaciones_agrupadas) fueron eliminadas porque
    # no tenían datos reales de engagement/reacciones/compartidos — los
    # valores anteriores (doc_count*10, apoyo*5, critica*2) eran
    # multiplicadores arbitrarios sin fuente documentada.
    voces = []

    # Voces de Externos (datos reales de engagement por página)
    if externos_stats and externos_stats.get("posts", 0) > 0:
        try:
            from analytics.queries import get_external_page_engagement
            ext_pages = get_external_page_engagement()
            for ep in ext_pages[:5]:
                if ep.get("engagement", 0) > 0:
                    voces.append({
                        "pagina": ep.get("page_name", ""),
                        "postura": None,
                        "postura_nota": (
                            "No disponible: la fuente Externos no provee "
                            "sentimiento por comentario para derivar postura."
                        ),
                        "engagement": ep.get("engagement", 0),
                        "reacciones_totales": ep.get("total_reactions", 0),
                        "comentarios_totales": ep.get("comments_count", 0),
                        "compartidos_totales": 0,
                        "narrativa": "",
                        "enlaces_referencia": [],
                    })
        except Exception:
            pass

    total_apoyo_critica = total_apoyo + total_critica
    polarizacion_indice = 0.0
    if total_apoyo_critica > 0:
        polarizacion_indice = round(abs(total_apoyo - total_critica) / total_apoyo_critica, 3)

    # ── 16.3: Temas emergentes ──
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

    # ── §F: Alertas con series de tiempo, cooldown, sensibilidad y enlaces ──
    cooldown = alertas_cooldown_state or {}
    alertas = []
    alertas_links = []

    # Pre-compute monthly theme controversy for sensitivity calculations
    monthly_theme_controversy = fb_monthly_theme_controversy or []

    # ── ICI: controversia_actual de ventana de 7 días, historial mensual ──
    if fb_monthly_controversy and len(fb_monthly_controversy) >= 5:
        # controversia_actual: usar fb_period_controversy si se proveyó,
        # fallback al último mes de fb_monthly_controversy
        if fb_period_controversy is not None:
            controversia_actual_ici = fb_period_controversy[0]
        else:
            controversia_actual_ici = fb_monthly_controversy[-1][1]

        # Historial: meses previos, excluyendo el actual para evitar
        # traslape con la ventana de 7 días (el mes en curso parcialmente
        # cubierto por la ventana se excluye del historial mensual)
        historial_mensual = fb_monthly_controversy[:-1]
        hist_controversias = [c for _, c, n in historial_mensual if n >= 3]

        if len(hist_controversias) >= 4:
            # Sensibilidad del tema dominante del período
            tema_dominante = ""
            max_n_posts = 0
            if fb_per_theme_controversy:
                for td in fb_per_theme_controversy:
                    if td.get("n_posts", 0) > max_n_posts:
                        max_n_posts = td["n_posts"]
                        tema_dominante = td.get("tema", "")

            sens_ici = 1.0
            if tema_dominante and monthly_theme_controversy:
                sens_ici = calcular_sensibilidad_para_alertas(
                    tema_dominante, monthly_theme_controversy, fecha_hasta
                )
            umbral_ici = 2.0 * sens_ici

            alerta_ici = detectar_ici(
                controversia_actual_ici, hist_controversias, umbral_base=umbral_ici
            )
            if alerta_ici:
                if verificar_cooldown(cooldown.get("ICI"), ahora, "ICI"):
                    if fb_controversial_posts:
                        alerta_ici["enlaces_referencia"] = [
                            p["post_url"] for p in fb_controversial_posts[:5]
                            if p.get("post_url")
                        ]
                    alertas.append(alerta_ici)
                    alertas_links.extend(alerta_ici.get("enlaces_referencia", []))

    nsi_actual = net_sentiment_index(total_apoyo, total_critica, n_total)
    nsi_prev = n(nsi_previo) if nsi_previo is not None else 0.0
    alerta_sdi = detectar_sdi(nsi_actual, nsi_prev)
    if alerta_sdi:
        if verificar_cooldown(cooldown.get("SDI"), ahora, "SDI"):
            # enlaces_referencia: posts más controversiales del período
            if fb_controversial_posts:
                alerta_sdi["enlaces_referencia"] = [
                    p["post_url"] for p in fb_controversial_posts[:5]
                    if p.get("post_url")
                ]
            alertas.append(alerta_sdi)
            alertas_links.extend(alerta_sdi.get("enlaces_referencia", []))

    total_reacciones_fb = n(fb_stats.get("total_reacciones", 0)) if fb_stats else 0
    total_reacciones_tk = 0
    if tk_stats:
        total_reacciones_tk = (
            n(tk_stats.get("likes", 0)) + n(tk_stats.get("shares", 0))
            + n(tk_stats.get("favorites", 0)) + n(tk_stats.get("comments", 0))
        )
    total_reacciones_ext = 0
    if externos_stats:
        total_reacciones_ext = (
            n(externos_stats.get("total_reactions", 0))
            + n(externos_stats.get("comments", 0))
        )
    total_reacciones_all = total_reacciones_fb + total_reacciones_tk + total_reacciones_ext
    alerta_efi = None
    if er_previo is not None:
        alerta_efi = detectar_efi(er_display, er_previo, total_reacciones_all)
    if alerta_efi:
        if verificar_cooldown(cooldown.get("EFI"), ahora, "EFI"):
            # enlaces_referencia: posts con mayor caída de engagement
            if fb_controversial_posts:
                alerta_efi["enlaces_referencia"] = [
                    p["post_url"] for p in fb_controversial_posts[:5]
                    if p.get("post_url")
                ]
            alertas.append(alerta_efi)
            alertas_links.extend(alerta_efi.get("enlaces_referencia", []))

    if fb_per_theme_controversy:
        total_neg_r = sum(t.get("negativos", 0) for t in fb_per_theme_controversy)
        total_reac_r = sum(t.get("total_reacciones", 0) for t in fb_per_theme_controversy)
        ratio_enojo_general = total_neg_r / total_reac_r if total_reac_r > 0 else 0.0
        for tema_data in fb_per_theme_controversy:
            if tema_data.get("n_posts", 0) < 3:
                continue
            ratio_enojo_tema = tema_data["controversy"]

            # Sensibilidad temática ajustada para TAI
            tema_nombre = tema_data.get("tema", "")
            sens_tai = 1.0
            if tema_nombre and monthly_theme_controversy:
                sens_tai = calcular_sensibilidad_para_alertas(
                    tema_nombre, monthly_theme_controversy, fecha_hasta
                )
            umbral_tai = 2.0 * sens_tai

            alerta_tai = detectar_tai(
                ratio_enojo_tema, ratio_enojo_general,
                tema_data["n_posts"], umbral_base=umbral_tai
            )
            if alerta_tai:
                if verificar_cooldown(cooldown.get(f"TAI_{tema_data['tema']}"),
                                       ahora, "TAI"):
                    # enlaces_referencia: posts del tema que disparó la alerta
                    if fb_controversial_posts:
                        alerta_tai["enlaces_referencia"] = [
                            p["post_url"] for p in fb_controversial_posts
                            if p.get("topic_category") == tema_nombre
                            and p.get("post_url")
                        ][:5]
                    alertas.append(alerta_tai)
                    alertas_links.extend(alerta_tai.get("enlaces_referencia", []))

    if fb_anger_by_zone:
        for zona_data in fb_anger_by_zone:
            alerta_zdi = detectar_zdi(zona_data["pct_negativos"], zona_data["total"])
            if alerta_zdi:
                if verificar_cooldown(cooldown.get(f"ZDI_{zona_data['zona']}"),
                                       ahora, "ZDI"):
                    # enlaces_referencia: posts de la zona que disparó la alerta
                    zona_nombre = zona_data.get("zona", "")
                    if zona_nombre and zona_nombre != "sin_zona":
                        from analytics.queries import get_fb_posts_by_zone
                        posts_zona = get_fb_posts_by_zone(zona_nombre)
                        alerta_zdi["enlaces_referencia"] = [
                            p["post_url"] for p in posts_zona
                            if p.get("post_url")
                        ][:5]
                    alertas.append(alerta_zdi)
                    alertas_links.extend(alerta_zdi.get("enlaces_referencia", []))

    # ── §I: Autenticidad ──
    daily_vols_fb = []
    daily_vols_tk = []
    if fb_stats and fb_stats.get("daily_volumes"):
        daily_vols_fb = [v for _, v in fb_stats["daily_volumes"]]
    if tk_stats and tk_stats.get("daily_volumes"):
        daily_vols_tk = [v for _, v in tk_stats["daily_volumes"]]
    org_fb, coord_fb = autenticidad_pct(daily_vols_fb) if daily_vols_fb else (100.0, 0.0)
    org_tk, coord_tk = autenticidad_pct(daily_vols_tk) if daily_vols_tk else (100.0, 0.0)
    n_fb, n_tk = len(daily_vols_fb), len(daily_vols_tk)
    n_dias = n_fb + n_tk
    if n_dias > 0:
        pct_organico = round(org_fb * n_fb / n_dias + org_tk * n_tk / n_dias, 1)
        pct_coordinado = round(coord_fb * n_fb / n_dias + coord_tk * n_tk / n_dias, 1)
    else:
        pct_organico, pct_coordinado = 100.0, 0.0

    # ── §E: Risk Reputacional ──
    max_topic_controversy = 0.0
    if fb_per_theme_controversy:
        max_topic_controversy = max(
            (t.get("controversy", 0) for t in fb_per_theme_controversy), default=0.0
        )
    elif controversy_r > 0:
        max_topic_controversy = controversy_r

    vf = vol_factor(n(fb_stats.get("posts", 0)) if fb_stats else 0)
    rr = risk_reputacional(nsi_actual, max_topic_controversy, vf)

    rr_100 = rr * 100
    if rr_100 >= 60:
        semaforo = "rojo"
    elif rr_100 >= 30:
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
            "indice_riesgo": round(rr_100, 1),
            "pct_negativos": pct_critico,
            "indice_enojo_reacciones": round(
                (n(fb_stats.get("angrys", 0)) / total_reacciones_fb * 100)
                if total_reacciones_fb > 0 else 0, 1
            ),
            "balance_confrontacion": controversy_r,
            "n_temas_friccion": len(fricciones),
            "tema_principal": fricciones[0]["tema"] if fricciones else "",
            "emocion_principal": fricciones[0]["emocion_dominante"] if fricciones else "",
            "alertas_cambridge": [
                {"tipo": a["tipo"], "descripcion": a["descripcion"],
                 "enlaces_referencia": a.get("enlaces_referencia", [])}
                for a in alertas
            ],
            "narrativa": "",
            "enlaces_referencia": alertas_links,
            "formula_riesgo": (
                "RR = clamp((max_topic_controversy * 0.50 + nsi_deviation * 0.50) "
                "* vol_factor, 0, 1)  [decisión H5: sin factor *10]"
            ),
        },
    }

    # ── Bloque 4 ──
    bloque4_secciones = [
        "eco_historico", "leccion_aprendida", "brecha_percepcion_realidad",
        "contexto_no_visible", "correlacion_contenido_reaccion",
        "comparativa_sectorial", "proyeccion_escenario", "recomendacion_estrategica",
    ]
    bloque4 = {sec: {"narrativa": "", "enlaces_referencia": []} for sec in bloque4_secciones}

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
        {"tema": e["ngrama"], "variacion_semanal": e["ratio"],
         "pct_cambio": round((e["ratio"] - 1) * 100, 1)}
        for e in emergentes_result.get("emergentes", [])
        if e["tendencia"] == "desacelerando"
    ]

    # ── Indice de correlacion externa (independiente) ──
    try:
        from analytics.queries import calcular_correlacion_noticias_picos
        bloque4["indice_correlacion_externa"] = calcular_correlacion_noticias_picos()
    except Exception:
        bloque4["indice_correlacion_externa"] = {
            "semana": "", "engagement": 0, "fuente": "", "noticia": "",
            "fecha": "", "n_picos": 0, "coincidencias": 0,
            "indice_correlacion": 0.0,
        }

    # ── Persistir evidencia para paso narrar ──
    evidencia_data = {
        "periodo": periodo,
        "fecha_datos_hasta": fecha_hasta,
        "por_tema": {k: sorted(v) for k, v in evidencia_por_tema.items()},
        "por_emocion": {k: sorted(v) for k, v in evidencia_por_emocion.items()},
    }
    evidencia_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "_evidencia_periodo.json"
    )
    try:
        os.makedirs(os.path.dirname(evidencia_path), exist_ok=True)
        with open(evidencia_path, "w", encoding="utf-8") as f:
            json.dump(evidencia_data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # no bloquear el pipeline si falla la persistencia de evidencia

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
