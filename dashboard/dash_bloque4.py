"""Bloque IV — Memorándum Estratégico.

Diez estaciones tipo briefing: Eco Histórico, Lección Aprendida, Brecha
Percepción-Realidad, Temas Emergentes, Temas en Extinción, Contexto No Visible,
Correlación Contenido-Reacción, Comparativa Sectorial, Proyección de Escenario y
Recomendación Estratégica. Todo se calcula sobre la fuente única (dash_fuente)
filtrada por el periodo y la plataforma seleccionados. Las conclusiones
redactadas responden, en lenguaje del alcalde, qué ocurre, por qué y qué hacer.
El usuario no ve cómo se generó el análisis.

Filtro por plataforma:
  - Comentarios, distribución de sentimiento y KPIs derivados respetan el filtro
    (Facebook / TikTok / Ambas) a través de dash_fuente.
  - El índice de enojo / score emocional se delega en dash_emocional.metricas_
    emocionales, que usa un modelo distinto por plataforma (ver allí la
    justificación): Facebook a partir de reacciones tipadas y TikTok a partir
    del sentimiento de los comentarios; "Ambas" pondera por volumen.
  - La Correlación Contenido-Reacción depende de reacciones tipadas de Facebook;
    no aplica a la vista exclusiva de TikTok y se sustituye por una nota.
"""

import pandas as pd
import streamlit as st

from config import FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB
from dashboard.dash_metrics import (
    cargar_fb_engagement,
    cargar_tk_engagement,
    cargar_externos,
    calcular_contagio_emocional,
)
from dashboard.dash_emocional import metricas_emocionales
from dashboard.dash_memoria import clasificar_evolucion_temas, comparar_sectorial
from dashboard.dash_periodos import rango_periodo, filtrar_por_fecha, etiqueta_rango
from dashboard.dash_fuente import (
    cargar_comentarios_periodo,
    distribucion_sentimiento,
    clasificar_comentario,
)
from dashboard.dash_narrativa import generar_narrativa
from dashboard.dash_ui import _page_head, card_explicativa, referencias_publicaciones

_IGNORAR_TEMAS = {"", "no_aplica", "sin_tema", "general"}


def _filtra_fecha(df, col, ini, fin):
    if df is None or df.empty or col not in df.columns:
        return df if df is not None else pd.DataFrame()
    return filtrar_por_fecha(df, col, ini, fin)


def _temas_por_tono(df, top=5):
    """Top temas con más comentarios favorables y con más comentarios críticos."""
    if df is None or df.empty or "topic_category" not in df.columns:
        return [], []
    d = df.copy()
    d["_clase"] = d.apply(clasificar_comentario, axis=1)
    d["_tema"] = d["topic_category"].fillna("").astype(str).str.strip()
    d = d[~d["_tema"].str.lower().isin(_IGNORAR_TEMAS)]
    if d.empty:
        return [], []
    fav = d[d["_clase"] == "favorable"]["_tema"].value_counts().head(top)
    crit = d[d["_clase"] == "critico"]["_tema"].value_counts().head(top)
    return (
        [{"tema": k, "comentarios_favorables": int(v)} for k, v in fav.items()],
        [{"tema": k, "comentarios_criticos": int(v)} for k, v in crit.items()],
    )


def _conteo_temas(df):
    if df is None or df.empty or "topic_category" not in df.columns:
        return {}
    s = df["topic_category"].fillna("").astype(str).str.strip()
    s = s[~s.str.lower().isin(_IGNORAR_TEMAS)]
    return s.value_counts().to_dict()


def _b4_header(num, titulo):
    st.markdown(
        f'<div class="memo-section"><div class="memo-section-number">{num:02d}</div>'
        f'<div class="memo-section-title">{titulo}</div></div>',
        unsafe_allow_html=True,
    )


def _b4_card(num, titulo, tipo, ctx):
    _b4_header(num, titulo)
    with st.spinner(f"Preparando {titulo}…"):
        narrativa = generar_narrativa(tipo, ctx)
    st.markdown(f'<p class="memo-body">{narrativa}</p>', unsafe_allow_html=True)


