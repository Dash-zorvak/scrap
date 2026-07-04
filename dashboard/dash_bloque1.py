"""Bloque I — Pulso General.

Estaciones: Clima Narrativo, Intensidad y Concentracion Tematica.

Todas las estaciones que hablan de comentarios usan la MISMA fuente unica
(dash_fuente) filtrada por el periodo y la plataforma seleccionados, de modo que
el clima y el cierre "en una frase" cuenten exactamente lo mismo y siempre sobre
el 100% de los comentarios del periodo de la(s) plataforma(s) activa(s).

Filtro por plataforma:
  - Facebook  -> solo datos de Facebook.
  - TikTok    -> solo datos de TikTok.
  - Ambas     -> Facebook + TikTok combinados.
Ninguna estacion mezcla plataformas cuando el filtro no lo indica.
"""

import pandas as pd
import streamlit as st

from config import FACEBOOK_DB, TIKTOK_DB
from dashboard.dash_periodos import rango_periodo, etiqueta_rango
from dashboard.dash_fuente import (
    cargar_comentarios_periodo,
    distribucion_sentimiento,
    frase_clima,
    cargar_engagement_periodo,
)
from dashboard.dash_pulso import (
    calcular_intensidad_vs_promedio,
    calcular_concentracion,
)
from dashboard.dash_ui import (
    _page_head,
    _warn_dropped_null_dates,
    hay_datos,
    card_explicativa,
    card_narrativa,
    referencias_por_categoria,
    referencias_publicaciones,
)


def _conteo_categorias(df_fb, df_tk, plataforma):
    """Conteo de categorias tematicas del periodo respetando la plataforma.

    Recibe df_fb y df_tk ya cargados y filtrados por cargar_engagement_periodo.
    """
    plat = str(plataforma or "").lower()
    frames = []
    if "tik" not in plat and df_fb is not None and not df_fb.empty and "categoria_nombre" in df_fb.columns:
        frames.append(df_fb[["categoria_nombre"]])
    if plat != "facebook" and df_tk is not None and not df_tk.empty and "categoria_nombre" in df_tk.columns:
        frames.append(df_tk[["categoria_nombre"]])
    if not frames:
        return {}
    cat = pd.concat(frames, ignore_index=True)["categoria_nombre"].dropna()
    cat = cat[cat.astype(str).str.strip() != ""]
    return cat.value_counts().to_dict()


