"""Seccion de carga e ingesta de contenido (extraida de app.py).

Incluye la fuente 'Externos': autores que NO son cuentas oficiales. Se permite
seleccionar una pagina externa ya registrada o agregar una nueva, que se persiste
en external_pages para reutilizarla. Externos se procesa con el mismo layout que
Facebook (extraccion, revision y confirmacion).
"""

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date

from src.config import Config
_cfg = Config()
FB_PAGES_OFICIALES = _cfg.FB_PAGES_OFICIALES
TK_ACCOUNTS = _cfg.TK_ACCOUNTS
FACEBOOK_DB = _cfg.FACEBOOK_DB
TIKTOK_DB = _cfg.TIKTOK_DB
EXTERNOS_DB = _cfg.EXTERNOS_DB
from dashboard.guardar_lote import guardar_lote
from dashboard.externos_store import listar_paginas_externas, agregar_pagina_externa


def _activas():
    """Devuelve (FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB)."""
    return (FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB)


# ═══════════════════════
# Helpers de revisión (Fase 3)
# ═════════════════════════

def _campo_numero(label: str, dato_confianza: dict, key_suffix: str, id_temporal: str) -> None:
    """Renderiza st.number_input con resaltado por confianza.

    confianza 'seguro' → normal
    confianza 'dudoso' → 🟡 + "revisar: lectura dudosa"
    confianza 'no_detectado' → 🟡 + "no detectado — completa a mano"
    confianza 'manual' → 🟡 + "se teclea a mano (no se confía al OCR)"
    """
    confianza = dato_confianza.get("confianza", "no_detectado")
    valor = dato_confianza.get("valor")
    key = f"rev_{key_suffix}_{id_temporal}"

    label_display = f"🟡 {label}" if confianza != "seguro" else label
    initial = valor if valor is not None else 0

    st.number_input(label_display, min_value=0, value=initial, step=1, key=key)
    if confianza == "dudoso":
        st.caption("revisar: lectura dudosa")
    elif confianza == "no_detectado":
        st.caption("no detectado — completa a mano")
    elif confianza == "manual":
        st.caption("se teclea a mano (no se confía al OCR)")


def _contrato_vacio(plataforma: str) -> dict:
    """Contrato vacío para rellenar a mano cuando la IA falla."""
    vacio = {"valor": None, "confianza": "no_detectado"}
    if plataforma in ("facebook", "externos"):
        return {
            "plataforma": plataforma,
            "texto_post": "",
            "fecha": {"valor": None, "confianza": "no_detectado"},
            "autor_pagina": None,
            "reacciones": {k: dict(vacio) for k in (
                "likes", "loves", "cares", "hahas", "sads", "wows", "angrys", "total"
            )},
            "comentarios_count": dict(vacio),
            "compartidos": {"valor": None, "confianza": "manual"},
            "vistas": {"valor": None, "confianza": "manual"},
            "comentarios": [],
        }
    elif plataforma == "tiktok":
        return {
            "plataforma": "tiktok",
            "texto_post": "",
            "fecha": {"valor": None, "confianza": "no_detectado"},
            "autor_cuenta": None,
            "metricas": {k: dict(vacio) for k in (
                "likes", "favoritos", "comentarios_count"
            )} | {
                "compartidos": {"valor": None, "confianza": "manual"},
                "vistas": {"valor": None, "confianza": "manual"},
            },
            "comentarios": [],
        }


# ═════════════════════════
# Fase 3 — Revisión editable del lote
# ═════════════════════════

