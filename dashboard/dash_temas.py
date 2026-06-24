"""UI de Temas Emergentes con banderas de confianza y tono.

Renderiza la tarjeta de Temas Emergentes mostrando, además del tema y su
porcentaje, una bandera de calidad de la clasificación (alta confianza,
clasificación dudosa o posible sarcasmo) y separa en un bloque aparte los
comentarios ambiguos (baja confianza o tono sarcástico) para revisión humana.

Incluye además (Capa 4) un panel de honestidad que resume qué tan confiable es
la clasificación del período: cuántos comentarios se clasificaron con confianza,
cuántos quedaron dudosos o irónicos y cuántos no hablaban de ningún tema.
"""

import streamlit as st

from dashboard.dash_inteligencia import cargar_temas_latentes_detallado
from dashboard.dash_honestidad import resumen_honestidad

# Bandera -> (emoji, texto, color).
_BANDERA_CHIP = {
    "ok": ("🟢", "alta confianza", "#22c55e"),
    "dudosa": ("🟡", "clasificación dudosa", "#eab308"),
    "sarcasmo": ("🟠", "posible sarcasmo", "#f97316"),
}


def _chip(emoji, texto, color):
    return (
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;'
        f'background:var(--bg-elevated);color:{color};border:1px solid {color}44">'
        f'{emoji} {texto}</span>'
    )


