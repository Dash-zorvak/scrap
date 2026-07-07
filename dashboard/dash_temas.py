"""UI de Temas Emergentes con aprobación manual (el sistema sugiere, el usuario aprueba).

Cambios respecto a la versión anterior:
  - Temas englobantes por defecto (tema_taxonomia), no descubiertos libremente.
  - El sistema SUGIERE un tema y una POSTURA (apoyo/crítica/neutral) por
    comentario; el usuario APRUEBA/corrige ambos y eso se guarda
    (tema_aprobaciones). Solo los comentarios aprobados cuentan en las tarjetas.
  - Cada tarjeta de tema se divide en apoyo / crítica / neutral, de modo que una
    crítica no se lea como impulso positivo del tema.
  - Las sugerencias se cachean por comentario durante la sesión y se revisan en
    lotes pequeños: aprobar un comentario NO vuelve a procesar a los demás, así
    el bloque no se congela ni deja de clasificar nuevos comentarios.
"""

import os
import sqlite3

import streamlit as st

from dashboard.dash_fuente import cargar_comentarios_periodo
from dashboard.dash_inteligencia import (
    cargar_temas_universo,
    sugerir_temas_pendientes_cacheado,
)
from dashboard.tema_aprobaciones import guardar_aprobacion, resumen_revision, resumen_cobertura_universo
from dashboard.tema_taxonomia import TEMAS_VISIBLES, TEMA_LABELS

# Cuántos comentarios se preparan para revisión por pantalla. Un lote pequeño
# mantiene la revisión ágil: al aprobar uno, solo se prepara el siguiente, en
# lugar de volver a procesar cientos de comentarios de golpe (lo que congelaba
# el bloque).
try:
    _LOTE_REVISION = int(os.environ.get("TEMAS_REVISION_LOTE", "10"))
except (TypeError, ValueError):
    _LOTE_REVISION = 10

# Opciones del selector de tema: temas englobantes + 'sin tema'.
_OPCIONES = list(TEMAS_VISIBLES) + ["no_aplica"]

# Opciones del selector de postura.
_POSTURA_OPCIONES = ["apoyo", "critica", "neutral"]
_POSTURA_LABELS_UI = {
    "apoyo": "👍 Apoyo",
    "critica": "👎 Crítica",
    "neutral": "➖ Neutral",
}


def _label_opcion(clave):
    if clave == "no_aplica":
        return "— Sin tema / descartar —"
    return TEMA_LABELS.get(clave, clave)


def _label_postura(clave):
    return _POSTURA_LABELS_UI.get(clave, clave)


def _contar_comentarios(db_path, ini=None, fin=None):
    """Total de comentarios de Facebook con mensaje no vacío.

    Si se dan `ini`/`fin`, cuenta solo los del período (mismo criterio de
    fecha que el resto del dashboard, vía dash_fuente.cargar_comentarios_periodo).
    Sin `ini`/`fin`, cuenta el histórico completo (comportamiento anterior).
    """
    try:
        if ini is not None and fin is not None:
            df = cargar_comentarios_periodo(ini, fin, "Facebook", db_path)
            if df is None or df.empty:
                return 0
            mensajes = df["message"].fillna("").astype(str).str.strip()
            return int((mensajes != "").sum())
        conn = sqlite3.connect(db_path)
        n = conn.execute(
            "SELECT COUNT(*) FROM fb_comments "
            "WHERE message IS NOT NULL AND message != ''"
        ).fetchone()[0]
        conn.close()
        return int(n or 0)
    except Exception:
        return 0