def seccion_revisar_lote() -> None:
    """Pantalla de revisión editable post-extracción (Fase 3).

    Dispara extracción con Groq (Llama 4 Scout), muestra tarjetas editables
    con resaltado por confianza, y produce datos_revisados.
    """
    lote = st.session_state["lote_ingreso"]
    pendientes = [p for p in lote if p["estado"] == "pendiente"]
    extraidos = [p for p in lote if p["estado"] in ("extraido", "revisado")]
    errores = [p for p in lote if p["estado"] == "error"]

    if not pendientes and not extraidos and not errores:
        return

    # ── Paso 1: Botón de extracción ──
    if pendientes:
        st.markdown("### 🔍 Extracción con IA")
        st.caption(
            "Groq (Llama 4 Scout) leerá las capturas y extraerá texto, fechas, "
            "reacciones y comentarios. Los números borrosos o no visibles "
            "quedarán marcados para que los completes."
        )
        if st.button("🔍 Extraer y revisar lote", width='stretch', type="primary"):
            from ingreso_extraccion import extraer_posts_desde_archivos
            import uuid

            n = len(pendientes)
            status = st.status(f"Extrayendo datos de los archivos… 0/{n}", expanded=True)
            nuevos_items = []
            procesados = 0
            for item in st.session_state["lote_ingreso"]:
                if item.get("estado") != "pendiente":
                    nuevos_items.append(item)
                    continue

                fuente_item = item.get("fuente", "?")
                # Mostrar avance ANTES de procesar este archivo: el contador i/n
                # se mueve en vivo en vez de quedarse pegado en 0/n hasta el final.
                status.update(
                    label=f"Extrayendo datos de los archivos… {procesados}/{n} — {fuente_item}"
                )

                # Externos usa el mismo layout de extracción que Facebook
                plat_extraccion = "facebook" if item["plataforma"] == "externos" else item["plataforma"]
                resultado = extraer_posts_desde_archivos(item["imagenes"], plat_extraccion)

                if isinstance(resultado, dict) and resultado.get("error"):
                    item["estado"] = "error"
                    item["error_msg"] = resultado["error"]
                    nuevos_items.append(item)
                    procesados += 1
                    status.write(f"❌ {procesados}/{n} · {fuente_item}: {resultado['error']}")
                    continue

                posts = resultado.get("posts", [])
                if not posts:
                    item["estado"] = "error"
                    item["error_msg"] = "No se detectaron posts en el archivo"
                    nuevos_items.append(item)
                    procesados += 1
                    status.write(f"❌ {procesados}/{n} · {fuente_item}: sin posts detectados")
                    continue

                for datos in posts:
                    enlace_auto = (datos.get("enlace") or {}).get("valor")
                    nuevos_items.append({
                        "id_temporal": str(uuid.uuid4()),
                        "plataforma": item["plataforma"],
                        "fuente": item["fuente"],
                        "imagenes": item["imagenes"],
                        "enlace": enlace_auto or item.get("enlace", ""),
                        "enlace_confianza": (datos.get("enlace") or {}).get("confianza", "no_detectado"),
                        "estado": "extraido",
                        "datos_extraidos": datos,
                    })

                procesados += 1
                # Liberar/mostrar lo ya procesado en vivo mientras el resto sigue.
                status.write(f"✅ {procesados}/{n} · {fuente_item} ({len(posts)} post(s))")

            st.session_state["lote_ingreso"] = nuevos_items
            n_total = sum(1 for p in nuevos_items if p["estado"] == "extraido")
            status.update(label=f"✅ Extracción completada ({n_total} posts)", state="complete", expanded=False)
            st.rerun()

        # ── Vía alterna: importar JSON ya extraído ──
        st.markdown("---")
        st.markdown("#### 📥 Importar JSON extraído externamente")
        st.caption(
            "Si ya tienes el JSON generado por otro modelo (Gemini, ChatGPT, etc.), "
            "sube aquí para aplicar directamente sin usar la IA."
        )

        if len(pendientes) > 1:
            opciones_pendientes = [
                f"{p['fuente']} ({p['plataforma']})" for p in pendientes
            ]
            idx_seleccionado = st.selectbox(
                "Selecciona el item pendiente",
                range(len(opciones_pendientes)),
                format_func=lambda i: opciones_pendientes[i],
                key="import_json_select",
            )
            item_seleccionado = pendientes[idx_seleccionado]
        else:
            item_seleccionado = pendientes[0]

        archivo_json = st.file_uploader(
            "Importar JSON ya extraído (opcional)",
            type=["json"],
            key="import_json_uploader",
        )

        if st.button("📥 Aplicar JSON importado", key="btn_importar_json"):
            if not archivo_json:
                st.error("Sube un archivo JSON primero.")
            else:
                import json as _json
                from ingreso_extraccion import _aplicar_contrato

                try:
                    contenido = archivo_json.read().decode("utf-8")
                    datos_json = _json.loads(contenido)
                except (UnicodeDecodeError, _json.JSONDecodeError) as e:
                    st.error(f"El archivo no es un JSON válido: {e}")
                else:
                    if (
                        not isinstance(datos_json, dict)
                        or "posts" not in datos_json
                        or not isinstance(datos_json["posts"], list)
                    ):
                        st.error('El JSON debe tener la forma {"posts": [...]}.')
                    else:
                        posts_raw = datos_json["posts"]
                        if not posts_raw:
                            st.error("El JSON no contiene posts.")
                        else:
                            plat_extraccion = (
                                "facebook"
                                if item_seleccionado["plataforma"] == "externos"
                                else item_seleccionado["plataforma"]
                            )
                            nuevos_items = []
                            error_msg = None

                            for i, post_crudo in enumerate(posts_raw):
                                try:
                                    post_normalizado = _aplicar_contrato(
                                        post_crudo, plat_extraccion
                                    )
                                except Exception as e:
                                    error_msg = (
                                        f"Error al procesar post {i+1} del JSON: {e}"
                                    )
                                    break

                                enlace_auto = (
                                    post_normalizado.get("enlace") or {}
                                ).get("valor")
                                nuevos_items.append({
                                    "id_temporal": str(uuid.uuid4()),
                                    "plataforma": item_seleccionado["plataforma"],
                                    "fuente": item_seleccionado["fuente"],
                                    "imagenes": item_seleccionado["imagenes"],
                                    "enlace": enlace_auto
                                    or item_seleccionado.get("enlace", ""),
                                    "enlace_confianza": (
                                        post_normalizado.get("enlace") or {}
                                    ).get("confianza", "no_detectado"),
                                    "estado": "extraido",
                                    "datos_extraidos": post_normalizado,
                                })

                            if error_msg:
                                lote_actual = list(
                                    st.session_state["lote_ingreso"]
                                )
                                for item in lote_actual:
                                    if (
                                        item["id_temporal"]
                                        == item_seleccionado["id_temporal"]
                                    ):
                                        item["estado"] = "error"
                                        item["error_msg"] = error_msg
                                        break
                                st.session_state["lote_ingreso"] = lote_actual
                                st.error(f"❌ {error_msg}")
                            else:
                                lote_actual = list(
                                    st.session_state["lote_ingreso"]
                                )
                                nuevos = [
                                    item
                                    for item in lote_actual
                                    if item["id_temporal"]
                                    != item_seleccionado["id_temporal"]
                                ]
                                nuevos.extend(nuevos_items)
                                st.session_state["lote_ingreso"] = nuevos
                                st.success(
                                    f"✅ {len(nuevos_items)} post(s) importado(s) "
                                    "desde JSON."
                                )
                                st.rerun()

    # ── Paso 2: Tarjetas editables ──
    if extraidos:
        st.markdown("### ✏️ Revisión y corrección")
        st.caption("Campos marcados con 🟡 requieren atención. Vistas y compartidos se teclean siempre a mano.")

        n_revisados = sum(1 for p in extraidos if p["estado"] == "revisado")
        if n_revisados:
            st.info(f"{n_revisados}/{len(extraidos)} posts confirmados hasta ahora.")

        emoji_plat = {"facebook": "📘", "tiktok": "🎵", "externos": "🌐"}
        for i, item in enumerate(extraidos):
            datos = item.get("datos_extraidos", {})
            is_error = "error" in datos
            is_revisado = item["estado"] == "revisado"
            id_ = item["id_temporal"]

            plat_emoji = emoji_plat.get(item["plataforma"], "📄")
            tag = "✅ Revisado" if is_revisado else "🟡 Pendiente"
            label = f"{plat_emoji} Post {i+1}: {item['fuente']} — {tag}"

            with st.expander(label, expanded=not is_revisado):
                conf = item.get("enlace_confianza", "no_detectado")
                if conf in ("dudoso", "no_detectado"):
                    st.warning("Revisa el enlace: no se detectó con seguridad en el PDF.")
                st.text_input(
                    "Enlace del post",
                    value=item.get("enlace", ""),
                    key=f"rev_enlace_{id_}",
                    help="Extraído automáticamente del PDF. Corrige si es necesario.",
                )

                if is_error:
                    st.error(f"⚠️ Groq no pudo leer esta captura: «{datos['error']}». Llénala a mano.")
                    datos = _contrato_vacio(item["plataforma"])

                with st.form(key=f"form_revision_{id_}"):
                    # ── Texto del post ──
                    texto_key = f"rev_texto_{id_}"
                    texto_val = datos.get("texto_post", "")
                    st.text_area("Texto del post / descripción", value=texto_val, key=texto_key)
                    if not texto_val:
                        st.caption("no se leyó texto, escríbelo si aplica")

                    # ── Fecha ──
                    fecha_key = f"rev_fecha_{id_}"
                    fecha_dato = datos.get("fecha", {"valor": None, "confianza": "no_detectado"})
                    fecha_conf = fecha_dato.get("confianza", "no_detectado")
                    fecha_label = "🟡 Fecha" if fecha_conf != "seguro" else "Fecha"
                    fv = fecha_dato.get("valor")
                    try:
                        fecha_init = datetime.strptime(fv, "%Y-%m-%d").date() if fv else None
                    except (ValueError, TypeError):
                        fecha_init = None
                    # Rango válido del selector. Si no se fija min/max, Streamlit
                    # usa valor±10 años; una fecha mal leída por la IA (p. ej.
                    # 1987) dejaba el calendario topado en ~1997 y al operador
                    # atrapado sin poder llegar a la fecha real. Un post no puede
                    # ser futuro, así que el tope es hoy.
                    fecha_min = date(2015, 1, 1)
                    fecha_max = date.today()
                    fecha_fuera_rango = (
                        fecha_init is not None
                        and not (fecha_min <= fecha_init <= fecha_max)
                    )
                    if fecha_fuera_rango:
                        fecha_init = None
                    st.date_input(
                        fecha_label,
                        value=fecha_init,
                        min_value=fecha_min,
                        max_value=fecha_max,
                        key=fecha_key,
                    )
                    if fecha_fuera_rango:
                        st.caption(
                            "⚠️ la fecha leída quedaba fuera de rango (posible "
                            "error de lectura); selecciónala a mano"
                        )
                    elif fecha_conf == "dudoso":
                        st.caption("revisar: lectura dudosa")
                    elif fecha_conf == "no_detectado":
                        st.caption("no detectado — completa a mano")

                    # ── Métricas según plataforma (Externos = Facebook) ──
                    if item["plataforma"] in ("facebook", "externos"):
                        reacs = datos.get("reacciones", {})
                        st.markdown("**Reacciones**")
                        cols = st.columns(3)
                        fb_order = [
                            ("likes", "Likes"), ("loves", "Me encanta"), ("cares", "Me importa"),
                            ("hahas", "Me divierte"), ("sads", "Me entristece"),
                            ("wows", "Me asombra"), ("angrys", "Me enoja"),
                        ]
                        for idx, (field, lbl) in enumerate(fb_order):
                            with cols[idx % 3]:
                                _campo_numero(lbl, reacs.get(field, {"valor": None, "confianza": "no_detectado"}),
                                              f"fb_{field}", id_)
                        _campo_numero("Total reacciones",
                                      reacs.get("total", {"valor": None, "confianza": "dudoso"}),
                                      "fb_total", id_)
                        _campo_numero("Comentarios (conteo)",
                                      datos.get("comentarios_count", {"valor": None, "confianza": "no_detectado"}),
                                      "fb_comentarios_count", id_)
                        st.markdown("**Campos manuales**")
                        c2 = st.columns(2)
                        with c2[0]:
                            _campo_numero("Compartidos", {"valor": None, "confianza": "manual"},
                                          "fb_compartidos", id_)
                        with c2[1]:
                            _campo_numero("Vistas", {"valor": None, "confianza": "manual"},
                                          "fb_vistas", id_)
                    else:  # TikTok
                        metrics = datos.get("metricas", {})
                        st.markdown("**Métricas**")
                        cols = st.columns(3)
                        tk_order = [
                            ("likes", "Likes"), ("favoritos", "Favoritos"),
                            ("comentarios_count", "Comentarios (conteo)"),
                        ]
                        for idx, (field, lbl) in enumerate(tk_order):
                            with cols[idx % 3]:
                                _campo_numero(lbl, metrics.get(field, {"valor": None, "confianza": "no_detectado"}),
                                              f"tk_{field}", id_)
                        st.markdown("**Campos manuales**")
                        c2 = st.columns(2)
                        with c2[0]:
                            _campo_numero("Compartidos", {"valor": None, "confianza": "manual"},
                                          "tk_compartidos", id_)
                        with c2[1]:
                            _campo_numero("Vistas", {"valor": None, "confianza": "manual"},
                                          "tk_vistas", id_)

                    # ── Comentarios (data_editor dinámico) ──
                    comments_key = f"rev_comments_{id_}"
                    raw = datos.get("comentarios", [])
                    _COMMENT_FIELDS = ["emocion", "intensidad", "confianza_emocion", "tema_sugerido"]
                    if item["plataforma"] in ("facebook", "externos"):
                        df_init = pd.DataFrame([
                            {"texto": c.get("texto", ""), "autor": c.get("autor") or ""}
                            | {f: c.get(f, "") for f in _COMMENT_FIELDS}
                            for c in raw
                        ])
                    else:
                        df_init = pd.DataFrame([
                            {"texto": c.get("texto", "")}
                            | {f: c.get(f, "") for f in _COMMENT_FIELDS}
                            for c in raw
                        ])

                    st.markdown("**Comentarios transcritos**")
                    n_comments = len(df_init)
                    suf = "suficiente" if n_comments >= 15 else "insuficiente"
                    st.caption(
                        f"Edita, borra o agrega filas. Comentarios sin texto se descartan."
                    )
                    col_config = {
                        "texto": st.column_config.TextColumn("Texto", required=True, width="large"),
                    }
                    if item["plataforma"] in ("facebook", "externos"):
                        col_config["autor"] = st.column_config.TextColumn("Autor", width="medium")
                    edited_df = st.data_editor(
                        df_init,
                        column_config=col_config,
                        num_rows="dynamic",
                        key=comments_key,
                        width='stretch',
                    )

                    st.markdown("---")
                    confirmado = st.form_submit_button("✅ Confirmar este post", disabled=is_revisado)

                    if confirmado:
                        _confirmar_post(item, texto_key, fecha_key, edited_df)

    # ── Paso 3: Items en error ──
    errores = [p for p in lote if p["estado"] == "error"]
    if errores:
        st.markdown("### ❌ Errores de extracción")
        st.caption("Estos archivos no pudieron procesarse. Revisa el motivo y reintenta.")
        for item in errores:
            st.error(f"**{item.get('fuente', '?')}** — {item.get('error_msg', 'Error desconocido')}")
            if st.button("🔁 Reintentar extracción", key=f"retry_{item['id_temporal']}"):
                item["estado"] = "pendiente"
                item.pop("error_msg", None)
                st.rerun()


