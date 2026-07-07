"""Editor de base de datos para el analista (dentro del panel de carga, SOLO LOCAL).

Dos herramientas:
  1) Corregir registros ya guardados (Facebook y TikTok) — p.ej. cambiar el
     autor de un post de «Alcaldía de Santa Ana» a «Gustavo Acevedo», ajustar
     texto/descripción, fecha, métricas o enlace; también eliminar un registro.
  2) Administrar la «medalla» del período — ver la sugerencia automática
     (mayor tracción positiva), aprobarla manualmente, marcar las réplicas en
     páginas externas, redactar la narrativa del informe (borrador con IA,
     editable) y elegir las publicaciones que no traducen tracción.
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
import medalla_pdf  # noqa: E402
import externos_store  # noqa: E402
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

# Claves de narrativa editable ↔ su widget en session_state.
_NARR_KEYS = {
    "mensaje_corto": "narr_mensaje",
    "emocion_real": "narr_emocion",
    "autoridad_cercana": "narr_autoridad",
    "evidencia_tangible": "narr_evidencia",
    "titular": "narr_titular",
    "medio_retomo": "narr_medio",
    "comparacion": "narr_comparacion",
}


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


# ═════════════════════════════════════
# Herramienta 1 — corregir registros
# ═════════════════════════════════════

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


# ═════════════════════════════════════
# Herramienta 2 — medalla del período
# ═════════════════════════════════════

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
    try:
        inicio, fin, candidatos = medalla_seleccion.sugerir_candidatos(periodo)
    except Exception as e:
        st.error(f"No se pudo calcular la sugerencia: {e}")
        return
    st.caption(f"Período: {etiqueta_rango(inicio, fin)}")
    if not candidatos:
        st.info("No hay publicaciones oficiales en este período.")
        return

    # Sugerencia de la IA sobre cuál es la medalla (afinada con el historial).
    if st.button("Sugerir con IA cuál es la medalla", key="btn_ia_medalla"):
        with st.spinner("Consultando…"):
            texto = medalla_seleccion.recomendacion_ia(candidatos)
        st.session_state["medalla_reco_ia"] = texto or ""
        if not texto:
            st.info("La IA no está disponible; usa la sugerencia heurística (la primera).")
    if st.session_state.get("medalla_reco_ia"):
        st.info(st.session_state["medalla_reco_ia"])

    # Post medalla (el primero es la sugerencia heurística de mayor tracción).
    opciones_post = {_etiqueta_post(p): p for p in candidatos}
    elegido_lbl = st.radio(
        "Publicación medalla (sugerida primero)", list(opciones_post.keys()),
        key="medalla_radio",
    )
    elegido = opciones_post[elegido_lbl]

    # Réplicas en medios externos ya cargados.
    externos = medalla_seleccion.listar_externos(inicio, fin)
    opc_ext = {
        f"{e.get('page_name')} · {int(e.get('total_reactions') or 0)} reac · "
        f"{(e.get('message') or '')[:40]}": e.get("post_id")
        for e in externos
    }
    medios_sel = st.multiselect(
        "Réplicas en medios externos (de la base de externos)",
        list(opc_ext.keys()), key="medalla_medios",
    )

    # Alta manual de un medio externo (cuando la réplica no está en la base).
    with st.expander("➕ Agregar enlace de un medio externo a mano"):
        url_m = st.text_input("Enlace del medio", key="medalla_ext_url")
        nombre_m = st.text_input("Nombre del medio", key="medalla_ext_nombre")
        c1, c2 = st.columns(2)
        with c1:
            reac_m = st.number_input("Reacciones", min_value=0, step=1, key="medalla_ext_reac")
        with c2:
            com_m = st.number_input("Comentarios", min_value=0, step=1, key="medalla_ext_com")
        if st.button("Agregar medio", key="btn_add_ext_medalla"):
            if url_m.strip():
                try:
                    pid_ext = externos_store.agregar_post_externo_manual(
                        url_m.strip(), page_name=nombre_m.strip(),
                        total_reactions=int(reac_m), comments_count=int(com_m),
                    )
                    st.session_state.setdefault("medalla_medios_manuales", [])
                    if pid_ext and pid_ext not in st.session_state["medalla_medios_manuales"]:
                        st.session_state["medalla_medios_manuales"].append(pid_ext)
                    st.success("Medio agregado. Se incluirá al aprobar la medalla.")
                except Exception as e:
                    st.error(f"No se pudo agregar el medio: {e}")
            else:
                st.warning("Escribe el enlace del medio.")
    manuales = st.session_state.get("medalla_medios_manuales", [])
    if manuales:
        st.caption(f"Medios agregados a mano en esta sesión: {len(manuales)}")

    # —— Narrativa del informe (borrador editable) ——
    # El botón de borrador IA va ANTES de crear los widgets: así puede escribir
    # en session_state las claves narr_* en el mismo run (Streamlit no permite
    # modificar la clave de un widget después de instanciarlo).
    st.markdown("**Narrativa del informe (borrador editable)**")
    st.caption(
        "La IA propone un borrador a partir del texto del post; tú lo editas. "
        "El texto puede variar cada vez, pero la estructura del PDF se mantiene."
    )
    contexto_borrador = {
        "descripcion_post": (elegido.get("message") or "").strip(),
        "periodo_label": etiqueta_rango(inicio, fin),
    }
    if st.button("Generar borrador con IA", key="btn_narr_ia"):
        with st.spinner("Redactando borrador…"):
            try:
                borrador = medalla_pdf.borrador_narrativa(
                    elegido, contexto_borrador, usar_ia=True,
                )
            except Exception:
                borrador = {}
        for clave, wkey in _NARR_KEYS.items():
            st.session_state[wkey] = borrador.get(clave, "") if borrador else ""
        st.success("Borrador generado. Revísalo y edítalo antes de aprobar.")
    for wkey in _NARR_KEYS.values():
        st.session_state.setdefault(wkey, "")

    st.text_input("Mensaje corto (la «prueba del dolor» en una frase)", key="narr_mensaje")
    st.text_area("Emoción real", key="narr_emocion", height=70)
    st.text_area("Autoridad cercana", key="narr_autoridad", height=70)
    st.text_area("Evidencia tangible", key="narr_evidencia", height=70)
    st.text_input("Titular legible al instante", key="narr_titular")
    st.text_input("Medio que la retomó (opcional)", key="narr_medio")
    st.text_area(
        "Comparación con otro alcalde (opcional, manual)",
        key="narr_comparacion", height=70,
    )

    # Publicaciones que no traducen tracción: sugeridas automáticamente, editables.
    st.markdown("**Publicaciones que no traducen tracción** (sugeridas, editables)")
    sugeridos_nt = medalla_seleccion.sugerir_no_traccion(inicio, fin, top=3)
    opc_nt = {_etiqueta_post(p): p.get("post_id") for p in sugeridos_nt}
    marcadas_nt = st.multiselect(
        "Se incluirán en la sección «contenido que no traduce tracción»",
        list(opc_nt.keys()), default=list(opc_nt.keys()), key="medalla_no_traccion",
    )

    nota = st.text_input("Nota interna (opcional)", key="medalla_nota")

    if st.button("Aprobar como medalla del período", type="primary", key="btn_aprobar_medalla"):
        medios_ids = [opc_ext[k] for k in medios_sel if k in opc_ext]
        medios_ids += list(st.session_state.get("medalla_medios_manuales", []))
        narrativa = {
            clave: (st.session_state.get(wkey) or "").strip()
            for clave, wkey in _NARR_KEYS.items()
        }
        narrativa["no_traccion"] = [opc_nt[k] for k in marcadas_nt if k in opc_nt]
        features = elegido.get("_metricas") or {}
        try:
            medalla_store.aprobar_medalla(
                elegido.get("post_id"), score=elegido.get("_score", 0),
                periodo_label=etiqueta_rango(inicio, fin), medios=medios_ids,
                nota=nota, features=features, narrativa=narrativa,
            )
        except Exception as e:
            st.error(f"No se pudo aprobar la medalla: {e}")
            return
        # Limpia el estado de edición para la próxima medalla.
        for wkey in _NARR_KEYS.values():
            st.session_state.pop(wkey, None)
        st.session_state.pop("medalla_medios_manuales", None)
        st.session_state.pop("medalla_reco_ia", None)
        st.success(
            "Medalla aprobada. El informe del alcalde se actualizará automáticamente."
        )


def seccion_editar_db():
    st.subheader("🛠️ Editor de base de datos")
    tab1, tab2 = st.tabs(["✏️ Corregir registros", "🏅 Medalla del período"])
    with tab1:
        _editor_posts()
    with tab2:
        _editor_medalla()
