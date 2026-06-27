"""UI de Temas Emergentes con aprobación manual (la IA sugiere, el usuario aprueba).

Cambios respecto a la versión anterior:
  - Temas englobantes por defecto (tema_taxonomia), no descubiertos libremente.
  - La IA SUGIERE un tema por comentario; el usuario APRUEBA/corrige y eso se
    guarda (tema_aprobaciones). Solo los comentarios aprobados cuentan en las
    tarjetas. El sistema aprende de las aprobaciones (few-shot).
  - Se elimina el semáforo de confianza. El badge de cada tema ahora muestra el
    porcentaje y la cantidad de comentarios: '%·N comentarios'.
  - Las sugerencias de la IA se cachean por comentario durante la sesión: aprobar
    un comentario ya no reclasifica a los demás (el bloque no se congela).
"""

import sqlite3

import streamlit as st

from dashboard.dash_inteligencia import (
    cargar_temas_aprobados,
    sugerir_temas_pendientes_cacheado,
)
from dashboard.tema_aprobaciones import guardar_aprobacion, resumen_revision
from dashboard.tema_taxonomia import TEMAS_VISIBLES, TEMA_LABELS

# Opciones del selector: temas englobantes + 'sin tema'.
_OPCIONES = list(TEMAS_VISIBLES) + ["no_aplica"]


def _label_opcion(clave):
    if clave == "no_aplica":
        return "— Sin tema / descartar —"
    return TEMA_LABELS.get(clave, clave)


def _contar_comentarios(db_path):
    try:
        conn = sqlite3.connect(db_path)
        n = conn.execute(
            "SELECT COUNT(*) FROM fb_comments "
            "WHERE message IS NOT NULL AND message != ''"
        ).fetchone()[0]
        conn.close()
        return int(n or 0)
    except Exception:
        return 0


def render_temas_emergentes(db_path):
    st.markdown(
        '<div class="section-header"><div class="section-title">06 · Temas Emergentes</div>'
        '<div class="section-subtitle">Temas englobantes definidos por defecto. La IA sugiere '
        'en qué tema va cada comentario y tú lo apruebas; solo lo aprobado cuenta.</div></div>',
        unsafe_allow_html=True,
    )

    temas = cargar_temas_aprobados(db_path)

    if not temas:
        st.markdown(
            '<div class="status-info">Aún no hay comentarios aprobados en ningún tema. '
            'Usa el revisor de abajo para aprobar las sugerencias de la IA.</div>',
            unsafe_allow_html=True,
        )
    else:
        cols = st.columns(min(len(temas), 3))
        for i, t in enumerate(temas[:9]):
            titulo = t.get("label") or "Tema"
            pct = t.get("pct", 0)
            n_com = t.get("doc_count", 0)
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
            with cols[i % 3]:
                st.markdown(
                    f'<div class="panel" style="margin-bottom:8px">'
                    f'<div class="panel-head"><div class="panel-title">{titulo}</div></div>'
                    f'<div style="margin-top:6px">{badge}</div>'
                    f'{ejemplo_html}</div>',
                    unsafe_allow_html=True,
                )
        st.markdown(
            '<p style="font-size:11px;color:var(--fg-muted);margin-top:6px">'
            'El porcentaje es sobre los comentarios que ya aprobaste con un tema, no sobre el total.</p>',
            unsafe_allow_html=True,
        )

    total = _contar_comentarios(db_path)
    res = resumen_revision(db_path, total_comentarios=total)
    st.markdown(
        f'<div class="panel" style="margin-top:10px">'
        f'<div class="panel-head"><div class="panel-title">PROGRESO DE REVISIÓN</div>'
        f'<div class="panel-meta">{res["total_aprobaciones"]:,} de {total:,} revisados</div></div>'
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

    _render_revisor(db_path)


def _render_revisor(db_path):
    with st.expander("✍️ Revisar y aprobar temas — la IA sugiere, tú confirmas", expanded=False):
        # Cache de sugerencias por comment_id durante la sesión. Sin esto, cada
        # aprobación dispara un rerun que reclasificaba TODOS los pendientes con
        # el LLM, dejando el bloque congelado mientras cargaba. Con el cache,
        # aprobar un comentario no vuelve a llamar al LLM por los demás.
        cache = st.session_state.setdefault("sugerencias_temas_cache", {})

        _, col_btn = st.columns([3, 1])
        with col_btn:
            if st.button(
                "🔄 Re-sugerir", key="resugerir_temas",
                help="Vuelve a pedir sugerencias a la IA usando tus aprobaciones "
                     "recientes como ejemplos.",
            ):
                cache.clear()
                st.rerun()

        pendientes = sugerir_temas_pendientes_cacheado(db_path, cache=cache)
        if not pendientes:
            st.markdown(
                '<div class="status-info">No hay comentarios pendientes de revisión.</div>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            '<p style="font-size:11px;color:var(--fg-muted)">La IA propone un tema para cada '
            'comentario (según tus aprobaciones previas). Ajusta el tema si hace falta y aprueba. '
            'Cada aprobación enseña al sistema para que a futuro sugiera mejor.</p>',
            unsafe_allow_html=True,
        )

        if st.button("✅ Aprobar todos con la sugerencia de la IA", key="aprobar_todos"):
            for p in pendientes:
                guardar_aprobacion(
                    db_path, p["comment_id"], p["sugerencia"],
                    texto=p["texto"], tema_sugerido=p["sugerencia"],
                    tono=p["tono"], confianza=p["confianza"],
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
                f'Sugerencia IA: {p["sugerencia_label"]}</div></div>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([3, 1])
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
                if st.button("Aprobar", key=f"ap_{cid}"):
                    guardar_aprobacion(
                        db_path, cid, sel, texto=p["texto"],
                        tema_sugerido=p["sugerencia"], tono=p["tono"],
                        confianza=p["confianza"],
                    )
                    cache.pop(cid, None)
                    st.rerun()