def render_bloque4_inteligencia(periodo, plataforma):
    ref = st.session_state.get("fecha_ref")
    ini, fin = rango_periodo(
        periodo, ref,
        st.session_state.get("fecha_desde"),
        st.session_state.get("fecha_hasta"),
    )

    _page_head(
        "MEMORÁNDUM / SÍNTESIS ESTRATÉGICA",
        "Memo estratégico para la toma de decisiones",
        "Briefing ejecutivo: qué ocurre, por qué y qué conviene hacer. Cada punto se apoya en las cifras del período seleccionado.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> {etiqueta_rango(ini, fin).upper()} <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    st.markdown("""
    <div class="memo-container">
        <div class="memo-header">
            <div class="memo-title">MEMORÁNDUM EJECUTIVO</div>
            <div class="memo-ref">PANEL·SANTA ANA · Inteligencia Ciudadana · Síntesis Estratégica</div>
        </div>
    """, unsafe_allow_html=True)

    plat = str(plataforma or "").lower()

    # ── Fuente única: comentarios del periodo (respeta plataforma) ──
    df_coment = cargar_comentarios_periodo(ini, fin, plataforma)
    dist = distribucion_sentimiento(df_coment, plataforma)

    # Periodo anterior de igual duración (para emergentes / extinción)
    try:
        dur = fin - ini
        df_prev = cargar_comentarios_periodo(ini - dur, ini, plataforma)
    except Exception:
        df_prev = pd.DataFrame()

    # Engagement total: solo de la(s) plataforma(s) activa(s), nunca se mezcla
    # cuando el filtro no corresponde.
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB) if "tik" not in plat else pd.DataFrame()
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB, FACEBOOK_DB) if plat != "facebook" else pd.DataFrame()
    fb_p = _filtra_fecha(df_fb_raw, "created_time", ini, fin)
    tk_p = _filtra_fecha(df_tk_raw, "created_at", ini, fin)
    total_eng = (int(fb_p["engagement_total"].sum()) if not fb_p.empty and "engagement_total" in fb_p.columns else 0)
    total_eng += (int(tk_p["engagement_total"].sum()) if not tk_p.empty and "engagement_total" in tk_p.columns else 0)

    # Índice de enojo / score emocional: delegado al modelo desacoplado por
    # plataforma (dash_emocional.metricas_emocionales). Facebook usa reacciones
    # tipadas; TikTok usa el sentimiento de los comentarios; "Ambas" pondera por
    # volumen. NO se copia el algoritmo de FB a TikTok porque conceptualmente no
    # aplica (TikTok no expone reacciones tipadas).
    enojo = float(metricas_emocionales(plataforma, ini, fin).get("indice_enojo", 0) or 0)

    temas_fav, temas_crit = _temas_por_tono(df_coment)
    score_interno = round((dist["pct_favorable"] - dist["pct_critico"]) / 100.0, 3)

    # Evolución de temas (periodo actual vs anterior) — fuente única
    evol = clasificar_evolucion_temas(_conteo_temas(df_coment), _conteo_temas(df_prev))

    # Correlación contenido-reacción (filtrada al periodo). Depende de las
    # reacciones tipadas de Facebook; no aplica a la vista exclusiva de TikTok.
    if plat == "tiktok":
        df_posts = None
    else:
        df_posts, _conteo_hist, _dist_hist, _ = calcular_contagio_emocional()
        if df_posts is not None and not df_posts.empty:
            df_posts = _filtra_fecha(df_posts, "created_time", ini, fin)
    if df_posts is not None and not df_posts.empty and "tipo_contagio" in df_posts.columns:
        conteo_tipos = df_posts["tipo_contagio"].value_counts().to_dict()
        total_p = int(len(df_posts))
        reson_pos = int(conteo_tipos.get("resonancia_positiva", 0))
        rechazo = int(conteo_tipos.get("rechazo_a_positivo", 0))
        reson_neg = int(conteo_tipos.get("resonancia_negativa", 0))
        peores = df_posts[df_posts["tipo_contagio"] == "rechazo_a_positivo"].nlargest(3, "distorsion") if "distorsion" in df_posts.columns else pd.DataFrame()
    else:
        total_p = 0; reson_pos = 0; rechazo = 0; reson_neg = 0; peores = pd.DataFrame()

    correlacion_ctx = {
        "publicaciones_analizadas": total_p,
        "conectaron_bien": reson_pos,
        "rechazo_pese_a_mensaje_positivo": rechazo,
        "resonancia_negativa": reson_neg,
    }

    ctx = {
        "periodo": periodo,
        "rango": etiqueta_rango(ini, fin),
        "comentarios_analizados": dist["n_total"],
        "pct_favorable": dist["pct_favorable"],
        "pct_neutral": dist["pct_neutral"],
        "pct_critico": dist["pct_critico"],
        "interacciones_totales": int(total_eng),
        "indice_enojo": round(enojo, 4),
        "temas_que_funcionaron": temas_fav,
        "temas_con_rechazo": temas_crit,
        "temas_emergentes": [it.get("tema") for it in evol.get("emergentes", [])[:5]],
        "temas_en_extincion": [it.get("tema") for it in evol.get("en_extincion", [])[:5]],
        "correlacion": correlacion_ctx,
    }

    _b4_card(1, "Eco Histórico", "eco_historico", ctx)
    _b4_card(2, "Lección Aprendida", "leccion", ctx)
    _b4_card(3, "Brecha Percepción-Realidad", "brecha", ctx)

    # ── 04 Temas Emergentes ──
    _b4_header(4, "Temas Emergentes")
    card_explicativa(
        "Qué está ocurriendo: temas que aparecen por primera vez o que ganan fuerza frente al período anterior.",
        "El signo + marca temas nuevos; la flecha ▲ marca temas que crecen. El número indica menciones o el cambio.",
    )
    filas = []
    for it in evol.get("emergentes", [])[:6]:
        filas.append(f'<div class="memo-item memo-item-positivo">+ {it["tema"]} <span style="color:var(--fg-muted)">· nuevo, {it["n_actual"]} menciones</span></div>')
    for it in evol.get("en_auge", [])[:4]:
        filas.append(f'<div class="memo-item memo-item-positivo">▲ {it["tema"]} <span style="color:var(--fg-muted)">· ganando fuerza, {it["cambio_pct"]:+.0f}% ({it["n_previo"]}→{it["n_actual"]})</span></div>')
    if filas:
        st.markdown("".join(filas), unsafe_allow_html=True)
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Sin temas nuevos ni en alza frente al período anterior.</div>', unsafe_allow_html=True)

    # ── 05 Temas en Extinción ──
    _b4_header(5, "Temas en Extinción")
    card_explicativa(
        "Qué está ocurriendo: temas que dejaron de mencionarse o que pierden fuerza frente al período anterior.",
        "El signo - marca temas que desaparecieron; la flecha ▼ marca temas que caen. El número indica el descenso.",
    )
    filas = []
    for it in evol.get("en_extincion", [])[:6]:
        filas.append(f'<div class="memo-item memo-item-negativo">- {it["tema"]} <span style="color:var(--fg-muted)">· dejó de mencionarse, {it["n_previo"]} → 0</span></div>')
    for it in evol.get("en_declive", [])[:4]:
        filas.append(f'<div class="memo-item memo-item-negativo">▼ {it["tema"]} <span style="color:var(--fg-muted)">· perdiendo fuerza, {it["cambio_pct"]:+.0f}% ({it["n_previo"]}→{it["n_actual"]})</span></div>')
    if filas:
        st.markdown("".join(filas), unsafe_allow_html=True)
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Ningún tema perdió fuerza frente al período anterior.</div>', unsafe_allow_html=True)

    _b4_card(6, "Contexto No Visible", "contexto", ctx)

    # ── 07 Correlación Contenido-Reacción (traducida) ──
    _b4_header(7, "Correlación Contenido-Reacción")
    card_explicativa(
        "Qué está ocurriendo: si lo que publican las páginas conecta con cómo reacciona la gente.",
        "Se cuenta cuántas publicaciones lograron una buena respuesta y cuántas generaron rechazo a pesar de un mensaje positivo.",
    )
    if total_p > 0:
        pct_bien = (reson_pos / total_p * 100) if total_p else 0
        pct_rech = (rechazo / total_p * 100) if total_p else 0
        st.markdown(
            f'<div class="memo-item memo-item-positivo">De las {total_p} publicaciones del período, {reson_pos} conectaron bien: su mensaje positivo recibió una reacción positiva de la ciudadanía ({pct_bien:.0f}%).</div>'
            f'<div class="memo-item memo-item-negativo">{rechazo} publicaciones generaron rechazo pese a tener un mensaje positivo ({pct_rech:.0f}%): el mensaje no conectó con la gente.</div>',
            unsafe_allow_html=True,
        )
        _b4_card_correlacion = generar_narrativa("correlacion", ctx)
        st.markdown(f'<p class="memo-body">{_b4_card_correlacion}</p>', unsafe_allow_html=True)
        if peores is not None and not peores.empty:
            st.markdown('<div class="memo-section-number" style="margin-top:8px">PUBLICACIONES QUE NO CONECTARON</div>', unsafe_allow_html=True)
            for _, r in peores.iterrows():
                msg = str(r.get("message", "") or "")[:120]
                st.markdown(f'<div class="memo-item memo-item-negativo">“{msg}”</div>', unsafe_allow_html=True)
    elif plat == "tiktok":
        st.markdown('<div class="memo-item memo-item-neutral">La correlación contenido-reacción se basa en las reacciones tipadas de Facebook (me encanta, me enoja, etc.), que TikTok no expone. En la vista exclusiva de TikTok esta estación no aplica; el clima emocional de TikTok se mide en el índice de enojo/score a partir del sentimiento de los comentarios.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="memo-item memo-item-neutral">No hay suficientes publicaciones en el período para evaluar la conexión entre contenido y reacción.</div>', unsafe_allow_html=True)

    # ── 08 Comparativa Sectorial (sin cambios de fondo) ──
    _b4_header(8, "Comparativa Sectorial")
    card_explicativa(
        "Qué está ocurriendo: cómo se ve el tono de tus páginas frente al de fuentes externas (medios y otras páginas).",
        "Si el tono externo es más crítico que el propio, hay riesgo reputacional fuera de tus canales.",
    )
    df_ext = cargar_externos(EXTERNOS_DB)
    comp = None
    if df_ext is not None and not df_ext.empty:
        col_fuente = 'page_name' if 'page_name' in df_ext.columns else ('source' if 'source' in df_ext.columns else None)
        n_fuentes = int(df_ext[col_fuente].nunique()) if col_fuente else 0
        n_menciones = len(df_ext)
        score_ext = float(df_ext['score_sentimiento'].mean()) if 'score_sentimiento' in df_ext.columns else 0.0
        comp = comparar_sectorial(score_interno, score_ext, n_fuentes, n_menciones)
    if comp:
        tono_color = {"favorable": "var(--green)", "mixto": "var(--amber)", "crítico": "var(--red)"}
        c_int = tono_color.get(comp['tono_interno'], 'var(--amber)')
        c_ext = tono_color.get(comp['tono_externo'], 'var(--amber)')
        st.markdown(
            f'<div class="memo-item" style="border-left-color:{c_int}">Tus páginas: tono <strong style="color:{c_int}">{comp["tono_interno"]}</strong></div>'
            f'<div class="memo-item" style="border-left-color:{c_ext}">Fuentes externas: tono <strong style="color:{c_ext}">{comp["tono_externo"]}</strong> · {comp["n_fuentes"]} fuentes, {comp["n_menciones"]} menciones</div>'
            f'<div class="memo-item memo-item-neutral">{comp["lectura"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Aún no hay menciones en fuentes externas para comparar con la conversación propia.</div>', unsafe_allow_html=True)

    _b4_card(9, "Proyección de Escenario", "proyeccion", ctx)
    _b4_card(10, "Recomendación Estratégica", "recomendacion", ctx)
    st.markdown('</div>', unsafe_allow_html=True)
    referencias_publicaciones(limit=10, titulo="Post bibliográficos", plataforma=plataforma)
