"""Bloque III — Riesgo y Autenticidad.

Estaciones: Autenticidad, Nivel de Alerta (solo semáforo), Velocidad de
Propagación y Puntos de Fricción. Todo se calcula sobre la fuente única
(dash_fuente) filtrada por el periodo y la plataforma seleccionados, usando el
100% de los comentarios del periodo. El lenguaje es ejecutivo: cada estación
responde qué ocurre, por qué y qué hacer.

Filtro por plataforma:
  - Comentarios, distribución de sentimiento, autenticidad y fricciones respetan
    el filtro (Facebook / TikTok / Ambas) a través de dash_fuente.
  - El índice de enojo que alimenta el Nivel de Alerta se delega en
    dash_emocional.metricas_emocionales (Facebook por reacciones tipadas, TikTok
    por sentimiento de comentarios, "Ambas" ponderado por volumen), en lugar de
    leerse solo de las reacciones de Facebook.
"""

import pandas as pd
import streamlit as st

from config import FACEBOOK_DB, TIKTOK_DB
from dashboard.dash_metrics import cargar_fb_engagement, cargar_tk_engagement
from dashboard.dash_audiencia import polarizacion_desde_conteos
from dashboard.dash_riesgo import (
    calcular_autenticidad,
    calcular_nivel_alerta,
    calcular_propagacion_24_48,
)
from dashboard.dash_periodos import rango_periodo, filtrar_por_fecha, etiqueta_rango
from dashboard.dash_fuente import (
    cargar_comentarios_periodo,
    distribucion_sentimiento,
    clasificar_comentario,
)
from dashboard.dash_emocional import metricas_emocionales
from dashboard.dash_ui import (
    _page_head,
    card_explicativa,
    card_narrativa,
    referencias_publicaciones,
    referencias_por_tema_comentarios,
    _post_ids_por_tema_comentarios,
)


def _filtra_fecha(df, ini, fin):
    if df is None or df.empty:
        return df
    col = "created_time" if "created_time" in df.columns else ("created_at" if "created_at" in df.columns else None)
    if col is None:
        return df
    return filtrar_por_fecha(df, col, ini, fin)


def _detectar_fricciones(df_coment, top_n=3):
    """Temas con más comentarios críticos del periodo, con una cita real.

    Usa la MISMA clasificación que el resto del dashboard (clasificar_comentario)
    para que, si el Clima muestra comentarios críticos, aquí sí aparezcan. Antes
    quedaba vacío porque dependía de etiquetas de sentimiento que no siempre
    coincidían.
    """
    if df_coment is None or df_coment.empty:
        return []
    dfc = df_coment.copy()
    dfc["_clase"] = dfc.apply(clasificar_comentario, axis=1)
    dfc["_score"] = pd.to_numeric(dfc.get("sentiment_score"), errors="coerce")
    crit = dfc[dfc["_clase"] == "critico"].copy()
    if crit.empty:
        return []
    if "topic_category" in crit.columns:
        crit["_tema"] = crit["topic_category"].fillna("General").replace("", "General")
    else:
        crit["_tema"] = "General"
    fr = []
    for tema, g in crit.groupby("_tema"):
        if g["_score"].notna().any():
            peor = g.sort_values("_score").iloc[0]
        else:
            peor = g.iloc[0]
        cita = str(peor["message"])[:160] if "message" in g.columns else ""
        fr.append({"tema": str(tema), "n": int(len(g)), "cita": cita})
    fr.sort(key=lambda x: x["n"], reverse=True)
    return fr[:top_n]