def render_temas_emergentes(db_path):
    """Renderiza la sección 06 · Temas Emergentes con banderas y ambiguos."""
    st.markdown(
        '<div class="section-header"><div class="section-title">06 · Temas Emergentes</div>'
        '<div class="section-subtitle">Los asuntos ciudadanos de los que más hablan los '
        'comentarios, con una bandera de qué tan confiable es cada clasificación.</div></div>',
        unsafe_allow_html=True,
    )

    data = cargar_temas_latentes_detallado(db_path)
    temas = data.get("temas", [])
    ambiguos = data.get("ambiguos", [])

    if not temas:
        st.markdown(
            '<div class="status-info">Se requieren al menos 10 comentarios para identificar los temas principales.</div>',
            unsafe_allow_html=True,
        )
        return

    cols = st.columns(min(len(temas), 3))
    for i, t in enumerate(temas[:6]):
        titulo = t.get("label") or "Tema sin clasificar"
        pct = t.get("pct", 0)
        n_com = t.get("doc_count", 0)
        conf = t.get("confianza_promedio", 0) or 0
        bandera = t.get("bandera", "ok")
        n_sarc = t.get("n_sarcasticos", 0)
        n_dud = t.get("n_dudosos", 0)
        ejemplo = (t.get("ejemplo") or "").replace('"', "'")

        emoji, txt, color = _BANDERA_CHIP.get(bandera, _BANDERA_CHIP["ok"])
        chip = _chip(emoji, f"{txt} · {conf * 100:.0f}%", color)

        detalle = []
        if n_sarc:
            detalle.append(f"{n_sarc} con posible sarcasmo")
        if n_dud:
            detalle.append(f"{n_dud} dudosos")
        detalle_html = (
            f'<div style="font-size:10px;color:var(--fg-muted);margin-top:4px">{" · ".join(detalle)}</div>'
            if detalle else ""
        )
        ejemplo_html = (
            f'<div style="font-size:11px;color:var(--fg-secondary);margin-top:6px;font-style:italic">Ejemplo: «{ejemplo}»</div>'
            if ejemplo else ""
        )
        with cols[i % 3]:
            st.markdown(
                f'<div class="panel" style="margin-bottom:8px">'
                f'<div class="panel-head"><div class="panel-title">{titulo}</div>'
                f'<div class="panel-meta">{pct:.0f}% · {n_com:,} com.</div></div>'
                f'<div style="margin-top:6px">{chip}</div>'
                f'{detalle_html}{ejemplo_html}</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<p style="font-size:11px;color:var(--fg-muted);margin-top:6px">'
        'Cada comentario se clasifica en el asunto ciudadano que menciona. La bandera indica '
        'qué tan confiable es esa clasificación: 🟢 alta confianza, 🟡 dudosa, 🟠 posible sarcasmo. '
        'El porcentaje es sobre los comentarios con un asunto identificable, no sobre el total.</p>',
        unsafe_allow_html=True,
    )

    # ── Capa 4 · Honestidad: qué tan confiable es la clasificación ──
    honest = resumen_honestidad(data.get("resumen"))
    if honest:
        nivel_color = {
            "alta": "var(--green)", "media": "var(--amber)", "baja": "var(--red)",
        }.get(honest["nivel_confiabilidad"], "var(--amber)")
        st.markdown(
            f'<div class="panel" style="margin-top:10px">'
            f'<div class="panel-head"><div class="panel-title">CALIDAD DE LA CLASIFICACIÓN</div>'
            f'<div class="panel-meta" style="color:{nivel_color}">CONFIABILIDAD {honest["nivel_confiabilidad"].upper()}</div></div>'
            f'<div class="bar-tri" style="height:14px;border-radius:3px">'
            f'<span class="bar-tri-pos" style="width:{honest["pct_con_confianza"]:.1f}%"></span>'
            f'<span class="bar-tri-neu" style="width:{honest["pct_dudosos"]:.1f}%"></span>'
            f'<span style="display:inline-block;height:100%;background:var(--border);width:{honest["pct_no_aplica"]:.1f}%"></span>'
            f'</div>'
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px">'
            f'<div class="stat-card" style="border-top:2px solid var(--green);padding:12px"><div class="stat-value" style="color:var(--green)">{honest["con_confianza"]:,}</div><div class="stat-label">CON CONFIANZA</div></div>'
            f'<div class="stat-card" style="border-top:2px solid var(--amber);padding:12px"><div class="stat-value" style="color:var(--amber)">{honest["dudosos"]:,}</div><div class="stat-label">DUDOSOS</div></div>'
            f'<div class="stat-card" style="border-top:2px solid var(--fg-muted);padding:12px"><div class="stat-value" style="color:var(--fg-muted)">{honest["no_aplica"]:,}</div><div class="stat-label">SIN TEMA</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="interpretation" style="margin:6px 0 12px 0">'
            f'<div class="interpretation-label">🔎 LÉELO ASÍ</div>'
            f'<div class="interpretation-texto">{honest["lectura"]}</div></div>',
            unsafe_allow_html=True,
        )

    # Separar ambiguos: bloque aparte para revisión humana.
    if ambiguos:
        with st.expander(f"⚠️ {len(ambiguos)} comentarios ambiguos · revisar manualmente"):
            st.markdown(
                '<p style="font-size:11px;color:var(--fg-muted)">La IA marcó estos comentarios como '
                'dudosos o con posible sarcasmo. No se usan como ejemplo de ningún tema; conviene '
                'revisarlos antes de sacar conclusiones.</p>',
                unsafe_allow_html=True,
            )
            for a in ambiguos:
                texto = (a.get("texto") or "").replace('"', "'")
                label = a.get("label_tentativa", "")
                motivo = a.get("motivo", "")
                conf = a.get("confianza", 0) or 0
                tono = a.get("tono", "literal")
                color = "#f97316" if tono == "sarcastico" else "#eab308"
                st.markdown(
                    f'<div style="font-size:12px;padding:8px 10px;margin-bottom:6px;'
                    f'background:var(--bg-elevated);border-radius:6px;border-left:3px solid {color}">'
                    f'«{texto}»'
                    f'<div style="font-size:10px;color:var(--fg-muted);margin-top:4px">'
                    f'{motivo} · tema tentativo: {label} · confianza {conf * 100:.0f}%</div></div>',
                    unsafe_allow_html=True,
                )
