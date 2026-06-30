"""Editor de base de datos para el analista (dentro del panel de carga, SOLO LOCAL).

Dos herramientas:
  1) Corregir registros ya guardados (Facebook y TikTok) — p.ej. cambiar el
     autor de un post de «Alcaldía de Santa Ana» a «Gustavo Acevedo», ajustar
     texto/descripción, fecha, métricas o enlace; también eliminar un registro.
  2) Administrar la «medalla» del período — ver la sugerencia automática
     (mayor tracción positiva), aprobarla manualmente y marcar las réplicas en
     páginas externas que saldrán en el informe PDF del dashboard del alcalde.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import FACEBOOK_DB, FB_PAGES_OFICIALES, TK_ACCOUNTS  # type: ignore
except Exception:
    FACEBOOK_DB = os.getenv("FACEBOOK_DB", "facebook.db")
    FB_PAGES_OFICIALES = ["Alcaldía de Santa Ana", "Gustavo Acevedo"]
    TK_ACCOUNTS = {1: "Alcaldía de Santa Ana", 3: "Gustavo Acevedo"}

import medalla_store  # noqa: E402
import medalla_seleccion  # noqa: E402
from capturas_store import borrar_capturas  # noqa: E402
from dash_periodos import OPCIONES_PERIODO, etiqueta_rango  # noqa: E402
import db_edits  # noqa: E402

try:
    from src.storage.db import LocalStorage  # type: ignore
except Exception:
    from storage.db import LocalStorage  # type: ignore


# Campos de reacciones editables (clave en BD, etiqueta visible).
REACCIONES = [
    ("likes_count", "Likes"),
    ("loves_count", "Me encanta"),
    ("cares_count", "Me importa"),
    ("hahas_count", "Me divierte"),
    ("wows_count", "Me asombra"),
    ("sads_count", "Me entristece"),
    ("angrys_count", "Me enoja"),
]


def _store():
    return LocalStorage(db_path=FACEBOOK_DB)


def _etiqueta_post(p):
    fecha = str(p.get("created_time") or "")[:10]
    msg = (p.get("message") or "").strip().replace("\n", " ")
    if len(msg) > 60:
        msg = msg[:57] + "…"
    autor = p.get("page_name") or "—"
    return f"{autor} · {fecha} · {msg or '(sin texto)'}"


def _etiqueta_video_tiktok(v):
    fecha = str(v.get("created_at") or "")[:10]
    desc = (v.get("description") or "").strip().replace("\n", " ")
    if len(desc) > 60:
        desc = desc[:57] + "…"
    cuenta = TK_ACCOUNTS.get(v.get("account_id"), "—")
    return f"{cuenta} · {fecha} · {desc or '(sin descripción)'}"


# ══════════════════════════════════════════════
# Herramienta 1 — corregir registros
# ══════════════════════════════════════════════

def _editor_posts():
    plataforma = st.radio(
        "Plataforma", ["Facebook", "TikTok"], horizontal=True, key="edit_plataforma",
    )
    if plataforma == "TikTok":
        _editor_posts_tiktok()
    else:
        _editor_posts_fb()


def _editor_posts_fb():
    store = _store()
    try:
        posts = store.get_fb_posts(limit=500, offset=0) or []
    except Exception as e:
        st.error(f"No se pudieron leer los posts: {e}")
        return
    if not posts:
        st.info("Aún no hay publicaciones de Facebook guardadas para editar.")
        return

    filtro = st.text_input(
        "Buscar (texto o página)", "", key="edit_filtro",
        placeholder="Escribe para filtrar por autor o contenido…",
    ).strip().lower()
    if filtro:
        posts = [
            p for p in posts
            if filtro in (p.get("message") or "").lower()
            or filtro in (p.get("page_name") or "").lower()
        ]
    if not posts:
        st.warning("Ningún registro coincide con el filtro.")
        return

    opciones = {_etiqueta_post(p): p for p in posts}
    elegido = st.selectbox("Registro a corregir", list(opciones.keys()), key="edit_sel")
    post = opciones[elegido]
    pid = post.get("post_id")

    with st.form(f"form_edit_{pid}"):
        st.caption(f"ID: {pid}")
        # Autor / página: caso principal de corrección (Alcaldía ↔ Alcalde).
        actual = post.get("page_name") or ""
        opciones_pagina = list(dict.fromkeys(FB_PAGES_OFICIALES + ([actual] if actual else [])))
        opciones_pagina.append("Otro…")
        idx = opciones_pagina.index(actual) if actual in opciones_pagina else 0
        sel_pagina = st.selectbox("Autor / página", opciones_pagina, index=idx)
        pagina_otro = st.text_input("Otro autor (si elegiste «Otro…»)", "")

        message = st.text_area("Texto del post", post.get("message") or "", height=120)
        col1, col2 = st.columns(2)
        with col1:
            created = st.text_input(
                "Fecha (YYYY-MM-DD HH:MM:SS)", str(post.get("created_time") or ""),
            )
            comments = st.number_input(
                "Comentarios", min_value=0, value=int(post.get("comments_count") or 0), step=1,
            )
            shares = st.number_input(
                "Compartidos", min_value=0, value=int(post.get("shares_count") or 0), step=1,
            )
        with col2:
            post_url = st.text_input("Enlace del post", post.get("post_url") or "")
            views = st.number_input(
                "Vistas", min_value=0, value=int(post.get("views_count") or 0), step=1,
            )

        st.markdown("**Reacciones**")
        rc = st.columns(4)
        valores_reac = {}
        for i, (clave, etiqueta) in enumerate(REACCIONES):
            with rc[i % 4]:
                valores_reac[clave] = st.number_input(
                    etiqueta, min_value=0, value=int(post.get(clave) or 0), step=1,
                    key=f"reac_{clave}_{pid}",
                )

        guardar = st.form_submit_button("Guardar cambios", type="primary")

    if guardar:
        page_name = pagina_otro.strip() if sel_pagina == "Otro…" else sel_pagina
        campos = {
            "page_name": page_name,
            "message": message,
            "post_url": post_url.strip(),
            "created_time": created.strip(),
            "comments_count": int(comments),
            "shares_count": int(shares),
            "views_count": int(views),
        }
        campos.update({k: int(v) for k, v in valores_reac.items()})
        ok = db_edits.update_fb_post(pid, campos)
        if ok:
            st.success("Cambios guardados. Recarga para ver la lista actualizada.")
        else:
            st.error("No se pudo actualizar el registro.")

    with st.expander("Eliminar este registro"):
        st.warning("Esta acción borra el post y sus comentarios. No se puede deshacer.")
        if st.button("Eliminar definitivamente", key=f"del_{pid}"):
            if db_edits.delete_fb_post(pid):
                try:
                    borrar_capturas(pid)
                except Exception:
                    pass
                st.success("Registro eliminado. Recarga la página.")
            else:
                st.error("No se pudo eliminar el registro.")


def _editor_posts_tiktok():
    try:
        videos = db_edits.leer_videos_tiktok(limit=500, offset=0) or []
    except Exception as e:
        st.error(f"No se pudieron leer los videos de TikTok: {e}")
        return
    if not videos:
        st.info("Aún no hay videos de TikTok guardados para editar.")
        return

    filtro = st.text_input(
        "Buscar (descripción o cuenta)", "", key="edit_filtro_tk",
        placeholder="Escribe para filtrar por cuenta o descripción…",
    ).strip().lower()
    if filtro:
        videos = [
            v for v in videos
            if filtro in (v.get("description") or "").lower()
            or filtro in (TK_ACCOUNTS.get(v.get("account_id"), "")).lower()
        ]
    if not videos:
        st.warning("Ningún video coincide con el filtro.")
        return

    opciones = {_etiqueta_video_tiktok(v): v for v in videos}
    elegido = st.selectbox("Video a corregir", list(opciones.keys()), key="edit_sel_tk")
    video = opciones[elegido]
    vid = video.get("id")

    cuentas = list(TK_ACCOUNTS.items())  # [(1, 'Alcaldía...'), (3, 'Gustavo...')]
    nombres_cuenta = [n for _, n in cuentas]
    actual_id = video.get("account_id")
    try:
        idx_cuenta = [cid for cid, _ in cuentas].index(actual_id)
    except ValueError:
        idx_cuenta = 0

    with st.form(f"form_edit_tk_{vid}"):
        st.caption(f"ID: {vid}")
        sel_cuenta = st.selectbox("Cuenta / autor", nombres_cuenta, index=idx_cuenta)
        description = st.text_area(
            "Descripción del video", video.get("description") or "", height=120,
        )
        col1, col2 = st.columns(2)
        with col1:
            created = st.text_input(
                "Fecha (YYYY-MM-DD HH:MM:SS)", str(video.get("created_at") or ""),
            )
            views = st.number_input(
                "Vistas", min_value=0, value=int(video.get("views") or 0), step=1,
            )
            likes = st.number_input(
                "Likes", min_value=0, value=int(video.get("likes") or 0), step=1,
            )
        with col2:
            favoritos = st.number_input(
                "Favoritos", min_value=0, value=int(video.get("favorites_count") or 0), step=1,
            )
            compartidos = st.number_input(
                "Compartidos", min_value=0, value=int(video.get("shares") or 0), step=1,
            )
            comments = st.number_input(
                "Comentarios", min_value=0, value=int(video.get("comments_count") or 0), step=1,
            )

        guardar = st.form_submit_button("Guardar cambios", type="primary")

    if guardar:
        nombre_a_id = {n: cid for cid, n in cuentas}
        campos = {
            "account_id": nombre_a_id.get(sel_cuenta, actual_id),
            "description": description,
            "created_at": created.strip(),
            "views": int(views),
            "likes": int(likes),
            "favorites_count": int(favoritos),
            "shares": int(compartidos),
            "comments_count": int(comments),
        }
        ok = db_edits.update_video_tiktok(vid, campos)
        if ok:
            st.success("Cambios guardados. Recarga para ver la lista actualizada.")
        else:
            st.error("No se pudo actualizar el video.")

    with st.expander("Eliminar este video"):
        st.warning("Esta acción borra el video y sus comentarios. No se puede deshacer.")
        if st.button("Eliminar definitivamente", key=f"del_tk_{vid}"):
            if db_edits.delete_video_tiktok(vid):
                st.success("Video eliminado. Recarga la página.")
            else:
                st.error("No se pudo eliminar el video.")


# ══════════════════════════════════════════════
# Herramienta 2 — medalla del período
# ══════════════════════════════════════════════

def _editor_medalla():
    vigente = medalla_store.get_medalla_vigente()
    if vigente and vigente.get("post_id"):
        periodo_lbl = vigente.get("periodo_label") or "s/período"
        n_medios = len(vigente.get("medios") or [])
        st.caption(
            f"Medalla vigente: {vigente.get('post_id')} · {periodo_lbl} · {n_medios} réplica(s)"
        )

    periodo = st.selectbox(
        "Período a evaluar", OPCIONES_PERIODO,
        index=min(2, len(OPCIONES_PERIODO) - 1), key="medalla_periodo",
    )
    fecha_ref = st.session_state.get("fecha_ref")

    try:
        inicio, fin, candidatos = medalla_seleccion.sugerir_candidatos(
            periodo, fecha_ref=fecha_ref, top=8,
        )
    except Exception as e:
        st.error(f"No se pudieron calcular los candidatos: {e}")
        return

    if not candidatos:
        st.info("No hay publicaciones oficiales en el período seleccionado.")
        return

    st.caption(f"Rango: {etiqueta_rango(inicio, fin)}")

    # Sugerencia opcional del LLM (afinada con decisiones anteriores).
    if st.button("Ver recomendación de la IA", key="btn_ia_medalla"):
        with st.spinner("Analizando candidatos…"):
            texto = medalla_seleccion.recomendacion_ia(candidatos)
        if texto:
            st.info(texto)
        else:
            st.caption("La IA no está disponible; usa el orden por tracción de abajo.")

    etiquetas = {}
    for i, c in enumerate(candidatos):
        m = c.get("_metricas") or {}
        positivas = m.get("positivas", 0)
        negativas = m.get("negativas", 0)
        compartidos = m.get("compartidos", 0)
        etiquetas[
            f"#{i + 1} · {_etiqueta_post(c)} — +{positivas} / -{negativas} · {compartidos} comp."
        ] = c
    sel = st.radio("Candidato a medalla (sugerido: el primero)",
                   list(etiquetas.keys()), key="medalla_radio")
    elegido = etiquetas[sel]

    # Réplicas externas que el analista marca para el informe.
    externos = medalla_seleccion.listar_externos(inicio, fin)
    opc_ext = {}
    for e in externos:
        nombre_ext = e.get("page_name") or "—"
        reac = int(e.get("total_reactions") or 0)
        com = int(e.get("comments_count") or 0)
        opc_ext[f"{nombre_ext} · {reac} reac. · {com} com."] = e.get("post_id")
    marcadas = st.multiselect(
        "Réplicas en páginas externas (medios) para el informe",
        list(opc_ext.keys()), key="medalla_medios",
    )
    nota = st.text_input("Nota (por qué es la medalla; ayuda a la IA a aprender)", "")

    if st.button("Aprobar como medalla", type="primary", key="btn_aprobar_medalla"):
        medios_ids = [opc_ext[k] for k in marcadas]
        medalla_store.aprobar_medalla(
            post_id=elegido.get("post_id"),
            score=elegido.get("_score", 0),
            periodo_label=etiqueta_rango(inicio, fin),
            medios=medios_ids,
            nota=nota,
            features=elegido.get("_metricas"),
        )
        st.success(
            "Medalla aprobada. En el dashboard del alcalde, el informe ya queda "
            "disponible en la pestaña «Memoria e Inteligencia Aplicada», sección "
            "«Informe de la mejor medalla reciente» (con descarga directa del PDF)."
        )


def seccion_editar_db():
    st.markdown("## 🛠️ Editar base de datos y medalla")
    st.caption(
        "Herramienta interna del analista. Corrige registros y administra la "
        "medalla del período. El alcalde solo ve y descarga el informe en el dashboard."
    )
    tab_corr, tab_medalla = st.tabs(["✏️ Corregir registros", "🏅 Medalla del período"])
    with tab_corr:
        _editor_posts()
    with tab_medalla:
        _editor_medalla()
