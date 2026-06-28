"""Bloque I — Pulso General.

Estaciones: Clima Narrativo, Intensidad y Concentracion Tematica. Recibe
`periodo` y `plataforma` como argumentos (ya no los lee de variables globales).
"""

import streamlit as st

from config import FACEBOOK_DB, TIKTOK_DB
from dashboard.muestra import evaluar_muestra
from dashboard.dash_metrics import (
    safe_query,
    filtrar_por_periodo_plataforma,
    cargar_fb_engagement,
    cargar_tk_engagement,
    cargar_sentimiento_fb,
    generar_interpretacion,
)
from dashboard.dash_pulso import (
    calcular_clima_diario,
    calcular_intensidad_vs_promedio,
    calcular_concentracion,
)
from dashboard.dash_ui import (
    _page_head,
    _warn_dropped_null_dates,
    hay_datos,
    card_explicativa,
    referencias_por_categoria,
    referencias_publicaciones,
)


def render_bloque1_pulso(periodo, plataforma):
    _warn_dropped_null_dates()
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB, FACEBOOK_DB)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    _page_head(
        "PULSO GENERAL / LECTURA CIUDADANA",
        "Pulso general de la conversación pública",
        "Síntesis ejecutiva del clima narrativo, intensidad de la conversación y concentración temática observada en el período seleccionado.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos para este período.")
        return

    # Métricas de sentimiento (alimentan el cierre factual).
    df_sent = cargar_sentimiento_fb(FACEBOOK_DB)
    score_val = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg_val = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos_val = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo_val = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0
    total_comentarios = df_sent['total_comentarios'].sum() if not df_sent.empty else 0

    # ── 1. CLIMA NARRATIVO ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Clima Narrativo</div><div class="section-subtitle">Tono dominante del día y su tendencia frente al día anterior.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "El tono (favorable, neutro o adverso) de los comentarios del último día con datos, y si mejoró o empeoró frente al día anterior.",
        "La barra reparte los comentarios en favorables, neutros y adversos. La flecha dice si lo favorable subió o bajó respecto al día previo.",
        "Se pondera por la cantidad de comentarios de cada publicación, no por número de publicaciones.",
    )
    clima = calcular_clima_diario(safe_query(
        "SELECT fs.pct_positivo, fs.pct_negativo, fs.total_comentarios, fe.created_time "
        "FROM fb_sentimiento fs JOIN fb_engagement fe ON fs.post_id = fe.post_id",
        FACEBOOK_DB,
    ))
    if clima:
        fav = clima['pct_favorable']; neu = clima['pct_neutro']; adv = clima['pct_adverso']
        dom = max((fav, 'Favorable'), (neu, 'Neutro'), (adv, 'Adverso'), key=lambda x: x[0])[1]
        delta = clima.get('delta_favorable')
        if delta is None:
            trend = '<span style="color:var(--fg-muted)">Sin día previo para comparar.</span>'
        elif delta > 1:
            trend = f'<span style="color:var(--green)">▲ +{delta:.1f} pts favorables respecto al día anterior.</span>'
        elif delta < -1:
            trend = f'<span style="color:var(--red)">▼ {delta:.1f} pts favorables respecto al día anterior.</span>'
        else:
            trend = f'<span style="color:var(--fg-secondary)">→ Estable respecto al día anterior ({delta:+.1f} pts).</span>'
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title">TONO DOMINANTE · {dom.upper()}</div><div class="panel-meta">{clima['n_comentarios']:,} COMENTARIOS · {clima['fecha']}</div></div>
            <div class="bar-tri" style="height:16px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{fav:.1f}%"></span>
                <span class="bar-tri-neu" style="width:{neu:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{adv:.1f}%"></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:12px">
                <span style="color:var(--green)">Favorable {fav:.0f}%</span>
                <span style="color:var(--amber)">Neutro {neu:.0f}%</span>
                <span style="color:var(--red)">Adverso {adv:.0f}%</span>
            </div>
            <div style="margin-top:10px;font-size:13px">{trend}</div>
        </div>
        """, unsafe_allow_html=True)
        m = evaluar_muestra(clima['n_comentarios'])
        st.markdown(f'<p style="font-size:11px;color:var(--fg-muted)">{m["etiqueta"]}</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Aún no hay suficientes comentarios con fecha para calcular el clima del día.</div>', unsafe_allow_html=True)

    # ── 2. INTENSIDAD ──
    st.markdown('<div class="section-header"><div class="section-title">02 · Intensidad de la Conversación</div><div class="section-subtitle">Volumen de interacción del último día frente al promedio diario de la semana.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Cuánta interacción (reacciones, comentarios, compartidos) generó el último día frente al promedio diario de la semana.",
        "Si la barra del último día es más larga que la del promedio, hubo más movimiento de lo habitual; si es más corta, hubo menos.",
    )
    intens = calcular_intensidad_vs_promedio(df_fb, df_tk)
    if intens:
        vol_hoy = intens['vol_hoy']; prom = intens['promedio']; pct = intens['pct_dif']
        maxv = max(vol_hoy, prom, 1)
        if pct > 15:
            col_hoy = 'var(--red)'; lectura = f'El último día registró {pct:.0f}% más interacción que el promedio de la semana.'
        elif pct < -15:
            col_hoy = 'var(--blue)'; lectura = f'El último día registró {abs(pct):.0f}% menos interacción que el promedio de la semana.'
        else:
            col_hoy = 'var(--accent)'; lectura = 'El último día se mantiene en línea con el promedio de la semana.'
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title">ÚLTIMO DÍA VS PROMEDIO SEMANAL</div><div class="panel-meta">{intens['fecha_hoy']} · {intens['n_ref']} DÍAS DE REFERENCIA</div></div>
            <div class="bar-row"><div class="bar-row-label">ÚLTIMO DÍA</div><div class="bar-track"><div class="bar-fill" style="width:{vol_hoy / maxv * 100:.1f}%;background:{col_hoy}"></div></div><div class="bar-row-val">{vol_hoy:,.0f}</div></div>
            <div class="bar-row"><div class="bar-row-label">PROMEDIO</div><div class="bar-track"><div class="bar-fill bar-fill-blu" style="width:{prom / maxv * 100:.1f}%"></div></div><div class="bar-row-val">{prom:,.0f}</div></div>
            <div style="margin-top:10px;font-size:13px;color:var(--fg-primary)">{lectura}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Aún no hay suficientes días con interacción para comparar contra el promedio semanal.</div>', unsafe_allow_html=True)

    # ── 3. CONCENTRACIÓN TEMÁTICA — desglose completo de todos los temas ──
    st.markdown('<div class="section-header"><div class="section-title">03 · Concentración Temática</div><div class="section-subtitle">Cómo se reparte la conversación entre todos los temas, no solo el principal.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Si la conversación gira en torno a un solo tema o está repartida entre varios.",
        "Cada color es un tema y su porcentaje es la parte de la conversación que ocupa. Mientras más repartidos los colores, más diversa es la conversación.",
        "HHI alto = un tema concentra casi todo; HHI bajo = conversación fragmentada.",
    )
    df_cat = safe_query("SELECT item_id, categoria_nombre FROM post_categorias", FACEBOOK_DB)
    conc = calcular_concentracion(df_cat['categoria_nombre'].value_counts().to_dict()) if not df_cat.empty else None
    if conc:
        col_estado = {'dominado': 'var(--red)', 'liderado': 'var(--amber)', 'fragmentado': 'var(--green)'}.get(conc['nivel'], 'var(--accent)')
        ramas = conc.get('ramas', [])
        paleta = ['var(--accent)', '#a78bfa', '#f59e0b', '#34d399', '#f472b6', '#60a5fa', '#fbbf24', '#4ade80', '#fb7185', '#818cf8']
        segmentos = ""
        filas = ""
        for i, rama in enumerate(ramas):
            c = paleta[i % len(paleta)]
            segmentos += f'<span title="{rama["tema"]} {rama["share"]:.0f}%" style="display:inline-block;height:100%;background:{c};width:{rama["share"]:.1f}%"></span>'
            filas += (
                '<div style="display:flex;align-items:center;gap:8px;margin-top:6px;font-size:12px">'
                f'<span style="width:10px;height:10px;border-radius:2px;background:{c};display:inline-block;flex:none"></span>'
                f'<span style="flex:1;color:var(--fg-primary)">{rama["tema"]}</span>'
                f'<span style="color:var(--fg-secondary)">{rama["n"]} publicaciones · {rama["share"]:.0f}%</span>'
                '</div>'
            )
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_estado}">{conc['estado'].upper()}</div><div class="panel-meta">{conc['n_temas']} TEMAS · HHI {conc['hhi']:.2f}</div></div>
            <div class="bar-tri" style="height:16px;border-radius:3px">{segmentos}</div>
            <div style="margin-top:12px">{filas}</div>
        </div>
        """, unsafe_allow_html=True)
        referencias_por_categoria(conc['top_tema'])
    else:
        st.markdown('<div class="status-info">Clasificación de temas no disponible para este período.</div>', unsafe_allow_html=True)

    st.markdown('<div class="status-info">Este análisis está basado al 100% en los comentarios extraídos y analizados de las publicaciones revisadas.</div>', unsafe_allow_html=True)

    # ── CIERRE FACTUAL — lectura en una frase ──
    interp_cierre = generar_interpretacion("semaforo", {
        'score': score_val, 'pct_negativo': pct_neg_val,
        'pct_positivo': pct_pos_val, 'indice_enojo': enojo_val,
        'total_comentarios': int(total_comentarios),
    })
    st.markdown(f'<div class="interpretation" style="margin-top:16px"><div class="interpretation-label">🔎 En una frase:</div><div class="interpretation-texto">{interp_cierre}</div></div>', unsafe_allow_html=True)
    referencias_publicaciones(limit=10, titulo="PUBLICACIONES ANALIZADAS")