def render_temas_emergentes(db_path, ini=None, fin=None):
    st.markdown(
        '<div class="section-header"><div class="section-title">06 · Temas Emergentes</div></div>',
        unsafe_allow_html=True,
    )

    # Aclaración de denominador: ahora incluye IA + aprobaciones manuales
    st.markdown(
        '<div style="font-size:11px;color:var(--fg-muted);margin:-4px 0 10px 0">'
        'Porcentajes calculados sobre comentarios con clasificación (IA + revisión manual), '
        'no sobre el total del período. Para el 100% de los comentarios, ve «Pulso General».</div>',
        unsafe_allow_html=True,
    )

    temas = cargar_temas_universo(db_path, ini=ini, fin=fin)

    if not temas:
        st.markdown(
            '<div class="status-info">Aún no hay comentarios aprobados en ningún tema. '
            'Usa el revisor de abajo para aprobar las sugerencias.</div>',
            unsafe_allow_html=True,
        )
    else:
        cols = st.columns(min(len(temas), 3))
        for i, t in enumerate(temas[:9]):
            titulo = t.get("label") or "Tema"
            pct = t.get("pct", 0)
            n_com = t.get("doc_count", 0)
            n_apoyo = t.get("apoyo", 0)
            n_critica = t.get("critica", 0)
            n_neutral = t.get("neutral", 0)
            pct_critica = t.get("pct_critica", 0)
            ejemplo = (t.get("ejemplo") or "").replace('"', "'")
            ejemplo_html = (
                f'<div style="font-size:11px;color:var(--fg-secondary);margin-top:6px;'
                f'font-style:italic">Ejemplo: «{ejemplo}»</div>'
                if ejemplo else ""
            )
            badge = (
                f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;'
                f'font-weight:700;padding:2px 8px;border-radius:10px;background:var(--bg-elevated);'
                f'color:var(--accent);border:1px solid var(--border)">'
                f'{pct:.0f}% · {n_com:,} comentarios</span>'
            )
            # Desglose de postura: apoyo / crítica / neutral.
            split_html = (
                f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;font-size:11px;font-weight:700">'
                f'<span style="padding:2px 8px;border-radius:10px;background:rgba(34,197,94,0.12);'
                f'color:var(--green)">👍 {n_apoyo:,} apoyo</span>'
                f'<span style="padding:2px 8px;border-radius:10px;background:rgba(239,68,68,0.12);'
                f'color:var(--red)">👎 {n_critica:,} crítica</span>'
                f'<span style="padding:2px 8px;border-radius:10px;background:var(--bg-elevated);'
                f'color:var(--fg-muted)">➖ {n_neutral:,} neutral</span>'
                f'</div>'
            )
            aviso_critica = (
                f'<div style="font-size:11px;color:var(--red);margin-top:6px;font-weight:600">'
                f'⚠️ {pct_critica:.0f}% de este tema es crítica</div>'
                if pct_critica >= 50 else ""
            )
            with cols[i % 3]:
                st.markdown(
                    f'<div class="panel" style="margin-bottom:8px">'
                    f'<div class="panel-head"><div class="panel-title">{titulo}</div></div>'
                    f'<div style="margin-top:6px">{badge}</div>'
                    f'{split_html}{aviso_critica}{ejemplo_html}</div>',
                    unsafe_allow_html=True,
                )

    total = _contar_comentarios(db_path, ini=ini, fin=fin)
    res = resumen_revision(db_path, total_comentarios=total, ini=ini, fin=fin)
    cobertura = resumen_cobertura_universo(db_path, total, ini=ini, fin=fin)
    st.markdown(
        f'<div class="panel" style="margin-top:10px">'
        f'<div class="panel-head"><div class="panel-title">PROGRESO DE REVISIÓN</div>'
        f'<div class="panel-meta">{res["total_aprobaciones"]:,} de {total:,} revisados · '
        f'{cobertura["clasificados"]:,} de {total:,} ya clasificados (IA + manual)</div></div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px">'
        f'<div class="stat-card" style="border-top:2px solid var(--green);padding:12px">'
        f'<div class="stat-value" style="color:var(--green)">{res["aprobados"]:,}</div>'
        f'<div class="stat-label">CON TEMA</div></div>'
        f'<div class="stat-card" style="border-top:2px solid var(--fg-muted);padding:12px">'
        f'<div class="stat-value" style="color:var(--fg-muted)">{res["sin_tema"]:,}</div>'
        f'<div class="stat-label">SIN TEMA</div></div>'
        f'<div class="stat-card" style="border-top:2px solid var(--amber);padding:12px">'
        f'<div class="stat-value" style="color:var(--amber)">{res.get("pendientes", 0):,}</div>'
        f'<div class="stat-label">PENDIENTES</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def render_revisor_temas(db_path):
    with st.expander("✍️ Revisar y aprobar temas — revisa el lote y confirma", expanded=False):
        # Cache de sugerencias por comment_id durante la sesión. Además, se
        # revisa en lotes pequeños (_LOTE_REVISION): al aprobar un comentario
        # solo se prepara el siguiente, en vez de reprocesar todos los
        # pendientes. Así el bloque no se congela ni deja de avanzar.
        cache = st.session_state.setdefault("sugerencias_temas_cache", {})

        _, col_btn = st.columns([3, 1])
        with col_btn:
            if st.button(
                "🔄 Re-sugerir", key="resugerir_temas",
                help="Vuelve a generar las sugerencias usando tus aprobaciones "
                     "recientes como ejemplos.",
            ):
                cache.clear()
                st.rerun()

        with st.spinner("Generando sugerencias de tema y postura con IA…"):
            pendientes = sugerir_temas_pendientes_cacheado(
                db_path, cache=cache, limite=_LOTE_REVISION,
            )
        if not pendientes:
            st.markdown(
                '<div class="status-info">No hay comentarios pendientes de revisión.</div>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            f'<p style="font-size:11px;color:var(--fg-muted)">Se propone un tema y una '
            f'postura para cada comentario (según tus aprobaciones previas). Revisa este lote de '
            f'{len(pendientes)}, ajusta lo que haga falta y aprueba. Cada aprobación afina las '
            f'siguientes sugerencias.</p>',
            unsafe_allow_html=True,
        )

        if st.button("✅ Aprobar todo el lote con la sugerencia", key="aprobar_todos"):
            for p in pendientes:
                guardar_aprobacion(
                    db_path, p["comment_id"], p["sugerencia"],
                    texto=p["texto"], tema_sugerido=p["sugerencia"],
                    tono=p["tono"], confianza=p["confianza"],
                    postura=p.get("postura", "neutral"),
                )
                cache.pop(p["comment_id"], None)
            st.rerun()

        for p in pendientes:
            cid = p["comment_id"]
            texto = (p["texto"] or "").replace('"', "'")
            st.markdown(
                f'<div style="font-size:13px;padding:8px 10px;margin:8px 0 4px 0;'
                f'background:var(--bg-elevated);border-radius:6px;border-left:3px solid var(--accent)">'
                f'«{texto}»<div style="font-size:10px;color:var(--fg-muted);margin-top:4px">'
                f'Sugerencia: {p["sugerencia_label"]} · {p.get("postura_label", "Neutral")}</div></div>',
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                try:
                    idx = _OPCIONES.index(p["sugerencia"])
                except ValueError:
                    idx = _OPCIONES.index("no_aplica")
                sel = st.selectbox(
                    "Tema", _OPCIONES, index=idx, format_func=_label_opcion,
                    key=f"sel_{cid}", label_visibility="collapsed",
                )
            with c2:
                try:
                    idx_p = _POSTURA_OPCIONES.index(p.get("postura", "neutral"))
                except ValueError:
                    idx_p = _POSTURA_OPCIONES.index("neutral")
                sel_postura = st.selectbox(
                    "Postura", _POSTURA_OPCIONES, index=idx_p, format_func=_label_postura,
                    key=f"post_{cid}", label_visibility="collapsed",
                )
            with c3:
                if st.button("Aprobar", key=f"ap_{cid}"):
                    guardar_aprobacion(
                        db_path, cid, sel, texto=p["texto"],
                        tema_sugerido=p["sugerencia"], tono=p["tono"],
                        confianza=p["confianza"], postura=sel_postura,
                    )
                    cache.pop(cid, None)
                    st.rerun()