"""Bloque IV — Memoria e Inteligencia Aplicada.

Estaciones (10): Eco Histórico, Lección Aprendida, Brecha Percepción-Realidad,
Temas Emergentes, Temas en Extinción, Contexto No Visible, Correlación
Contenido-Reacción, Comparativa Sectorial, Proyección de Escenario y
Recomendación Estratégica. Se eliminó la antigua estación "Fragilidad de la
Narrativa" (fuera del índice de 20). Recibe `periodo` y `plataforma`.
"""

import streamlit as st
import pandas as pd

from config import FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB
from dashboard.dash_metrics import (
    safe_query,
    filtrar_por_periodo_plataforma,
    cargar_sentimiento_fb,
    cargar_fb_engagement,
    cargar_tk_engagement,
    cargar_externos,
    calcular_contagio_emocional,
    generar_narrativa_ia,
)
from dashboard.dash_memoria import clasificar_evolucion_temas, comparar_sectorial
from dashboard.dash_ui import _page_head, card_explicativa, referencias_publicaciones


def _b4_header(num: int, titulo: str, subtitulo: str = ""):
    st.markdown(
        f'<div class="memo-section"><div class="memo-section-number">{num:02d}</div>'
        f'<div class="memo-section-title">{titulo}</div></div>',
        unsafe_allow_html=True,
    )


def _b4_card_ia(num: int, titulo: str, tipo: str, ctx: dict):
    _b4_header(num, titulo)
    with st.spinner(f"Generando {titulo}…"):
        narrativa = generar_narrativa_ia(tipo, ctx)
    st.markdown(f'<p class="memo-body">{narrativa}</p>', unsafe_allow_html=True)


