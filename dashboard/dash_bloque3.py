"""Bloque III — Riesgo y Autenticidad.

Estaciones: Autenticidad, Nivel de Alerta, Velocidad de Propagación y Puntos
de Fricción. El Nivel de Alerta usa lenguaje natural (titular, acción, detalle,
factores y foco). Recibe `periodo` y `plataforma` como argumentos.
"""

import streamlit as st

from config import FACEBOOK_DB, TIKTOK_DB
from dashboard.dash_metrics import (
    safe_query,
    filtrar_por_periodo_plataforma,
    cargar_fb_engagement,
    cargar_tk_engagement,
    cargar_sentimiento_fb,
    cargar_comentarios_fb,
)
from dashboard.dash_audiencia import calcular_polarizacion
from dashboard.dash_riesgo import (
    calcular_autenticidad,
    calcular_nivel_alerta,
    calcular_propagacion_24_48,
    agrupar_fricciones,
)
from dashboard.dash_inteligencia import cargar_alertas_cambridge, traducir_alerta
from dashboard.dash_ui import (
    _page_head,
    hay_datos,
    card_explicativa,
    referencias_publicaciones,
    referencias_por_tema_comentarios,
    _post_ids_por_tema_comentarios,
)


def render_bloque3_riesgo(periodo, plataforma):
    _page_head(
        "RIESGO Y AUTENTICIDAD / GESTIÓN DE RIESGO REPUTACIONAL",
        "Riesgo, autenticidad y velocidad de propagación",
        "Señales tempranas sobre la salud de la conversación: patrones coordinados, necesidad de respuesta institucional, proyección a 24-48h y puntos críticos de fricción.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB, FACEBOOK_DB)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)
    df_sent = cargar_sentimiento_fb(FACEBOOK_DB)
    df_coment = cargar_comentarios_fb(FACEBOOK_DB)
    df_coment_raw = safe_query("SELECT message, sentiment, sentiment_score, topic_category FROM fb_comments", FACEBOOK_DB)

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos para este período.")
        return

    # ── 1. AUTENTICIDAD — orgánico vs coordinado/sospechoso ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Índice de Autenticidad</div><div class="section-subtitle">Proporción de conversación orgánica frente a patrones coordinados o sospechosos (mensajes repetidos).</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Qué parte de la conversación parece orgánica y qué parte parece copia-pega coordinado (mensajes idénticos repetidos).",
        "La barra verde es lo orgánico; la roja, lo sospechoso. Abajo se listan los mensajes que más se repiten.",
        "No detecta bots: solo mide repetición de texto idéntico.",
    )
    aut = calcular_autenticidad(df_coment_raw['message']) if not df_coment_raw.empty and 'message' in df_coment_raw.columns else None
    if aut:
        col_aut = {'organico': 'var(--green)', 'mixto': 'var(--amber)', 'coordinado': 'var(--red)'}.get(aut['nivel'], 'var(--accent)')
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_aut}">{aut['estado'].upper()}</div><div class="panel-meta">{aut['n_total']:,} COMENTARIOS · {aut['n_grupos']} GRUPOS REPETIDOS</div></div>
            <div class="bar-tri" style="height:16px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{aut['pct_organico']:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{aut['pct_sospechoso']:.1f}%"></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:12px">
                <span style="color:var(--green)">Orgánico {aut['pct_organico']:.0f}%</span>
                <span style="color:var(--red)">Sospechoso {aut['pct_sospechoso']:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if aut['ejemplos']:
            ej_html = "".join(f'<div class="bar-row"><div class="bar-row-label">\"{e["texto"][:80]}\"</div><div class="bar-row-val">×{e["veces"]}</div></div>' for e in aut['ejemplos'])
            st.markdown(f'<div class="panel" style="margin-top:8px"><div class="panel-head"><div class="panel-title">MENSAJES MÁS REPETIDOS</div></div>{ej_html}</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:var(--fg-muted)">Sospechoso = mensajes idénticos repetidos (posible copia-pega coordinado). No es detección de bots.</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Aún no hay suficientes comentarios para evaluar autenticidad.</div>', unsafe_allow_html=True)

    # ── 2. NIVEL DE ALERTA — necesidad de respuesta institucional (lenguaje natural) ──
    st.markdown('<div class="section-header"><div class="section-title">02 · Nivel de Alerta</div><div class="section-subtitle">Qué tan urgente es responder y, sobre todo, a qué responder.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Qué tan urgente es que la institución responda, en semáforo: verde (tranquilo), amarillo (preparar) o rojo (responder ya).",
        "El color resume el nivel de molestia. Abajo se nombran los temas concretos a los que habría que responder y qué podría crecer.",
    )
    pct_neg_val = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    enojo_val = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0
    pol_b3 = calcular_polarizacion(df_coment['score_sentimiento']) if not df_coment.empty and 'score_sentimiento' in df_coment.columns else None
    balance_b3 = pol_b3['balance'] if pol_b3 else None
    fricciones = agrupar_fricciones(df_coment_raw)
    alerta = calcular_nivel_alerta(pct_negativo=pct_neg_val, indice_enojo=enojo_val, balance_confrontacion=balance_b3, n_fricciones=len(fricciones), temas_friccion=fricciones)
    sem_class = {'verde': 'positive', 'amarillo': 'warning', 'rojo': 'critical'}.get(alerta['color'], 'positive')
    emoji_sem = {'verde': '🟢', 'amarillo': '🟡', 'rojo': '🔴'}.get(alerta['color'], '⚪')
    st.markdown(f'<div class="indicator indicator-{sem_class}"><div class="indicator-dot"></div><div style="flex:1"><div style="font-weight:600;font-size:14px;margin-bottom:2px">{emoji_sem} {alerta["titular"]}</div><div style="font-size:13px;color:var(--fg-secondary)">{alerta["accion"]}</div></div></div>', unsafe_allow_html=True)
    if alerta.get("detalle"):
        st.markdown(f'<div class="interpretation" style="margin-top:10px"><div class="interpretation-label">QUÉ SIGNIFICA</div><div class="interpretation-texto">{alerta["detalle"]}</div></div>', unsafe_allow_html=True)
    factores = alerta.get("factores", [])
    if factores:
        chips = "".join(f'<span style="font-size:11px;padding:3px 9px;margin:3px 4px 0 0;display:inline-block;background:var(--bg-elevated);border:1px solid var(--border);border-radius:12px;color:var(--fg-secondary)">{f}</span>' for f in factores)
        st.markdown(f'<div style="margin-top:8px"><div style="font-size:9px;color:var(--fg-muted);font-weight:600;letter-spacing:1.5px;text-transform:uppercase;font-family:IBM Plex Mono,monospace;margin-bottom:4px">POR QUÉ ESTE NIVEL</div>{chips}</div>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:11px;color:var(--fg-muted);margin-top:8px">Índice de necesidad de respuesta: {alerta["riesgo"]:.0f}/100 — combina cuántos comentarios son negativos, el enojo en las reacciones, la confrontación y los temas de fricción.</p>', unsafe_allow_html=True)
    if fricciones:
        ids_alerta = []
        for fr in fricciones[:3]:
            ids_alerta.extend(_post_ids_por_tema_comentarios(fr["tema"]))
        referencias_publicaciones(post_ids=ids_alerta, limit=8, titulo="PUBLICACIONES DETRÁS DE LA ALERTA")

    alertas = cargar_alertas_cambridge(FACEBOOK_DB)
    if alertas:
        st.markdown('<p style="font-size:11px;color:var(--fg-muted);margin-top:10px;font-weight:600">SEÑALES DE COMPORTAMIENTO DETECTADAS</p>', unsafe_allow_html=True)
        for a in alertas:
            ta = traducir_alerta(a)
            color_class = {"🟢": "positive", "🟡": "warning", "🔴": "critical"}.get(ta["color"], "warning")
            st.markdown(f'<div class="indicator indicator-{color_class}" style="margin-bottom:8px"><div class="indicator-dot"></div><div style="flex:1"><div style="font-weight:600;font-size:13px">{ta["color"]} {ta["titular"]}</div><div style="font-size:12px;color:var(--fg-secondary)">{ta["lectura"]}</div></div></div>', unsafe_allow_html=True)

    # ── 3. VELOCIDAD DE PROPAGACIÓN — proyección 24-48h ──
    st.markdown('<div class="section-header"><div class="section-title">03 · Velocidad de Propagación</div><div class="section-subtitle">Hacia dónde va la conversación en las próximas 24 a 48 horas.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Hacia dónde va la interacción en las próximas 24 a 48 horas si sigue la tendencia actual.",
        "Compara hoy con la proyección a 24h y 48h. Es una estimación por tendencia, no una certeza.",
    )
    prop = calcular_propagacion_24_48(df_fb)
    if prop:
        col_p = {'acelerando': 'var(--red)', 'desacelerando': 'var(--blue)', 'estable': 'var(--fg-secondary)'}.get(prop['tendencia'], 'var(--accent)')
        maxv = max(prop['hoy'], prop['proy_24h'], prop['proy_48h'], 1)
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_p}">{prop['flecha']} {prop['tendencia'].upper()}</div><div class="panel-meta">{prop['n_dias']} DÍAS DE TENDENCIA</div></div>
            <div class="bar-row"><div class="bar-row-label">HOY</div><div class="bar-track"><div class="bar-fill bar-fill-cy" style="width:{prop['hoy'] / maxv * 100:.1f}%"></div></div><div class="bar-row-val">{prop['hoy']:,.0f}</div></div>
            <div class="bar-row"><div class="bar-row-label">PROY. +24H</div><div class="bar-track"><div class="bar-fill" style="width:{prop['proy_24h'] / maxv * 100:.1f}%;background:{col_p}"></div></div><div class="bar-row-val">{prop['proy_24h']:,.0f} ({prop['pct_24h']:+.0f}%)</div></div>
            <div class="bar-row"><div class="bar-row-label">PROY. +48H</div><div class="bar-track"><div class="bar-fill" style="width:{prop['proy_48h'] / maxv * 100:.1f}%;background:{col_p}"></div></div><div class="bar-row-val">{prop['proy_48h']:,.0f} ({prop['pct_48h']:+.0f}%)</div></div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:var(--fg-muted)">Proyección por tendencia lineal de la interacción diaria reciente. Es una estimación, no una certeza; se actualiza con cada nuevo día de datos.</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Se necesitan al menos 3 días con interacción para proyectar a 24-48h.</div>', unsafe_allow_html=True)

    # ── 4. PUNTOS DE FRICCIÓN — 2-3 temas con más reacción negativa ──
    st.markdown('<div class="section-header"><div class="section-title">04 · Puntos de Fricción</div><div class="section-subtitle">Los 2-3 temas que más reacción negativa generan, con un comentario representativo.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Los temas que concentran más comentarios negativos, con una cita real de ejemplo.",
        "Cada tarjeta roja es un tema; el número son sus comentarios negativos y la frase entre comillas es un comentario representativo.",
    )
    if fricciones:
        for fr in fricciones:
            st.markdown(f'<div class="pattern-card pattern-card-critical"><div style="font-family:var(--font-mono);font-size:9px;letter-spacing:1.4px;color:var(--red);font-weight:700;margin-bottom:6px">{fr["tema"].upper()} · {fr["n"]} COMENTARIOS NEGATIVOS</div><p style="font-size:13px;color:var(--fg-primary);line-height:1.55;margin:0">\"{fr["cita"]}\"</p></div>', unsafe_allow_html=True)
            referencias_por_tema_comentarios(fr["tema"], limit=6)
    else:
        st.markdown('<div class="status-info">No se detectaron temas con reacción negativa relevante en este período. Si esperabas ver fricción, puede faltar volumen de comentarios clasificados.</div>', unsafe_allow_html=True)