def _confirmar_post(item: dict, texto_key: str, fecha_key: str, df_comentarios: pd.DataFrame) -> None:
    """Lee widgets, valida, y escribe datos_revisados + estado revisado."""
    id_ = item["id_temporal"]
    plataforma = item["plataforma"]

    mensaje = st.session_state.get(texto_key, "")
    fecha = st.session_state.get(fecha_key)

    if not fecha:
        st.error("❌ La fecha es obligatoria. Sin fecha, el post queda excluido del análisis.")
        return

    created = str(fecha)

    comentarios = []
    for _, row in df_comentarios.iterrows():
        t = str(row.get("texto", "") or "").strip()
        if t:
            entry = {"texto": t}
            if plataforma in ("facebook", "externos"):
                entry["autor"] = str(row.get("autor", "") or "").strip() or None
            for field in ("emocion", "intensidad", "confianza_emocion", "tema_sugerido"):
                val = row.get(field)
                if val is not None and str(val).strip():
                    entry[field] = str(val).strip()
            comentarios.append(entry)

    muestra_suf = len(comentarios) >= 15
    if not muestra_suf:
        st.warning(f"⚠️ Muestra insuficiente ({len(comentarios)} < 15). "
                   "El análisis de sentimiento será limitado.")

    # Leer enlace del campo editable
    enlace_final = st.session_state.get(f"rev_enlace_{id_}", item.get("enlace", ""))
    if enlace_final:
        lote = st.session_state["lote_ingreso"]
        for otro in lote:
            if otro["id_temporal"] != id_ and otro.get("enlace", "").strip() == enlace_final.strip():
                st.warning(f"⚠️ Este enlace ya existe en el lote (post {otro.get('id_temporal', '?')[:8]}…).")
                break

    # Leer widgets numéricos
    def _r(suffix):
        return st.session_state.get(f"rev_{suffix}_{id_}", 0) or 0

    if plataforma in ("facebook", "externos"):
        revisados = {
            "plataforma": plataforma,
            "page_name": item["fuente"],
            "message": mensaje,
            "created_time": created,
            "likes_count": _r("fb_likes"),
            "loves_count": _r("fb_loves"),
            "cares_count": _r("fb_cares"),
            "hahas_count": _r("fb_hahas"),
            "sads_count": _r("fb_sads"),
            "wows_count": _r("fb_wows"),
            "angrys_count": _r("fb_angrys"),
            "comments_count": _r("fb_comentarios_count"),
            "shares_count": _r("fb_compartidos"),
            "views_count": _r("fb_vistas"),
            "post_url": enlace_final or None,
            "comentarios": comentarios,
            "muestra_suficiente": muestra_suf,
        }
    else:  # TikTok
        try:
            account_id = int(item["fuente"])
        except (ValueError, TypeError):
            account_id = 0
        revisados = {
            "plataforma": "tiktok",
            "account_id": account_id,
            "description": mensaje,
            "created_at": created,
            "post_url": enlace_final or None,
            "views": _r("tk_vistas"),
            "likes": _r("tk_likes"),
            "favorites_count": _r("tk_favoritos"),
            "shares": _r("tk_compartidos"),
            "comments_count": _r("tk_comentarios_count"),
            "comentarios": comentarios,
            "muestra_suficiente": muestra_suf,
        }

    item["datos_revisados"] = revisados
    item["estado"] = "revisado"
    st.success("✅ Post confirmado.")
    st.rerun()