def render_bloque4_inteligencia(periodo, plataforma):
    _page_head(
        "MEMORÁNDUM / INTELIGENCIA APLICADA",
        "Memo estratégico para toma de decisiones",
        "Síntesis ejecutiva en formato briefing: eco histórico, brechas percepción-realidad, temas emergentes, proyección y recomendación estratégica.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    card_explicativa(
        "Un resumen estratégico que conecta lo que pasa hoy con la memoria de casos anteriores y proyecta lo que viene.",
        "Léelo como un briefing: cada bloque numerado es una conclusión. Los textos largos los redacta la IA a partir de los datos del período; las listas salen directo de los comentarios y publicaciones.",
        "Las secciones de IA son interpretaciones asistidas; contéjalas con las cifras de los bloques anteriores.",
    )

    st.markdown("""
    <div class="memo-container">
        <div class="memo-header">
            <div class="memo-title">MEMORÁNDUM EJECUTIVO</div>
            <div class="memo-ref">PANEL·SANTA ANA · Inteligencia Ciudadana · Análisis Estratégico</div>
        </div>
    """, unsafe_allow_html=True)

    df_sent = cargar_sentimiento_fb(FACEBOOK_DB)
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB, FACEBOOK_DB)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    score = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0
    total_eng = (int(df_fb['engagement_total'].sum()) if not df_fb.empty else 0) + (int(df_tk['engagement_total'].sum()) if not df_tk.empty else 0)

    ctx = {
        "score": round(float(score), 3),
        "pct_negativo": round(float(pct_neg), 1),
        "pct_positivo": round(float(pct_pos), 1),
        "indice_enojo": round(float(enojo), 3),
        "interacciones": int(total_eng),
        "periodo": periodo,
    }

    _b4_card_ia(1, "Eco Histórico", "eco_historico", ctx)
    _b4_card_ia(2, "Lección Aprendida", "leccion", ctx)
    _b4_card_ia(3, "Brecha Percepción-Realidad", "brecha", ctx)

    # ── 04 + 05 Temas (emergentes / en auge / en declive / en extinción) ──
    evol = None
    temas_disponibles = False
    df_cat = safe_query(
        "SELECT item_id, categoria_nombre, created_time FROM fb_posts "
        "LEFT JOIN post_categorias ON fb_posts.post_id = post_categorias.item_id",
        FACEBOOK_DB,
    )
    if not df_cat.empty and 'created_time' in df_cat.columns and 'categoria_nombre' in df_cat.columns:
        df_cat['created_time'] = pd.to_datetime(df_cat['created_time'], errors='coerce')
        df_cat['semana'] = df_cat['created_time'].dt.to_period('W').dt.start_time
        df_cat = df_cat.dropna(subset=['categoria_nombre', 'semana'])
        if not df_cat.empty:
            temas_disponibles = True
            ultima_sem = df_cat['semana'].max()
            sem_actual = df_cat[df_cat['semana'] == ultima_sem]
            sem_prev = df_cat[df_cat['semana'] == ultima_sem - pd.Timedelta(days=7)]
            evol = clasificar_evolucion_temas(
                sem_actual['categoria_nombre'].value_counts().to_dict(),
                sem_prev['categoria_nombre'].value_counts().to_dict(),
            )

    _b4_header(4, "Temas Emergentes")
    card_explicativa(
        "Temas que aparecen por primera vez o que ganan fuerza esta semana frente a la anterior.",
        "El signo + marca temas nuevos; la flecha ▲ marca temas que crecen. El número indica menciones o el cambio porcentual.",
    )
    if temas_disponibles and evol is not None:
        filas = []
        for it in evol['emergentes'][:6]:
            filas.append(f'<div class="memo-item memo-item-positivo">+ {it["tema"]} <span style="color:var(--fg-muted)">· nuevo, {it["n_actual"]} menciones</span></div>')
        for it in evol['en_auge'][:4]:
            filas.append(f'<div class="memo-item memo-item-positivo">▲ {it["tema"]} <span style="color:var(--fg-muted)">· ganando fuerza, {it["cambio_pct"]:+.0f}% ({it["n_previo"]}→{it["n_actual"]})</span></div>')
        if filas:
            st.markdown("".join(filas), unsafe_allow_html=True)
        else:
            st.markdown('<div class="memo-item memo-item-neutral">Sin temas nuevos ni en alza esta semana.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Clasificación de temas no disponible para este período.</div>', unsafe_allow_html=True)

    _b4_header(5, "Temas en Extinción")
    card_explicativa(
        "Temas que dejaron de mencionarse o que pierden fuerza frente a la semana anterior.",
        "El signo - marca temas que desaparecieron; la flecha ▼ marca temas que caen. El número indica el descenso.",
    )
    if temas_disponibles and evol is not None:
        filas = []
        for it in evol['en_extincion'][:6]:
            filas.append(f'<div class="memo-item memo-item-negativo">- {it["tema"]} <span style="color:var(--fg-muted)">· desapareció, {it["n_previo"]} → 0</span></div>')
        for it in evol['en_declive'][:4]:
            filas.append(f'<div class="memo-item memo-item-negativo">▼ {it["tema"]} <span style="color:var(--fg-muted)">· perdiendo tracción, {it["cambio_pct"]:+.0f}% ({it["n_previo"]}→{it["n_actual"]})</span></div>')
        if filas:
            st.markdown("".join(filas), unsafe_allow_html=True)
        else:
            st.markdown('<div class="memo-item memo-item-neutral">Ningún tema perdió tracción esta semana.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Clasificación de temas no disponible para este período.</div>', unsafe_allow_html=True)

    _b4_card_ia(6, "Contexto No Visible", "contexto", ctx)

    _b4_header(7, "Correlación Contenido/Reacción")
    card_explicativa(
        "Si lo que publican las páginas (su tono) coincide con cómo reacciona la gente.",
        "Resonancia positiva = un mensaje positivo recibe reacción positiva. Rechazo = un mensaje positivo recibe rechazo. Distorsión alta = mayor desajuste entre mensaje y reacción.",
    )
    df_posts, conteo_tipos, distorsion_alta, _por_semana = calcular_contagio_emocional()
    if not df_posts.empty:
        resonancia_pos = int(conteo_tipos.get('resonancia_positiva', 0))
        rechazo = int(conteo_tipos.get('rechazo_a_positivo', 0))
        total_p = len(df_posts)
        st.markdown(
            f'<div class="memo-item memo-item-positivo">Resonancia positiva: {resonancia_pos}/{total_p}</div>'
            f'<div class="memo-item memo-item-negativo">Rechazo a positivo: {rechazo}/{total_p}</div>',
            unsafe_allow_html=True,
        )
        if not distorsion_alta.empty:
            st.markdown('<div class="memo-section-number" style="margin-top:8px">DISTORSIÓN ALTA</div>', unsafe_allow_html=True)
            for _, r in distorsion_alta.head(3).iterrows():
                msg = str(r.get('message', '') or '')[:100]
                st.markdown(
                    f'<div class="memo-item memo-item-negativo">\"{msg}\"</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Sin datos suficientes para correlación contenido-reacción.</div>', unsafe_allow_html=True)

    _b4_header(8, "Comparativa Sectorial")
    card_explicativa(
        "Cómo se ve el tono de tus páginas frente al tono de fuentes externas (medios y otras páginas).",
        "Compara el índice de tu conversación con el de las fuentes externas: si el externo es más crítico, hay riesgo reputacional fuera de tus canales.",
    )
    df_ext = cargar_externos(EXTERNOS_DB)
    comp = None
    if df_ext is not None and not df_ext.empty:
        col_fuente = 'page_name' if 'page_name' in df_ext.columns else ('source' if 'source' in df_ext.columns else None)
        n_fuentes = int(df_ext[col_fuente].nunique()) if col_fuente else 0
        n_menciones = len(df_ext)
        score_ext = float(df_ext['score_sentimiento'].mean()) if 'score_sentimiento' in df_ext.columns else 0.0
        comp = comparar_sectorial(score, score_ext, n_fuentes, n_menciones)
    if comp:
        tono_color = {"favorable": "var(--green)", "mixto": "var(--amber)", "crítico": "var(--red)"}
        c_int = tono_color.get(comp['tono_interno'], 'var(--amber)')
        c_ext = tono_color.get(comp['tono_externo'], 'var(--amber)')
        st.markdown(
            f'<div class="memo-item" style="border-left-color:{c_int}">Tus páginas: tono <strong style="color:{c_int}">{comp["tono_interno"]}</strong> (índice {comp["score_interno"]:+.2f})</div>'
            f'<div class="memo-item" style="border-left-color:{c_ext}">Fuentes externas: tono <strong style="color:{c_ext}">{comp["tono_externo"]}</strong> (índice {comp["score_externo"]:+.2f}) · {comp["n_fuentes"]} fuentes, {comp["n_menciones"]} menciones</div>'
            f'<div class="memo-item memo-item-neutral">{comp["lectura"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Aún no hay menciones en fuentes externas para comparar con la conversación propia.</div>', unsafe_allow_html=True)

    _b4_card_ia(9, "Proyección de Escenario", "proyeccion", ctx)
    _b4_card_ia(10, "Recomendación Estratégica", "recomendacion", ctx)
    st.markdown('</div>', unsafe_allow_html=True)
    referencias_publicaciones(limit=10, titulo="PUBLICACIONES QUE SUSTENTAN EL MEMO")