def render_bloque1_pulso(periodo, plataforma):
    _warn_dropped_null_dates()

    ref = st.session_state.get("fecha_ref")
    ini, fin = rango_periodo(
        periodo, ref,
        st.session_state.get("fecha_desde"),
        st.session_state.get("fecha_hasta"),
    )

    # Fuente unica de comentarios del periodo (100%, sentimiento por comentario),
    # ya filtrada por plataforma.
    df_coment = cargar_comentarios_periodo(ini, fin, plataforma)
    dist = distribucion_sentimiento(df_coment, plataforma)

    # Engagement para Intensidad: la comparacion ultimo dia vs promedio semanal
    # necesita la ventana semanal completa, asi que solo se filtra por plataforma
    # (ini=None, fin=None = sin filtro de período).
    df_fb_int, df_tk_int = cargar_engagement_periodo(None, None, plataforma)

    # Engagement para Concentración Temática: ya filtrado por fecha via
    # cargar_engagement_periodo(ini, fin, plataforma)
    df_fb_cat, df_tk_cat = cargar_engagement_periodo(ini, fin, plataforma)

    _page_head(
        "PULSO GENERAL / LECTURA CIUDADANA",
        "Pulso general de la conversación pública",
        "Síntesis ejecutiva del clima narrativo, la intensidad de la conversación y la concentración temática del período seleccionado.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> {etiqueta_rango(ini, fin).upper()} <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    if dist["n_total"] == 0 and (df_fb_int is None or df_fb_int.empty) and (df_tk_int is None or df_tk_int.empty):
        hay_datos(df_fb_int, "No hay datos para este período.")
        return

    # ── 1. CLIMA NARRATIVO ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Clima Narrativo</div></div>', unsafe_allow_html=True)
    if dist["n_total"] > 0:
        _dom_pct, _dom = max((dist["pct_favorable"], "Favorable"), (dist["pct_neutral"], "Neutral"), (dist["pct_critico"], "Crítico"), key=lambda x: x[0])
        card_narrativa(
            f"El tono que más domina es <strong>{_dom}</strong>: {_dom_pct:.0f}% de {dist['n_total']:,} comentarios del período.",
            tono=_dom.lower(),
        )
    card_explicativa(
        "Qué está ocurriendo: cómo se reparte el ánimo de la ciudadanía entre comentarios a favor, neutrales y críticos.",
        "La barra reparte el 100% de los comentarios del período. Mientras más verde, más apoyo; mientras más rojo, más crítica.",
    )
    if dist["n_total"] > 0:
        fav = dist["pct_favorable"]; neu = dist["pct_neutral"]; adv = dist["pct_critico"]
        dom = max((fav, "Favorable"), (neu, "Neutral"), (adv, "Crítico"), key=lambda x: x[0])[1]
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title">TONO DOMINANTE · {dom.upper()}</div><div class="panel-meta">{dist['n_total']:,} COMENTARIOS · 100% DEL PERÍODO</div></div>
            <div class="bar-tri" style="height:18px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{fav:.1f}%"></span>
                <span class="bar-tri-neu" style="width:{neu:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{adv:.1f}%"></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:13px">
                <span style="color:var(--green)">A favor {fav:.0f}%</span>
                <span style="color:var(--amber)">Neutral {neu:.0f}%</span>
                <span style="color:var(--red)">Crítico {adv:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">No hay comentarios en el período seleccionado.</div>', unsafe_allow_html=True)

    # ── 2. INTENSIDAD ──
    intens = calcular_intensidad_vs_promedio(df_fb_int, df_tk_int)
    st.markdown('<div class="section-header"><div class="section-title">02 · Intensidad de la Conversación</div></div>', unsafe_allow_html=True)
    if intens:
        _pct = intens['pct_dif']; _prom = intens['promedio']; _vol = intens['vol_hoy']
        if _pct > 5:
            _txt = f"El último día hubo un <strong>{_pct:.0f}% más</strong> de interacción que en un día normal, que suele ser de <strong>{_prom:,.0f}</strong>; se registraron {_vol:,.0f}."
            _tono = "critico"
        elif _pct < -5:
            _txt = f"El último día hubo un <strong>{abs(_pct):.0f}% menos</strong> de interacción que en un día normal, que suele ser de <strong>{_prom:,.0f}</strong>; se registraron {_vol:,.0f}."
            _tono = "favorable"
        else:
            _txt = f"El último día la interacción estuvo <strong>en línea</strong> con un día normal, que suele ser de <strong>{_prom:,.0f}</strong>; se registraron {_vol:,.0f}."
            _tono = "neutral"
        card_narrativa(_txt, tono=_tono)
    card_explicativa(
        "Qué está ocurriendo: cuánta interacción (reacciones, comentarios y compartidos) generó el último día frente al promedio diario de la semana.",
        "Si el último día superó al promedio, hubo más movimiento de lo habitual; si quedó por debajo, hubo menos.",
    )
    if intens:
        vol_hoy = intens['vol_hoy']; prom = intens['promedio']; pct = intens['pct_dif']
        maxv = max(vol_hoy, prom, 1)
        if pct > 15:
            col_hoy = 'var(--red)'; signo = f'+{pct:.0f}%'; titular = 'MÁS movimiento de lo habitual'
        elif pct < -15:
            col_hoy = 'var(--blue)'; signo = f'{pct:.0f}%'; titular = 'MENOS movimiento de lo habitual'
        else:
            col_hoy = 'var(--accent)'; signo = f'{pct:+.0f}%'; titular = 'En línea con una semana normal'
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title">INTENSIDAD DEL ÚLTIMO DÍA</div><div class="panel-meta">{intens['fecha_hoy']} · {intens['n_ref']} DÍAS DE REFERENCIA</div></div>
            <div style="display:flex;align-items:baseline;gap:14px;margin:4px 0 12px">
                <span style="font-size:44px;font-weight:700;line-height:1;color:{col_hoy}">{signo}</span>
                <span style="font-size:15px;color:var(--fg-secondary)">{titular} de interacción</span>
            </div>
            <div style="font-size:15px;color:var(--fg-primary);margin-bottom:12px">El último día hubo <b>{vol_hoy:,.0f}</b> interacciones frente a un promedio semanal de <b>{prom:,.0f}</b>.</div>
            <div class="bar-row"><div class="bar-row-label">ÚLTIMO DÍA</div><div class="bar-track"><div class="bar-fill" style="width:{vol_hoy / maxv * 100:.1f}%;background:{col_hoy}"></div></div><div class="bar-row-val">{vol_hoy:,.0f}</div></div>
            <div class="bar-row"><div class="bar-row-label">PROMEDIO</div><div class="bar-track"><div class="bar-fill bar-fill-blu" style="width:{prom / maxv * 100:.1f}%"></div></div><div class="bar-row-val">{prom:,.0f}</div></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Aún no hay suficientes días con interacción para comparar contra el promedio semanal.</div>', unsafe_allow_html=True)

    # ── 3. CONCENTRACIÓN TEMÁTICA ──
    # Usar df_fb/df_tk ya filtrados por fecha desde cargar_engagement_periodo
    df_fb_cat, df_tk_cat = cargar_engagement_periodo(ini, fin, plataforma)
    conteo_cat = _conteo_categorias(df_fb_cat, df_tk_cat, plataforma)
    conc = calcular_concentracion(conteo_cat) if conteo_cat else None
    st.markdown('<div class="section-header"><div class="section-title">03 · Concentración Temática</div></div>', unsafe_allow_html=True)
    if conc:
        _ramas = conc.get('ramas', [])
        _share = _ramas[0]['share'] if _ramas else conc.get('share_top', 0)
        if conc['nivel'] == 'dominado':
            _txt = f"La conversación gira sobre todo en torno a <strong>«{conc['top_tema']}»</strong>, que concentra el {_share:.0f}% de las publicaciones del período."
        elif conc['nivel'] == 'liderado':
            _txt = f"El tema <strong>«{conc['top_tema']}»</strong> lidera con el {_share:.0f}%, pero la conversación se reparte entre {conc['n_temas']} temas."
        else:
            _txt = f"La conversación está repartida entre <strong>{conc['n_temas']} temas</strong>; ninguno supera el {_share:.0f}% del total."
        card_narrativa(_txt, tono="neutral")
    card_explicativa(
        "Qué está ocurriendo: en qué temas se concentra la conversación ciudadana del período.",
        "Cada color es un tema y su porcentaje es la parte de la conversación que ocupa. Mientras más repartidos los colores, más diversa es la conversación.",
    )
    if conc:
        nivel = conc['nivel']
        col_estado = {'dominado': 'var(--red)', 'liderado': 'var(--amber)', 'fragmentado': 'var(--green)'}.get(nivel, 'var(--accent)')
        if nivel == 'dominado':
            conclusion = f"Pocos asuntos concentran casi toda la conversación: el tema «{conc['top_tema']}» domina lo que se habla."
        elif nivel == 'liderado':
            conclusion = f"El tema «{conc['top_tema']}» lidera la conversación, pero no la monopoliza."
        else:
            conclusion = "La conversación está repartida entre varios temas; ninguno domina por sí solo."
        ramas = conc.get('ramas', [])
        paleta = ['var(--accent)', '#a78bfa', '#f59e0b', '#34d399', '#f472b6', '#60a5fa', '#fbbf24', '#4ade80', '#fb7185', '#818cf8']
        segmentos = ""
        filas = ""
        for i, rama in enumerate(ramas):
            c = paleta[i % len(paleta)]
            segmentos += f'<span title="{rama["tema"]} {rama["share"]:.0f}%" style="display:inline-block;height:100%;background:{c};width:{rama["share"]:.1f}%"></span>'
            filas += (
                '<div style="display:flex;align-items:center;gap:8px;margin-top:6px;font-size:13px">'
                f'<span style="width:10px;height:10px;border-radius:2px;background:{c};display:inline-block;flex:none"></span>'
                f'<span style="flex:1;color:var(--fg-primary)">{rama["tema"]}</span>'
                f'<span style="color:var(--fg-secondary)">{rama["n"]} publicaciones · {rama["share"]:.0f}%</span>'
                '</div>'
            )
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_estado}">{conc['estado'].upper()}</div><div class="panel-meta">{conc['n_temas']} TEMAS</div></div>
            <div style="font-size:16px;font-weight:600;color:var(--fg-primary);margin:2px 0 12px">{conclusion}</div>
            <div class="bar-tri" style="height:18px;border-radius:3px">{segmentos}</div>
            <div style="margin-top:12px">{filas}</div>
        </div>
        """, unsafe_allow_html=True)
        referencias_por_categoria(conc['top_tema'], plataforma=plataforma)
    else:
        st.markdown('<div class="status-info">Clasificación de temas no disponible para este período.</div>', unsafe_allow_html=True)

    # ── CIERRE — una sola verdad, misma fuente que el Clima ──
    st.markdown(f'<div class="interpretation" style="margin-top:16px"><div class="interpretation-label">En resumen:</div><div class="interpretation-texto">{frase_clima(dist)}</div></div>', unsafe_allow_html=True)
    referencias_publicaciones(limit=10, titulo="Enlaces de referencias bibliográficas", plataforma=plataforma)