def seccion_cargar_contenido():
    """Sección para que el operador cargue capturas y arme lotes de posts en memoria."""
    # SEGURIDAD PENDIENTE [PRIORIDAD ALTA]:
    # Este panel permite insertar, modificar y eliminar datos en las bases de datos
    # de producción (facebook.db, tiktok.db, externos.db) sin ninguna autenticación.
    # Opciones de mitigación por orden de implementación:
    # 1. [INMEDIATO] Ejecutar solo en localhost, nunca expuesto a red pública.
    # 2. [CORTO PLAZO] Agregar st.secrets check: contraseña de operador en secrets.toml.
    # 3. [MEDIANO PLAZO] Integrar con sistema de auth corporativo (OAuth2/LDAP).
    # Ver: https://docs.streamlit.io/develop/concepts/connections/secrets-management
    FACEBOOK_DB_ACTIVA, TIKTOK_DB_ACTIVA, EXTERNOS_DB_ACTIVA = _activas()

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">📥 Cargar contenido</div>
        <div class="seccion-subtitulo">
            Sube capturas de pantalla de redes sociales y arma lotes para procesar
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Selector de plataforma y fuente (fuera del form para reactividad) ──
    col_plat, col_fuente = st.columns(2)
    with col_plat:
        plataforma_post = st.radio(
            "Plataforma",
            ["Facebook", "TikTok", "Externos"],
            horizontal=True,
            key="carga_plataforma",
        )

    fuente = None
    with col_fuente:
        if plataforma_post == "Facebook":
            fuente = st.selectbox("Fuente (página oficial)", FB_PAGES_OFICIALES, key="carga_fuente_fb")
        elif plataforma_post == "TikTok":
            tk_nombres = list(TK_ACCOUNTS.values())
            tk_label = st.selectbox("Fuente (cuenta oficial)", tk_nombres, key="carga_fuente_tk")
            tk_id_map = {v: k for k, v in TK_ACCOUNTS.items()}
            fuente = str(tk_id_map[tk_label])
        else:  # Externos
            paginas = listar_paginas_externas(EXTERNOS_DB_ACTIVA)
            opciones = ["➕ Agregar nueva página…"] + list(paginas)
            seleccion = st.selectbox(
                "Fuente (página externa)",
                opciones,
                key="carga_fuente_ext",
                help="Autores que NO son cuentas oficiales. Selecciona una página ya registrada o agrega una nueva.",
            )
            if seleccion == "➕ Agregar nueva página…":
                fuente = st.text_input(
                    "Nombre de la nueva página externa",
                    key="carga_fuente_ext_nueva",
                    help="Se guardará de forma persistente para reutilizarla en el futuro.",
                ).strip()
            else:
                fuente = seleccion

    # ── Formulario: subir capturas y agregar al lote ──
    with st.form("form_agregar_post"):
        imagenes = st.file_uploader(
            "Sube capturas (PNG/JPG) o un PDF con uno o varios posts",
            type=["png", "jpg", "jpeg", "pdf"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.get('uploader_nonce', 0)}",
            help="Un PDF puede contener varios posts distintos; el sistema los separa automáticamente.",
        )

        enlace = st.text_input(
            "Enlace del post (opcional)",
            help="Solo de respaldo. Si el PDF ya incluye el enlace, se extrae automáticamente y este campo puede quedar vacío.",
        )

        submitted = st.form_submit_button("➕ Agregar post al lote", width='stretch')

        if submitted:
            errores = []
            if not imagenes:
                errores.append("Debes subir al menos una captura de pantalla.")
            if not fuente:
                if plataforma_post == "Externos":
                    errores.append("Debes seleccionar o escribir el nombre de la página externa.")
                else:
                    errores.append("Debes seleccionar una fuente (página/cuenta oficial).")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                # Persistir la página externa para reutilizarla en el futuro
                if plataforma_post == "Externos":
                    try:
                        agregar_pagina_externa(fuente, EXTERNOS_DB_ACTIVA)
                    except Exception:
                        pass
                post = {
                    "id_temporal": str(uuid.uuid4()),
                    "plataforma": plataforma_post.lower(),
                    "fuente": fuente,
                    "imagenes": list(imagenes),
                    "enlace": enlace.strip(),
                    "estado": "pendiente",
                }
                st.session_state["lote_ingreso"].append(post)
                st.success(f"✅ Post agregado al lote ({len(imagenes)} imágenes)")

    # ── Estado visual del lote ──
    st.markdown("---")
    lote = st.session_state["lote_ingreso"]
    emoji_plat = {"facebook": "📘", "tiktok": "🎵", "externos": "🌐"}

    if not lote:
        st.info("Aún no has agregado posts. Sube las capturas de un post y pulsa Agregar.")
    else:
        pendientes = sum(1 for p in lote if p["estado"] == "pendiente")
        st.metric("Lote actual", f"{len(lote)} posts", f"{pendientes} pendientes de procesar")

        for post in lote:
            cols = st.columns([1, 2, 1, 1, 1, 0.5])
            emoji = emoji_plat.get(post["plataforma"], "📄")
            cols[0].markdown(f"**{emoji} {post['plataforma'].title()}**")
            cols[1].markdown(f"*Fuente:* {post['fuente']}")
            cols[2].markdown(f"*Imágenes:* {len(post['imagenes'])}")
            cols[3].markdown("*Enlace:* sí" if post["enlace"] else "*Enlace:* —")
            cols[4].markdown(f"*Estado:* {post['estado']}")
            if cols[5].button("🗑️", key=f"quitar_{post['id_temporal']}"):
                st.session_state["lote_ingreso"] = [
                    p for p in st.session_state["lote_ingreso"]
                    if p["id_temporal"] != post["id_temporal"]
                ]
                st.rerun()
            st.markdown("---")

    # ── Revisión Fase 3 ──
    seccion_revisar_lote()

    # ── Guardado a SQLite (Fase 4) ──
    lote = st.session_state["lote_ingreso"]
    revisados = [p for p in lote if p["estado"] == "revisado"]
    guardados = [p for p in lote if p["estado"] == "guardado"]
    if revisados:
        st.markdown("### 💾 Paso 4 — Guardar en base de datos")
        st.caption(f"{len(revisados)} post(s) confirmados listos para guardar.")
        if st.button("💾 Guardar lote en base de datos", type="primary"):
            estado_guardado = st.status("Guardando lote en base de datos…", expanded=True)

            def _progreso_guardado(i, total, etiqueta):
                estado_guardado.update(label=f"Guardando… {i}/{total} — {etiqueta}")
                estado_guardado.write(f"💾 {i}/{total} · {etiqueta}")

            resumen = guardar_lote(lote, progreso_cb=_progreso_guardado)
            estado_guardado.update(label="Guardado finalizado", state="complete", expanded=False)
            partes = []
            if resumen["fb_posts"]:
                partes.append(f"{resumen['fb_posts']} posts FB")
            if resumen["fb_comments"]:
                partes.append(f"{resumen['fb_comments']} comentarios FB")
            if resumen["tk_videos"]:
                partes.append(f"{resumen['tk_videos']} videos TikTok")
            if resumen["tk_comments"]:
                partes.append(f"{resumen['tk_comments']} comentarios TikTok")
            if partes and not resumen["errores"]:
                msg = "✅ Guardado: " + ", ".join(partes)
                st.success(msg)
            elif partes and resumen["errores"]:
                msg = "⚠️ Guardado parcial: " + ", ".join(partes)
                for e in resumen["errores"][:5]:
                    msg += f"\n❌ {e}"
                if len(resumen["errores"]) > 5:
                    msg += f"\n... y {len(resumen['errores'])-5} error(es) más."
                st.warning(msg)
            elif resumen["errores"]:
                msg = "❌ Error al guardar:"
                for e in resumen["errores"][:5]:
                    msg += f"\n❌ {e}"
                if len(resumen["errores"]) > 5:
                    msg += f"\n... y {len(resumen['errores'])-5} error(es) más."
                st.error(msg)
            else:
                st.warning("⚠️ No se guardó nada.")
            st.rerun()
    if guardados:
        st.info(f"✅ {len(guardados)} post(s) ya guardados en la base de datos.")