def render_bloque3_riesgo(periodo, plataforma):
    ref = st.session_state.get("fecha_ref")
    ini, fin = rango_periodo(
        periodo, ref,
        st.session_state.get("fecha_desde"),
        st.session_state.get("fecha_hasta"),
    )

    _page_head(
        "RIESGO Y AUTENTICIDAD / GESTIÓN DE RIESGO REPUTACIONAL",
        "Riesgo, autenticidad y velocidad de propagación",
        "Señales tempranas sobre la salud de la conversación: qué tan urgente es responder, hacia dónde va la interacción y qué temas generan más rechazo.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> {etiqueta_rango(ini, fin).upper()} <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    df_coment = cargar_comentarios_periodo(ini, fin, plataforma)
    dist = distribucion_sentimiento(df_coment, plataforma)

    plat = (plataforma or "").lower()
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB) if "tik" not in plat else pd.DataFrame()
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB, FACEBOOK_DB) if plat != "facebook" else pd.DataFrame()
    df_eng_fb = _filtra_fecha(df_fb_raw, ini, fin)
    df_eng_tk = _filtra_fecha(df_tk_raw, ini, fin)
    if "tik" in plat and df_eng_tk is not None and not df_eng_tk.empty:
        df_eng = df_eng_tk
    else:
        df_eng = df_eng_fb

    if dist["n_total"] == 0 and (df_eng is None or df_eng.empty):
        st.markdown('<div class="status-info">No hay datos en el período seleccionado.</div>', unsafe_allow_html=True)
        return

    # ── 1. AUTENTICIDAD ──
    aut = calcular_autenticidad(df_coment["message"]) if dist["n_total"] > 0 and "message" in df_coment.columns else None
    st.markdown('<div class="section-header"><div class="section-title">01 · Índice de Autenticidad</div></div>', unsafe_allow_html=True)
    if aut:
        _tono = "favorable" if aut['nivel'] == 'organico' else ("critico" if aut['nivel'] == 'coordinado' else "neutral")
        card_narrativa(
            f"El <strong>{aut['pct_organico']:.0f}%</strong> de los comentarios es espontáneo y el {aut['pct_sospechoso']:.0f}% son mensajes idénticos repetidos.",
            tono=_tono,
        )
    card_explicativa(
        "Qué está ocurriendo: si los comentarios son espontáneos o si hay mensajes copiados y pegados muchas veces.",
        "La barra verde es lo espontáneo; la roja, los mensajes repetidos. Abajo se destaca el mensaje más repetido.",
    )
    if aut:
        col_aut = {'organico': 'var(--green)', 'mixto': 'var(--amber)', 'coordinado': 'var(--red)'}.get(aut['nivel'], 'var(--accent)')
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_aut}">{aut['estado'].upper()}</div><div class="panel-meta">{aut['n_total']:,} COMENTARIOS</div></div>
            <div class="bar-tri" style="height:16px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{aut['pct_organico']:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{aut['pct_sospechoso']:.1f}%"></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:13px">
                <span style="color:var(--green)">Espontáneo {aut['pct_organico']:.0f}%</span>
                <span style="color:var(--red)">Repetido {aut['pct_sospechoso']:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if aut['ejemplos']:
            top = aut['ejemplos'][0]
            st.markdown(f'<div class="pattern-card" style="border-left:3px solid var(--accent);margin-top:8px"><div style="font-family:var(--font-mono);font-size:10px;letter-spacing:1.4px;color:var(--accent);font-weight:700;margin-bottom:6px">MENSAJE MÁS REPETIDO POR LOS CIUDADANOS</div><p style="font-size:16px;color:var(--fg-primary);line-height:1.5;margin:0">El mensaje “{top["texto"][:90]}” se repitió {top["veces"]} veces entre los comentarios.</p></div>', unsafe_allow_html=True)
            otros = aut['ejemplos'][1:]
            if otros:
                ej_html = "".join(f'<div class="bar-row"><div class="bar-row-label">“{e["texto"][:70]}”</div><div class="bar-row-val">{e["veces"]} veces</div></div>' for e in otros)
                st.markdown(f'<div class="panel" style="margin-top:8px"><div class="panel-head"><div class="panel-title">OTROS MENSAJES REPETIDOS</div></div>{ej_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Aún no hay suficientes comentarios para evaluar autenticidad en este período.</div>', unsafe_allow_html=True)

    # ── 2. NIVEL DE ALERTA — solo semáforo ──
    fricciones = _detectar_fricciones(df_coment)
    pct_neg_val = dist["pct_critico"]
    # Indice de enojo desacoplado por plataforma (no se lee solo de FB).
    enojo_val = float(metricas_emocionales(plataforma, ini, fin).get("indice_enojo", 0) or 0)
    pol_b3 = polarizacion_desde_conteos(dist["n_favorable"], dist["n_critico"], dist["n_total"]) if dist["n_total"] > 0 else None
    balance_b3 = pol_b3['balance'] if pol_b3 else None
    alerta = calcular_nivel_alerta(pct_negativo=pct_neg_val, indice_enojo=enojo_val, balance_confrontacion=balance_b3, n_fricciones=len(fricciones), temas_friccion=fricciones)
    st.markdown('<div class="section-header"><div class="section-title">02 · Nivel de Alerta</div></div>', unsafe_allow_html=True)
    _tono_al = {'verde': 'favorable', 'amarillo': 'neutral', 'rojo': 'critico'}.get(alerta['color'], 'neutral')
    _senales = f"{dist['pct_critico']:.0f}% de comentarios críticos" + (f" y {len(fricciones)} tema(s) con rechazo" if fricciones else "")
    card_narrativa(
        f"El nivel de alerta es <strong>{alerta['titular'].lower()}</strong>: las señales a vigilar son {_senales}.",
        tono=_tono_al,
    )
    card_explicativa(
        "Qué está ocurriendo: qué tan urgente es que la alcaldía responda, en semáforo (verde tranquilo, amarillo preparar, rojo responder ya).",
        "El color resume el nivel de molestia. Abajo se nombran los temas concretos a los que conviene responder.",
    )
    sem_class = {'verde': 'positive', 'amarillo': 'warning', 'rojo': 'critical'}.get(alerta['color'], 'positive')
    emoji_sem = {'verde': '🟢', 'amarillo': '🟡', 'rojo': '🔴'}.get(alerta['color'], '⚪')
    st.markdown(f'<div class="indicator indicator-{sem_class}"><div class="indicator-dot"></div><div style="flex:1"><div style="font-weight:600;font-size:16px;margin-bottom:2px">{emoji_sem} {alerta["titular"]}</div><div style="font-size:14px;color:var(--fg-secondary)">{alerta["accion"]}</div></div></div>', unsafe_allow_html=True)
    if alerta.get("detalle"):
        st.markdown(f'<div class="interpretation" style="margin-top:10px"><div class="interpretation-label">QUÉ SIGNIFICA</div><div class="interpretation-texto">{alerta["detalle"]}</div></div>', unsafe_allow_html=True)
    if fricciones:
        ids_alerta = []
        for fr in fricciones[:3]:
            ids_alerta.extend(_post_ids_por_tema_comentarios(fr["tema"]))
        referencias_publicaciones(post_ids=ids_alerta, limit=8, titulo="PUBLICACIONES DETRÁS DE LA ALERTA", plataforma=plataforma)

    # ── 3. VELOCIDAD DE PROPAGACIÓN — con contexto narrativo ──
    prop = calcular_propagacion_24_48(df_eng) if df_eng is not None and not df_eng.empty else None
    st.markdown('<div class="section-header"><div class="section-title">03 · Velocidad de Propagación</div></div>', unsafe_allow_html=True)
    if prop:
        if prop['tendencia'] == 'acelerando':
            _txt = f"La interacción va <strong>en aumento</strong>: de {prop['hoy']:,.0f} hoy a unas {prop['proy_24h']:,.0f} mañana ({prop['pct_24h']:+.0f}%)."
            _tono = "critico"
        elif prop['tendencia'] == 'desacelerando':
            _txt = f"La interacción va <strong>a la baja</strong>: de {prop['hoy']:,.0f} hoy a unas {prop['proy_24h']:,.0f} mañana ({prop['pct_24h']:+.0f}%)."
            _tono = "favorable"
        else:
            _txt = f"La interacción se mantiene <strong>estable</strong>: unas {prop['proy_24h']:,.0f} mañana, similar a las {prop['hoy']:,.0f} de hoy."
            _tono = "neutral"
        card_narrativa(_txt, tono=_tono)
    card_explicativa(
        "Qué está ocurriendo: si la interacción (reacciones, comentarios y veces compartido) está creciendo o cayendo.",
        "Se compara la interacción de hoy con una estimación para mañana y pasado mañana, según la tendencia reciente.",
    )
    if prop:
        col_p = {'acelerando': 'var(--red)', 'desacelerando': 'var(--blue)', 'estable': 'var(--fg-secondary)'}.get(prop['tendencia'], 'var(--accent)')
        maxv = max(prop['hoy'], prop['proy_24h'], prop['proy_48h'], 1)
        if prop['tendencia'] == 'acelerando':
            narrativa = f"La interacción está creciendo. Hoy se registraron {prop['hoy']:,.0f} interacciones y, si sigue este ritmo, mañana rondarían las {prop['proy_24h']:,.0f}. Conviene preparar contenido y respuestas porque el alcance va en aumento."
        elif prop['tendencia'] == 'desacelerando':
            narrativa = f"La interacción está cayendo. Hoy se registraron {prop['hoy']:,.0f} interacciones y, si sigue este ritmo, mañana bajarían a unas {prop['proy_24h']:,.0f}. La conversación está perdiendo fuerza por sí sola."
        else:
            narrativa = f"La interacción está estable. Hoy se registraron {prop['hoy']:,.0f} interacciones y se espera un nivel parecido mañana (unas {prop['proy_24h']:,.0f}). No hay cambios bruscos a la vista."
        st.markdown(f'<div class="indicator indicator-{ "critical" if prop["tendencia"]=="acelerando" else "positive" }" style="margin-bottom:10px"><div class="indicator-dot"></div><div style="flex:1"><div style="font-weight:600;font-size:16px;margin-bottom:2px">{prop["flecha"]} La conversación está {prop["tendencia"]}</div><div style="font-size:14px;color:var(--fg-secondary)">{narrativa}</div></div></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_p}">INTERACCIONES POR DÍA</div><div class="panel-meta">ESTIMACIÓN POR TENDENCIA</div></div>
            <div class="bar-row"><div class="bar-row-label">Hoy</div><div class="bar-track"><div class="bar-fill bar-fill-cy" style="width:{prop['hoy'] / maxv * 100:.1f}%"></div></div><div class="bar-row-val">{prop['hoy']:,.0f} interacciones</div></div>
            <div class="bar-row"><div class="bar-row-label">Mañana (estimado)</div><div class="bar-track"><div class="bar-fill" style="width:{prop['proy_24h'] / maxv * 100:.1f}%;background:{col_p}"></div></div><div class="bar-row-val">{prop['proy_24h']:,.0f} ({prop['pct_24h']:+.0f}%)</div></div>
            <div class="bar-row"><div class="bar-row-label">En 2 días (estimado)</div><div class="bar-track"><div class="bar-fill" style="width:{prop['proy_48h'] / maxv * 100:.1f}%;background:{col_p}"></div></div><div class="bar-row-val">{prop['proy_48h']:,.0f} ({prop['pct_48h']:+.0f}%)</div></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Se necesitan al menos 3 días con interacción para estimar hacia dónde va la conversación. Amplía el período (por ejemplo, “Esta semana” o “Este mes”) para ver esta proyección.</div>', unsafe_allow_html=True)

    # ── 4. PUNTOS DE FRICCIÓN ──
    st.markdown('<div class="section-header"><div class="section-title">04 · Puntos de Fricción</div></div>', unsafe_allow_html=True)
    if fricciones:
        _top_fr = fricciones[0]
        card_narrativa(
            f"El tema con más rechazo es <strong>{_top_fr['tema']}</strong>, con {_top_fr['n']} comentarios críticos en el período.",
            tono="critico",
        )
    card_explicativa(
        "Qué está ocurriendo: qué temas concentran más comentarios críticos de la ciudadanía.",
        "Cada tarjeta es un tema; el número son sus comentarios críticos y la frase entre comillas es un comentario representativo.",
    )
    if fricciones:
        for fr in fricciones:
            st.markdown(f'<div class="pattern-card pattern-card-critical"><div style="font-family:var(--font-mono);font-size:10px;letter-spacing:1.4px;color:var(--red);font-weight:700;margin-bottom:6px">{fr["tema"].upper()} · {fr["n"]} COMENTARIOS CRÍTICOS</div><p style="font-size:14px;color:var(--fg-primary);line-height:1.55;margin:0">“{fr["cita"]}”</p></div>', unsafe_allow_html=True)
            referencias_por_tema_comentarios(fr["tema"], limit=6, plataforma=plataforma)
    else:
        st.markdown('<div class="status-info">No se detectaron temas con rechazo relevante en este período: la mayoría de los comentarios son neutrales o favorables.</div>', unsafe_allow_html=True)
